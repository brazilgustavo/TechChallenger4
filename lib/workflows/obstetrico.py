"""Fluxo Obstétrico.

Diagrama:

    START
      ↓
    coletar_dados_gestante      (LLM extrai IG, paridade, antecedentes da descrição)
      ↓
    avaliar_risco_gestacional   (regras + LLM classifica habitual / alto risco)
      ↓
    detectar_alertas_urgencia   (regex sinais de alarme obstétrico)
      ↓
   ┌────────┴────────┐
   │  emergência?    │
   └──┬───────────┬──┘
     sim         não
      ↓           ↓
   alerta_emerg → orientacoes_especificas (LLM gera, baseado em RAG)
      ↓           ↓
      └──→ agendar_exames        (rotina de pré-natal por IG)
              ↓
        definir_acompanhamento   (periodicidade conforme risco)
              ↓
        compilar_resposta
              ↓
             END
"""
from __future__ import annotations

from typing import TypedDict

from lib.config import ml_risco_habilitado

from . import common


# Sinais de alarme obstétrico (gestante deve buscar emergência imediatamente)
SINAIS_ALARME_OBST = {
    'sangramento': 'Sangramento vaginal de qualquer volume',
    'perda_liquido': 'Perda de líquido amniótico',
    'dor_cabeca_intensa': 'Cefaleia intensa / refratária — suspeita pré-eclâmpsia',
    'visao_turva': 'Alterações visuais (escotomas, turvação) — suspeita pré-eclâmpsia',
    'epigastralgia': 'Dor epigástrica em barra — suspeita HELLP',
    'edema_subito': 'Edema súbito de mãos/face',
    'ausencia_movimentos': 'Diminuição/ausência de movimentos fetais',
    'contracoes_regulares': 'Contrações regulares antes de 37 semanas (TPP)',
    'febre': 'Febre ≥38°C',
    'crise_convulsiva': 'Crise convulsiva (eclâmpsia)',
}


CRITERIOS_ALTO_RISCO = [
    'idade <16 ou >35a',
    'HAS prévia ou induzida',
    'DM prévio ou gestacional',
    'cardiopatia',
    'nefropatia',
    'TEV prévio',
    'cesárea prévia (≥2)',
    'abortamento de repetição (≥2)',
    'natimorto prévio',
    'malformação fetal prévia',
    'gemelaridade',
    'IMC ≥35',
    'tabagismo / álcool / drogas',
    'HIV / sífilis / hepatites',
    'isoimunização Rh',
]


class ObstetricoState(TypedDict, total=False):
    # Inputs
    descricao_caso: str
    paciente_id: int | None
    ig_semanas: int | None       # opcional — se informado, pula extração

    # Intermediários
    dados_gestante: dict          # {ig_semanas, paridade, antecedentes, sintomas_atuais}
    classificacao_risco: str      # 'habitual' | 'alto_risco'
    fatores_risco_identificados: list[str]
    alertas_urgencia: list[str]
    eh_emergencia: bool
    orientacoes_especificas: str
    exames_agendados: list[dict]  # [{exame, prazo}]
    acompanhamento: dict          # {periodicidade, proxima_consulta_em_dias}

    # Explainability
    raciocinio: list[str]
    fontes: list[dict]
    confianca: str

    # Output
    resposta_estruturada: dict


# ============= NODES =============

def _coletar_dados_gestante(chat_model):
    def node(state: ObstetricoState) -> dict:
        if state.get('ig_semanas') and state.get('dados_gestante'):
            return {}   # já tem dados, pula

        sistema = 'Você é obstetra. Extraia dados estruturados da descrição clínica.'
        prompt = (
            f'Descrição clínica:\n"{state["descricao_caso"]}"\n\n'
            'Extraia em JSON: {"ig_semanas": int|null, "paridade": "G2P1A0"|null, '
            '"antecedentes": ["HAS", "DM"], "sintomas_atuais": ["..."]}'
        )
        out = common.llm_json(chat_model, prompt, sistema, default={})
        dados = {
            'ig_semanas': out.get('ig_semanas') or state.get('ig_semanas'),
            'paridade': out.get('paridade'),
            'antecedentes': out.get('antecedentes', []),
            'sintomas_atuais': out.get('sintomas_atuais', []),
        }
        return {
            'dados_gestante': dados,
            'ig_semanas': dados['ig_semanas'],
            'raciocinio': [f'Dados extraídos: IG={dados["ig_semanas"]}, '
                          f'paridade={dados["paridade"]}, '
                          f'antecedentes={", ".join(dados["antecedentes"]) or "—"}'],
        }
    return node


