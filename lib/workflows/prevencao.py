"""Fluxo de Prevenção e Rastreamento.

Diagrama:

    START
      ↓
    carregar_historico        (consultar_prontuario + historico_exames)
      ↓
    identificar_exames_devidos (regras MS — papanicolau, mamografia)
      ↓
    orientacoes_preventivas    (LLM gera, baseado no perfil + RAG)
      ↓
    agendar_automaticamente    (propõe slot + especialidade por exame)
      ↓
    gerar_lembretes            (LLM redige mensagens curtas pra equipe entregar)
      ↓
    compilar_resposta
      ↓
     END

Esse fluxo é determinístico no core (regras de rastreamento são objetivas),
o LLM só gera linguagem para orientações e lembretes.
"""
from __future__ import annotations

from datetime import timedelta
from typing import TypedDict

from lib.config import REFERENCE_DATE

from . import common
from .. import tools as tools_mod
from .. import alertas as alertas_mod

TODAY = REFERENCE_DATE


class PrevencaoState(TypedDict, total=False):
    # Inputs
    paciente_id: int

    # Intermediários
    perfil: dict                # prontuário consolidado
    exames_historicos: list[dict]
    exames_atrasados: list[dict]
    exames_devidos: list[dict]  # = exames_atrasados + futuras recomendações
    orientacoes_preventivas: str
    agendamentos_propostos: list[dict]
    lembretes: list[dict]       # {canal, texto}

    # Explainability
    raciocinio: list[str]
    fontes: list[dict]
    confianca: str

    # Output
    resposta_estruturada: dict


# ============= NODES =============

def _carregar_historico(state: PrevencaoState, conn) -> dict:
    pid = state.get('paciente_id')
    if not pid:
        return {
            'perfil': {'erro': 'paciente_id obrigatório'},
            'exames_historicos': [],
            'raciocinio': ['ERRO: paciente_id ausente'],
        }
    perfil = tools_mod.consultar_prontuario(pid, conn)
    exames = tools_mod.historico_exames(pid, conn)
    return {
        'perfil': perfil,
        'exames_historicos': exames,
        'raciocinio': [f'Perfil: {perfil.get("nome", "?")} ({perfil.get("idade", "?")}a). '
                       f'{len(exames)} exame(s) no histórico.'],
    }


def _identificar_exames_devidos(state: PrevencaoState, conn) -> dict:
    """Determinístico — usa alertas_mod.exames_atrasados + projeção de próximos."""
    pid = state.get('paciente_id')
    if not pid:
        return {'exames_atrasados': [], 'exames_devidos': []}

    atrasados_raw = alertas_mod.exames_atrasados(conn, pid)
    atrasados = [{
        'exame': a.tipo,
        'status': 'atrasado',
        'ultima_data': a.ultima_data.isoformat() if a.ultima_data else None,
        'motivo': a.motivo,
        'prioridade': a.prioridade,
    } for a in atrasados_raw]

    # Projeção de próximas datas para exames em dia
    idade = state.get('perfil', {}).get('idade', 0)
    devidos = list(atrasados)

    # Recomendações futuras: se mamografia OK mas próxima vence em <90 dias, avisa
    if 50 <= idade <= 69:
        ultima_mamo = conn.execute(
            "SELECT proximo_recomendado FROM exames "
            "WHERE paciente_id = ? AND tipo = 'mamografia' "
            "ORDER BY data_realizacao DESC LIMIT 1", (pid,),
        ).fetchone()
        if ultima_mamo and ultima_mamo['proximo_recomendado']:
            prox = date.fromisoformat(ultima_mamo['proximo_recomendado'])
            dias = (prox - TODAY).days
            if 0 < dias <= 90 and not any(d['exame'] == 'mamografia' for d in devidos):
                devidos.append({
                    'exame': 'mamografia',
                    'status': 'a_vencer',
                    'ultima_data': None,
                    'motivo': f'Mamografia bienal vence em {dias} dias',
                    'prioridade': 'media',
                })

    if 25 <= idade <= 64:
        ultima_papa = conn.execute(
            "SELECT proximo_recomendado FROM exames "
            "WHERE paciente_id = ? AND tipo = 'papanicolau' "
            "ORDER BY data_realizacao DESC LIMIT 1", (pid,),
        ).fetchone()
        if ultima_papa and ultima_papa['proximo_recomendado']:
            prox = date.fromisoformat(ultima_papa['proximo_recomendado'])
            dias = (prox - TODAY).days
            if 0 < dias <= 90 and not any(d['exame'] == 'papanicolau' for d in devidos):
                devidos.append({
                    'exame': 'papanicolau',
                    'status': 'a_vencer',
                    'ultima_data': None,
                    'motivo': f'Citologia trienal vence em {dias} dias',
                    'prioridade': 'media',
                })

    return {
        'exames_atrasados': atrasados,
        'exames_devidos': devidos,
        'raciocinio': state.get('raciocinio', []) +
                      [f'{len(atrasados)} atrasado(s), {len(devidos) - len(atrasados)} a vencer.'],
    }


