"""Fluxo de Triagem Ginecológica.

Diagrama:

    START
      ↓
    parse_sintomas         (LLM extrai sintomas estruturados)
      ↓
    analisar_risco         (RAG busca diferenciais nos protocolos)
      ↓
    classificar_urgencia   (regras + LLM define emergência/urgente/agendado/rotina)
      ↓
   ┌──────┴──────┐
   │ emergencia? │
   └──┬───────┬──┘
     sim     não
      ↓       ↓
      ↓     sugerir_exames
      ↓       ↓
      ↓     orientacoes_iniciais
      ↓       ↓
      └→ agendamento  (especialidade + prazo)
            ↓
        compilar_resposta
            ↓
           END

Estado final inclui raciocínio, fontes citadas e nível de confiança.
"""
from __future__ import annotations

from typing import TypedDict

from . import common


SINAIS_EMERGENCIA = [
    'sangramento intenso', 'sangramento abundante', 'hemorragia',
    'dor pélvica intensa', 'dor abdominal severa',
    'perda de consciência', 'desmaio',
    'febre alta', 'sepse',
    'trabalho de parto', 'rotura de membranas',
    'ideação suicida', 'risco de vida',
]


class TriagemState(TypedDict, total=False):
    # Inputs
    queixa: str
    paciente_id: int | None

    # Intermediários
    sintomas_extraidos: list[str]
    diferenciais: list[str]
    sinais_alarme: list[str]
    urgencia: str               # 'emergencia' | 'urgente' | 'agendado' | 'rotina'
    justificativa_urgencia: str
    exames_sugeridos: list[str]
    orientacoes_iniciais: str
    agendamento: dict           # {especialidade, prazo}

    # Explainability
    raciocinio: list[str]
    fontes: list[dict]
    confianca: str

    # Output final
    resposta_estruturada: dict


# ============= NODES =============

def _parse_sintomas(chat_model):
    def node(state: TriagemState) -> dict:
        sistema = (
            'Você é um médico clínico em triagem. Extraia da queixa apenas os SINTOMAS '
            'e ACHADOS relatados, em formato lista. Responda APENAS JSON.'
        )
        prompt = (
            f'Queixa: {state["queixa"]}\n\n'
            'Responda no formato: {"sintomas": ["sangramento intenso", "dor pélvica", ...]}'
        )
        out = common.llm_json(chat_model, prompt, sistema, default={'sintomas': []})
        sintomas = out.get('sintomas', [])
        return {
            'sintomas_extraidos': sintomas,
            'raciocinio': [f'Sintomas extraídos: {", ".join(sintomas) or "nenhum"}'],
        }
    return node


def _analisar_risco(chat_model, retriever):
    def node(state: TriagemState) -> dict:
        query = ' '.join(state.get('sintomas_extraidos') or []) or state['queixa']
        fontes = common.rag_search(retriever, f'diferencial diagnóstico {query}',
                                   categoria='ginecologia_obstetricia', k=3)
        contexto = '\n---\n'.join(f['trecho'] for f in fontes) if fontes else '(sem contexto)'
        sistema = (
            'Você é um médico ginecologista. Dada a queixa e o contexto de protocolos, '
            'liste os principais diagnósticos diferenciais. JSON apenas.'
        )
        prompt = (
            f'Queixa: {state["queixa"]}\n'
            f'Sintomas: {state.get("sintomas_extraidos", [])}\n\n'
            f'Contexto de protocolos:\n{contexto[:2500]}\n\n'
            'Responda: {"diferenciais": ["...", "..."]}'
        )
        out = common.llm_json(chat_model, prompt, sistema, default={'diferenciais': []})
        diff = out.get('diferenciais', [])
        rac = state.get('raciocinio', []) + [
            f'Consulta RAG retornou {len(fontes)} trecho(s) do protocolo.',
            f'Diferenciais: {", ".join(diff) or "—"}',
        ]
        return {
            'diferenciais': diff,
            'fontes': fontes,
            'raciocinio': rac,
        }
    return node


def _classificar_urgencia(chat_model):
    def node(state: TriagemState) -> dict:
        queixa_low = state['queixa'].lower()
        alarme = [s for s in SINAIS_EMERGENCIA if s in queixa_low]

        if alarme:
            return {
                'urgencia': 'emergencia',
                'sinais_alarme': alarme,
                'justificativa_urgencia': f'Sinais de alarme detectados: {", ".join(alarme)}',
                'raciocinio': state.get('raciocinio', []) +
                              [f'Urgência = emergência (alarme: {", ".join(alarme)})'],
            }

        # Sem alarme: LLM classifica
        sistema = 'Você é um médico em triagem. Classifique a urgência: emergencia, urgente, agendado ou rotina.'
        prompt = (
            f'Queixa: {state["queixa"]}\n'
            f'Diferenciais: {state.get("diferenciais", [])}\n\n'
            'Responda: {"urgencia": "urgente|agendado|rotina", "justificativa": "..."}'
        )
        out = common.llm_json(chat_model, prompt, sistema,
                             default={'urgencia': 'agendado', 'justificativa': 'sem dados suficientes'})
        return {
            'urgencia': out.get('urgencia', 'agendado'),
            'sinais_alarme': [],
            'justificativa_urgencia': out.get('justificativa', ''),
            'raciocinio': state.get('raciocinio', []) + [f'Urgência = {out.get("urgencia")}'],
        }
    return node