def _avaliar_risco_gestacional(chat_model):
    def node(state: ObstetricoState) -> dict:
        dados = state.get('dados_gestante', {})
        sistema = ('Você é obstetra. Classifique como "habitual" ou "alto_risco" '
                   'conforme os critérios MS/FEBRASGO.')
        criterios = '; '.join(CRITERIOS_ALTO_RISCO)
        prompt = (
            f'Dados da gestante:\n{dados}\n\n'
            f'Critérios de alto risco (qualquer um basta): {criterios}\n\n'
            'Responda: {"classificacao": "habitual|alto_risco", "fatores": ["..."]}'
        )
        out = common.llm_json(chat_model, prompt, sistema,
                             default={'classificacao': 'habitual', 'fatores': []})
        return {
            'classificacao_risco': out.get('classificacao', 'habitual'),
            'fatores_risco_identificados': out.get('fatores', []),
            'raciocinio': state.get('raciocinio', []) +
                          [f'Risco gestacional: {out.get("classificacao")} | '
                           f'fatores: {", ".join(out.get("fatores", [])) or "nenhum"}'],
        }
    return node


def _detectar_alertas_urgencia(state: ObstetricoState) -> dict:
    """Determinístico: matching de keywords no texto da descrição."""
    desc = state.get('descricao_caso', '').lower()
    alertas = []
    for chave, desc_alerta in SINAIS_ALARME_OBST.items():
        # heurística simples: termos-chave de cada alarme
        if chave == 'sangramento' and 'sangra' in desc:
            alertas.append(desc_alerta)
        elif chave == 'perda_liquido' and ('perda de líquido' in desc or 'rotura' in desc):
            alertas.append(desc_alerta)
        elif chave == 'dor_cabeca_intensa' and ('cefaleia' in desc or 'dor de cabeça' in desc):
            alertas.append(desc_alerta)
        elif chave == 'visao_turva' and ('escotoma' in desc or 'turvaç' in desc or 'visão turv' in desc):
            alertas.append(desc_alerta)
        elif chave == 'epigastralgia' and ('epigastr' in desc or 'dor em barra' in desc):
            alertas.append(desc_alerta)
        elif chave == 'edema_subito' and 'edema' in desc and ('súbito' in desc or 'face' in desc):
            alertas.append(desc_alerta)
        elif chave == 'ausencia_movimentos' and ('movimento fetal' in desc and ('ausenc' in desc or 'diminui' in desc)):
            alertas.append(desc_alerta)
        elif chave == 'contracoes_regulares':
            ig = state.get('ig_semanas') or 40
            if 'contraç' in desc and ig < 37:
                alertas.append(desc_alerta)
        elif chave == 'febre' and ('febre' in desc or 'temperatura' in desc):
            alertas.append(desc_alerta)
        elif chave == 'crise_convulsiva' and ('convulsão' in desc or 'convulsiv' in desc):
            alertas.append(desc_alerta)

    return {
        'alertas_urgencia': alertas,
        'eh_emergencia': len(alertas) > 0,
        'raciocinio': state.get('raciocinio', []) +
                      [f'Sinais de alarme detectados: {len(alertas)} '
                       f'({", ".join(alertas[:2])}{"..." if len(alertas) > 2 else ""})'],
    }