def _orientacoes_preventivas(chat_model, retriever):
    def node(state: PrevencaoState) -> dict:
        if not state.get('exames_devidos'):
            return {
                'orientacoes_preventivas': 'Paciente em dia com rastreamentos populacionais. Manter periodicidade.',
                'fontes': [],
                'raciocinio': state.get('raciocinio', []) + ['Sem exames pendentes — orientação de manutenção.'],
            }

        devidos_str = ', '.join(d['exame'] for d in state['exames_devidos'])
        fontes = common.rag_search(
            retriever,
            f'rastreamento {devidos_str} mulher',
            categoria='cancer_mama_colo', k=3,
        )
        contexto = '\n---\n'.join(f['trecho'] for f in fontes)[:2500]
        perfil = state.get('perfil', {})

        sistema = ('Você é ginecologista. Forneça orientações preventivas curtas (3-5 bullets) '
                   'para a equipe entregar à paciente, em linguagem clara mas técnica.')
        prompt = (
            f'Paciente: {perfil.get("idade")}a, '
            f'método contraceptivo: {perfil.get("prontuario_gineco", {}).get("metodo_contraceptivo", "—")}, '
            f'histórico familiar: {perfil.get("prontuario_gineco", {}).get("historico_familiar", "—")}\n'
            f'Exames devidos: {state["exames_devidos"]}\n\n'
            f'Contexto:\n{contexto}\n\n'
            'Orientações preventivas (bullets):'
        )
        texto = common.llm_text(chat_model, prompt, sistema)
        return {
            'orientacoes_preventivas': texto,
            'fontes': fontes,
            'raciocinio': state.get('raciocinio', []) + ['Orientações preventivas geradas.'],
        }
    return node


def _agendar_automaticamente(state: PrevencaoState) -> dict:
    """Determinístico: propõe agendamento por exame, com prazo conforme prioridade."""
    propostas = []
    for d in state.get('exames_devidos', []):
        if d['prioridade'] == 'alta':
            prazo = (TODAY + timedelta(days=14)).isoformat()
            esp = 'Ginecologia (encaixe)'
        elif d['prioridade'] == 'media':
            prazo = (TODAY + timedelta(days=45)).isoformat()
            esp = 'Ginecologia ambulatorial'
        else:
            prazo = (TODAY + timedelta(days=90)).isoformat()
            esp = 'Coleta/imagem ambulatorial'

        # Sala específica
        if d['exame'] == 'mamografia':
            esp = 'Mastologia / radiologia'
        elif d['exame'] == 'papanicolau':
            esp = 'Ginecologia (coleta de citologia)'

        propostas.append({
            'exame': d['exame'],
            'data_proposta': prazo,
            'especialidade': esp,
            'prioridade': d['prioridade'],
        })
    return {
        'agendamentos_propostos': propostas,
        'raciocinio': state.get('raciocinio', []) +
                      [f'{len(propostas)} agendamento(s) proposto(s).'],
    }