def _sugerir_exames(chat_model, retriever):
    def node(state: TriagemState) -> dict:
        fontes_existentes = state.get('fontes', [])
        novas = common.rag_search(retriever,
                                  f'exames complementares {" ".join(state.get("diferenciais", []))}',
                                  k=2)
        contexto = '\n---\n'.join(f['trecho'] for f in (fontes_existentes + novas))[:2500]
        sistema = 'Você é ginecologista. Liste exames complementares apropriados conforme protocolo.'
        prompt = (
            f'Diferenciais: {state.get("diferenciais", [])}\n'
            f'Contexto:\n{contexto}\n\n'
            'Responda: {"exames": ["beta-hCG", "USG transvaginal", ...]}'
        )
        out = common.llm_json(chat_model, prompt, sistema, default={'exames': []})
        return {
            'exames_sugeridos': out.get('exames', []),
            'fontes': fontes_existentes + novas,
            'raciocinio': state.get('raciocinio', []) +
                          [f'Exames sugeridos: {", ".join(out.get("exames", []))}'],
        }
    return node


def _orientacoes_iniciais(chat_model):
    def node(state: TriagemState) -> dict:
        sistema = ('Você é ginecologista. Forneça orientações iniciais ACIONÁVEIS '
                   'à equipe de triagem, em até 4 linhas, em PT-BR.')
        prompt = (
            f'Queixa: {state["queixa"]}\n'
            f'Urgência: {state.get("urgencia")}\n'
            f'Diferenciais: {state.get("diferenciais", [])}\n'
            f'Exames sugeridos: {state.get("exames_sugeridos", [])}\n\n'
            'Orientações iniciais para a equipe (sem prescrever medicação específica):'
        )
        texto = common.llm_text(chat_model, prompt, sistema)
        return {
            'orientacoes_iniciais': texto,
            'raciocinio': state.get('raciocinio', []) + ['Orientações iniciais geradas.'],
        }
    return node


def _agendamento(state: TriagemState) -> dict:
    """Determinístico: mapeia urgência → especialidade + prazo."""
    urgencia = state.get('urgencia', 'agendado')
    diff_low = ' '.join(state.get('diferenciais', [])).lower()

    if urgencia == 'emergencia':
        ag = {'especialidade': 'Ginecologia/obstetrícia de plantão',
              'prazo': 'imediato (pronto-socorro)'}
    elif urgencia == 'urgente':
        ag = {'especialidade': 'Ginecologia ambulatorial',
              'prazo': 'até 48h'}
    elif urgencia == 'agendado':
        esp = 'Mastologia' if 'mama' in diff_low else 'Ginecologia ambulatorial'
        ag = {'especialidade': esp, 'prazo': 'até 14 dias'}
    else:
        ag = {'especialidade': 'Ginecologia ambulatorial', 'prazo': 'rotina (30-60 dias)'}

    return {
        'agendamento': ag,
        'raciocinio': state.get('raciocinio', []) + [f'Agendamento: {ag["especialidade"]} | {ag["prazo"]}'],
    }


def _compilar_resposta(state: TriagemState) -> dict:
    confianca = common.estimar_confianca(
        n_fontes=len(state.get('fontes', [])),
        n_decisoes_llm=4,
        dados_paciente_disponiveis=state.get('paciente_id') is not None,
    )
    resposta = {
        'urgencia': state.get('urgencia'),
        'sinais_alarme': state.get('sinais_alarme', []),
        'justificativa_urgencia': state.get('justificativa_urgencia'),
        'diferenciais': state.get('diferenciais', []),
        'exames_sugeridos': state.get('exames_sugeridos', []),
        'orientacoes_iniciais': state.get('orientacoes_iniciais'),
        'agendamento': state.get('agendamento'),
        'confianca': confianca,
        'raciocinio': state.get('raciocinio', []),
        'fontes': state.get('fontes', []),
    }
    return {'confianca': confianca, 'resposta_estruturada': resposta}


# ============= GRAPH =============

def _rota_urgencia(state: TriagemState) -> str:
    """Edge condicional: emergência pula sugerir_exames/orientações e vai direto a agendamento."""
    return 'node_agendamento' if state.get('urgencia') == 'emergencia' else 'sugerir_exames'


def build_triagem_workflow(chat_model, conn, retriever):
    """Compila e retorna o StateGraph do fluxo de Triagem Ginecológica.

    `conn` é mantido na assinatura por consistência com os outros workflows,
    mesmo que este não consulte o DB diretamente.
    """
    from langgraph.graph import StateGraph, START, END

    g = StateGraph(TriagemState)
    g.add_node('parse_sintomas', _parse_sintomas(chat_model))
    g.add_node('analisar_risco', _analisar_risco(chat_model, retriever))
    g.add_node('classificar_urgencia', _classificar_urgencia(chat_model))
    g.add_node('sugerir_exames', _sugerir_exames(chat_model, retriever))
    g.add_node('node_orientacoes_iniciais', _orientacoes_iniciais(chat_model))
    g.add_node('node_agendamento', _agendamento)
    g.add_node('compilar_resposta', _compilar_resposta)

    g.add_edge(START, 'parse_sintomas')
    g.add_edge('parse_sintomas', 'analisar_risco')
    g.add_edge('analisar_risco', 'classificar_urgencia')
    g.add_conditional_edges('classificar_urgencia', _rota_urgencia,
                            {'sugerir_exames': 'sugerir_exames',
                             'agendamento':    'node_agendamento'})
    g.add_edge('sugerir_exames', 'node_orientacoes_iniciais')
    g.add_edge('node_orientacoes_iniciais', 'node_agendamento')
    g.add_edge('node_agendamento', 'compilar_resposta')
    g.add_edge('compilar_resposta', END)

    return g.compile()