def _orientacoes_especificas(chat_model, retriever):
    def node(state: ObstetricoState) -> dict:
        ig = state.get('ig_semanas') or 0
        risco = state.get('classificacao_risco', 'habitual')

        fontes = common.rag_search(
            retriever,
            f'pré-natal {risco} {ig} semanas conduta orientações',
            categoria='ginecologia_obstetricia', k=3,
        )
        contexto = '\n---\n'.join(f['trecho'] for f in fontes)[:2500]

        sistema = ('Você é obstetra. Forneça orientações específicas para a equipe, em PT-BR, '
                   'em formato bullets curtos. Não prescreva medicações.')
        emergencia_msg = ('🚨 EMERGÊNCIA OBSTÉTRICA detectada. ' if state.get('eh_emergencia') else '')
        prompt = (
            f'{emergencia_msg}'
            f'Gestante {risco}, IG ≈ {ig}sem. '
            f'Fatores: {state.get("fatores_risco_identificados", [])}\n'
            f'Sintomas: {state.get("dados_gestante", {}).get("sintomas_atuais", [])}\n'
            f'Alarmes: {state.get("alertas_urgencia", [])}\n\n'
            f'Contexto de protocolo:\n{contexto}\n\n'
            'Forneça orientações específicas para a equipe (4-6 bullets):'
        )
        texto = common.llm_text(chat_model, prompt, sistema)
        return {
            'orientacoes_especificas': texto,
            'fontes': fontes,
            'raciocinio': state.get('raciocinio', []) +
                          [f'Orientações geradas com {len(fontes)} fonte(s) do protocolo.'],
        }
    return node


def _agendar_exames(state: ObstetricoState) -> dict:
    """Determinístico: rotina de pré-natal baseada na IG e classificação."""
    ig = state.get('ig_semanas') or 0
    risco = state.get('classificacao_risco', 'habitual')
    agendamentos: list[dict] = []

    # Rotina universal de 1º trimestre (até 13 semanas)
    if ig <= 13:
        agendamentos.extend([
            {'exame': 'Hemograma completo, tipagem sanguínea/Rh, glicemia jejum, EAS, urocultura',
             'prazo': 'até 7 dias'},
            {'exame': 'Sorologias (HIV, sífilis VDRL, hepatites B/C, toxoplasmose, rubéola)',
             'prazo': 'até 7 dias'},
            {'exame': 'USG obstétrica de 1º trimestre (11-13s+6d) com TN',
             'prazo': 'até 13 semanas'},
        ])

    # 2º trimestre (14-27)
    if 14 <= ig <= 27:
        agendamentos.append({
            'exame': 'USG morfológica de 2º trimestre (20-24s)',
            'prazo': 'agendar para 20-24 semanas',
        })
        if 24 <= ig <= 28:
            agendamentos.append({
                'exame': 'TOTG 75g (rastreio DMG)',
                'prazo': 'entre 24-28 semanas',
            })

    # 3º trimestre (28+)
    if ig >= 28:
        agendamentos.extend([
            {'exame': 'Repetir hemograma, sorologias',
             'prazo': 'até 7 dias'},
            {'exame': 'USG obstétrica de 3º trimestre (33-36s)',
             'prazo': 'agendar para 33-36 semanas'},
        ])
        if ig >= 35:
            agendamentos.append({
                'exame': 'Cultura de Streptococcus B vaginal/anal',
                'prazo': '35-37 semanas',
            })

    # Alto risco: exames adicionais
    if risco == 'alto_risco':
        agendamentos.append({
            'exame': 'Consultas e exames adicionais conforme fator(es) de risco específico(s)',
            'prazo': 'definir com pré-natal de alto risco',
        })

    return {
        'exames_agendados': agendamentos,
        'raciocinio': state.get('raciocinio', []) +
                      [f'Agendados {len(agendamentos)} exame(s) conforme IG/risco.'],
    }