def _gerar_lembretes(chat_model):
    def node(state: PrevencaoState) -> dict:
        agendamentos = state.get('agendamentos_propostos', [])
        if not agendamentos:
            return {
                'lembretes': [],
                'raciocinio': state.get('raciocinio', []) + ['Sem agendamentos — sem lembretes.'],
            }

        perfil = state.get('perfil', {})
        nome = perfil.get('nome', 'a paciente')

        sistema = ('Você redige mensagens curtas e claras para lembretes de exames preventivos. '
                   'Use linguagem cordial, em PT-BR, máximo 2 linhas por mensagem.')
        prompt = (
            f'Para {nome}, gere uma mensagem de lembrete CURTA para cada agendamento:\n'
            f'{agendamentos}\n\n'
            'Responda: {"lembretes": [{"canal": "sms|whatsapp|email", "texto": "..."}]}'
        )
        out = common.llm_json(chat_model, prompt, sistema, default={'lembretes': []})
        lembretes = out.get('lembretes', [])

        # Garante pelo menos um lembrete por agendamento se LLM falhou
        if len(lembretes) < len(agendamentos):
            for a in agendamentos:
                lembretes.append({
                    'canal': 'sms',
                    'texto': (f'Olá {nome.split()[0] if nome != "a paciente" else ""}, '
                              f'lembrete: {a["exame"]} agendado para {a["data_proposta"]} '
                              f'({a["especialidade"]}). Confirme presença.'),
                })

        return {
            'lembretes': lembretes,
            'raciocinio': state.get('raciocinio', []) +
                          [f'{len(lembretes)} lembrete(s) gerado(s).'],
        }
    return node


def _compilar_resposta(state: PrevencaoState) -> dict:
    confianca = common.estimar_confianca(
        n_fontes=len(state.get('fontes', [])),
        n_decisoes_llm=2,
        dados_paciente_disponiveis=state.get('paciente_id') is not None,
    )
    resposta = {
        'perfil': state.get('perfil', {}),
        'exames_atrasados': state.get('exames_atrasados', []),
        'exames_devidos': state.get('exames_devidos', []),
        'orientacoes_preventivas': state.get('orientacoes_preventivas'),
        'agendamentos_propostos': state.get('agendamentos_propostos', []),
        'lembretes': state.get('lembretes', []),
        'confianca': confianca,
        'raciocinio': state.get('raciocinio', []),
        'fontes': state.get('fontes', []),
    }
    return {'confianca': confianca, 'resposta_estruturada': resposta}


# ============= GRAPH =============

def build_prevencao_workflow(chat_model, conn, retriever):
    """Compila o StateGraph do fluxo de Prevenção."""
    from langgraph.graph import StateGraph, START, END

    g = StateGraph(PrevencaoState)
    g.add_node('carregar_historico', lambda s: _carregar_historico(s, conn))
    g.add_node('identificar_exames_devidos', lambda s: _identificar_exames_devidos(s, conn))
    g.add_node('gerar_orientacoes_preventivas', _orientacoes_preventivas(chat_model, retriever))
    g.add_node('agendar_automaticamente', _agendar_automaticamente)
    g.add_node('gerar_lembretes', _gerar_lembretes(chat_model))
    g.add_node('compilar_resposta', _compilar_resposta)

    g.add_edge(START, 'carregar_historico')
    g.add_edge('carregar_historico', 'identificar_exames_devidos')
    g.add_edge('identificar_exames_devidos', 'gerar_orientacoes_preventivas')
    g.add_edge('gerar_orientacoes_preventivas', 'agendar_automaticamente')
    g.add_edge('agendar_automaticamente', 'gerar_lembretes')
    g.add_edge('gerar_lembretes', 'compilar_resposta')
    g.add_edge('compilar_resposta', END)

    return g.compile()