def _definir_acompanhamento(state: ObstetricoState) -> dict:
    """Determinístico: periodicidade conforme IG e risco."""
    ig = state.get('ig_semanas') or 0
    risco = state.get('classificacao_risco', 'habitual')
    emergencia = state.get('eh_emergencia', False)

    if emergencia:
        ac = {
            'periodicidade': 'Encaminhar IMEDIATAMENTE para pronto-socorro obstétrico',
            'proxima_consulta_em_dias': 0,
            'profissionais_envolvidos': ['Obstetra de plantão', 'Anestesia', 'Neonatologia (se IG ≥24s)'],
        }
    elif risco == 'alto_risco':
        if ig < 28:
            prox = 14
        elif ig < 36:
            prox = 7
        else:
            prox = 3
        ac = {
            'periodicidade': 'Pré-natal de alto risco',
            'proxima_consulta_em_dias': prox,
            'profissionais_envolvidos': ['Obstetra de alto risco', 'Equipe multiprofissional'],
        }
    else:
        if ig < 28:
            prox = 30
        elif ig < 36:
            prox = 15
        else:
            prox = 7
        ac = {
            'periodicidade': 'Pré-natal de risco habitual (MS)',
            'proxima_consulta_em_dias': prox,
            'profissionais_envolvidos': ['Obstetra ou enfermeira obstétrica'],
        }
    return {
        'acompanhamento': ac,
        'raciocinio': state.get('raciocinio', []) +
                      [f'Próxima consulta: {ac["proxima_consulta_em_dias"]} dias ({ac["periodicidade"]})'],
    }


def _compilar_resposta(state: ObstetricoState) -> dict:
    confianca = common.estimar_confianca(
        n_fontes=len(state.get('fontes', [])),
        n_decisoes_llm=2,
        dados_paciente_disponiveis=(state.get('paciente_id') is not None
                                    or bool(state.get('dados_gestante'))),
    )
    resposta = {
        'dados_gestante': state.get('dados_gestante', {}),
        'classificacao_risco': state.get('classificacao_risco'),
        'fatores_risco_identificados': state.get('fatores_risco_identificados', []),
        'alertas_urgencia': state.get('alertas_urgencia', []),
        'eh_emergencia': state.get('eh_emergencia', False),
        'orientacoes_especificas': state.get('orientacoes_especificas'),
        'exames_agendados': state.get('exames_agendados', []),
        'acompanhamento': state.get('acompanhamento'),
        'confianca': confianca,
        'raciocinio': state.get('raciocinio', []),
        'fontes': state.get('fontes', []),
    }
    return {'confianca': confianca, 'resposta_estruturada': resposta}


# ============= GRAPH =============

def build_obstetrico_workflow(chat_model, conn, retriever):
    """Compila o StateGraph do fluxo Obstétrico."""
    from langgraph.graph import StateGraph, START, END

    g = StateGraph(ObstetricoState)
    g.add_node('coletar_dados_gestante', _coletar_dados_gestante(chat_model))
    g.add_node('avaliar_risco_gestacional', _avaliar_risco_gestacional(chat_model))
    g.add_node('detectar_alertas_urgencia', _detectar_alertas_urgencia)
    g.add_node('gerar_orientacoes_especificas', _orientacoes_especificas(chat_model, retriever))
    g.add_node('agendar_exames', _agendar_exames)
    g.add_node('definir_acompanhamento', _definir_acompanhamento)
    g.add_node('compilar_resposta', _compilar_resposta)

    g.add_edge(START, 'coletar_dados_gestante')
    g.add_edge('coletar_dados_gestante', 'avaliar_risco_gestacional')
    if ml_risco_habilitado():
        from .risco_ml import classificar_risco_ml_opcional

        g.add_node('classificar_risco_ml', classificar_risco_ml_opcional)
        g.add_edge('avaliar_risco_gestacional', 'classificar_risco_ml')
        g.add_edge('classificar_risco_ml', 'detectar_alertas_urgencia')
    else:
        g.add_edge('avaliar_risco_gestacional', 'detectar_alertas_urgencia')
    g.add_edge('detectar_alertas_urgencia', 'gerar_orientacoes_especificas')
    g.add_edge('gerar_orientacoes_especificas', 'agendar_exames')
    g.add_edge('agendar_exames', 'definir_acompanhamento')
    g.add_edge('definir_acompanhamento', 'compilar_resposta')
    g.add_edge('compilar_resposta', END)

    return g.compile()
