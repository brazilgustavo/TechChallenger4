"""Interface Gradio para o assistente clínico.

Layout (com workflows habilitados):
- Sidebar:    profissional, paciente em contexto, painel de alertas
- Tab 1:      Consulta livre (chat com agente LangChain)
- Tab 2:      Triagem Ginecológica (workflow LangGraph)
- Tab 3:      Detecção de Violência (workflow LangGraph) + checklist heurístico
- Tab 4:      Atendimento Obstétrico (workflow LangGraph)
- Tab 5:      Prevenção e Rastreamento (workflow LangGraph)

Se `workflows` não for passado, só Tab 1 e o checklist da Tab 3 aparecem.
"""
from __future__ import annotations

import json
from typing import Any

from . import alertas as alertas_mod
from . import tools as tools_mod


SINAIS_VIOLENCIA = list(alertas_mod.SINAIS_VIOLENCIA.items())


# =============================================================================
# Helpers de sidebar (mantidos do design anterior)
# =============================================================================

def _lista_pacientes(conn) -> list[tuple[str, int]]:
    rows = conn.execute(
        "SELECT paciente_id, nome, data_nascimento FROM pacientes ORDER BY nome"
    ).fetchall()
    out = []
    for r in rows:
        ano_nasc = r['data_nascimento'][:4]
        out.append((f"{r['nome']} (id={r['paciente_id']}, n. {ano_nasc})", r['paciente_id']))
    return out


def _alertas_paciente(conn, paciente_id: int | None) -> str:
    if not paciente_id:
        return '_(selecione uma paciente para ver alertas)_'
    p = tools_mod.consultar_prontuario(paciente_id, conn)
    if 'erro' in p:
        return f'_{p["erro"]}_'

    linhas = [f"### {p['nome']}  —  {p['idade']} anos  ({p['convenio']})"]
    pron = p.get('prontuario_gineco') or {}
    linhas.append(
        f"- DUM: {pron.get('dum') or 'não informado'}  |  "
        f"Método: {pron.get('metodo_contraceptivo') or '—'}  |  "
        f"G/P/A: {pron.get('g_p_a') or '—'}"
    )

    atrasados = tools_mod.exames_atrasados(paciente_id, conn)
    if atrasados:
        linhas.append('\n**⚠ Exames preventivos em atraso:**')
        for a in atrasados:
            tag = '🔴' if a['prioridade'] == 'alta' else '🟡'
            linhas.append(f"- {tag} **{a['tipo']}** — {a['motivo']}")
    else:
        linhas.append('\n✅ Exames preventivos em dia.')

    n_viol = conn.execute(
        'SELECT COUNT(*) AS c FROM registros_violencia WHERE paciente_id = ?',
        (paciente_id,),
    ).fetchone()['c']
    if n_viol > 0:
        linhas.append(
            f'\n🔒 **{n_viol} registro(s) prévio(s) em `registros_violencia`** '
            f'(acesso requer motivo clínico — auditoria LGPD).'
        )
    return '\n'.join(linhas)


# =============================================================================
# Formatadores de output dos workflows (state → Markdown)
# =============================================================================

URGENCIA_ICON = {
    'emergencia': '🚨', 'urgente': '⚠️', 'agendado': '🟡', 'rotina': '✅',
}
RISCO_ICON = {
    'alto_risco': '🔴', 'habitual': '🟢',
    'alta_suspeita': '🚨', 'atencao': '⚠️', 'sem_alerta': '✅',
}
PRIORIDADE_ICON = {'alta': '🔴', 'media': '🟡', 'baixa': '🟢'}


def _render_trace_e_fontes(resp: dict) -> str:
    """Bloco final colapsável com raciocínio + fontes (explainability)."""
    bloco = []
    if resp.get('confianca'):
        bloco.append(f"\n_Confiança estimada: **{resp['confianca']}**_")
    rac = resp.get('raciocinio') or []
    fontes = resp.get('fontes') or []
    if rac or fontes:
        bloco.append('\n<details><summary>🧠 Raciocínio e fontes</summary>\n')
        if rac:
            bloco.append('\n**Trace dos nodes:**')
            for r in rac:
                bloco.append(f'- {r}')
        if fontes:
            bloco.append('\n**Fontes consultadas:**')
            vistos = set()
            for f in fontes:
                doc = f.get('doc_id', '?')
                if doc in vistos:
                    continue
                vistos.add(doc)
                bloco.append(f"- `{doc}` ({f.get('category')})")
        bloco.append('\n</details>')
    return '\n'.join(bloco)


def _render_triagem(state: dict) -> str:
    r = state.get('resposta_estruturada', {})
    urg = r.get('urgencia', '?')
    icon = URGENCIA_ICON.get(urg, '⚪')

    md = [f"## {icon} Urgência: **{urg.upper()}**"]
    if r.get('sinais_alarme'):
        md.append(f"\n**Sinais de alarme detectados:** {', '.join(r['sinais_alarme'])}")
    if r.get('justificativa_urgencia'):
        md.append(f"\n**Justificativa:** {r['justificativa_urgencia']}")

    if r.get('diferenciais'):
        md.append('\n### Diagnósticos diferenciais')
        for d in r['diferenciais']:
            md.append(f'- {d}')

    if r.get('exames_sugeridos'):
        md.append('\n### Exames sugeridos')
        for e in r['exames_sugeridos']:
            md.append(f'- {e}')

    if r.get('orientacoes_iniciais'):
        md.append(f"\n### Orientações iniciais à equipe\n\n{r['orientacoes_iniciais']}")

    ag = r.get('agendamento') or {}
    if ag:
        md.append(f"\n### Agendamento sugerido\n**{ag.get('especialidade')}** — "
                  f"prazo: _{ag.get('prazo')}_")

    md.append(_render_trace_e_fontes(r))
    return '\n'.join(md)


def _render_violencia_wf(state: dict) -> str:
    r = state.get('resposta_estruturada', {})
    nivel = r.get('nivel', '?')
    icon = RISCO_ICON.get(nivel, '⚪')

    md = [f"## {icon} Nível: **{nivel.replace('_', ' ').upper()}**  "
          f"(score: {r.get('score', '?')})"]

    if r.get('sinais_descricoes'):
        md.append('\n**Sinais identificados:**')
        for d in r['sinais_descricoes']:
            md.append(f'- {d}')

    if r.get('protocolo_seguranca_ativado'):
        md.append('\n🔒 **Protocolo de segurança ATIVADO** '
                  '— atendimento em ambiente reservado, sem acompanhante.')
        for m in r.get('medidas') or []:
            md.append(f'- {m}')

    if r.get('conduta_sugerida'):
        md.append(f"\n### Conduta sugerida\n\n{r['conduta_sugerida']}")

    if r.get('equipe_acionada'):
        md.append('\n### Equipe acionada')
        for e in r['equipe_acionada']:
            md.append(f'- {e}')

    if r.get('encaminhamentos'):
        md.append('\n### Encaminhamentos da rede (informar à paciente)')
        for e in r['encaminhamentos']:
            md.append(f'- {e}')

    if r.get('notificacao_sinan'):
        rid = r.get('registro_id')
        md.append(f"\n✅ **Notificação SINAN registrada** (id: `{rid}`) e acesso auditado em `log_acesso`.")
    elif nivel == 'alta_suspeita':
        md.append('\n⚠️ Sem `paciente_id` ou `confirmacao_clinica` → **não foi gerado registro formal**. '
                  'Fazer notificação SINAN em ficha física.')

    seg = r.get('seguimento') or {}
    if seg:
        md.append(f"\n### Seguimento\n**Retorno:** {seg.get('prazo_retorno', '—')}  ")
        if seg.get('profissionais_envolvidos'):
            md.append(f"**Profissionais:** {', '.join(seg['profissionais_envolvidos'])}")
        if seg.get('orientacoes'):
            md.append(f"\n{seg['orientacoes']}")

    md.append(_render_trace_e_fontes(r))
    return '\n'.join(md)


def _render_obstetrico(state: dict) -> str:
    r = state.get('resposta_estruturada', {})
    risco = r.get('classificacao_risco', '?')
    icon = RISCO_ICON.get(risco, '⚪')

    md = [f"## {icon} Risco gestacional: **{risco.replace('_', ' ').upper()}**"]

    dg = r.get('dados_gestante') or {}
    if dg:
        md.append(f"\n**IG:** {dg.get('ig_semanas', '?')} semanas  |  "
                  f"**Paridade:** {dg.get('paridade', '—')}  |  "
                  f"**Antecedentes:** {', '.join(dg.get('antecedentes', [])) or '—'}")

    if r.get('fatores_risco_identificados'):
        md.append('\n**Fatores de risco identificados:**')
        for f in r['fatores_risco_identificados']:
            md.append(f'- {f}')

    if r.get('eh_emergencia'):
        md.append('\n🚨 **EMERGÊNCIA OBSTÉTRICA — encaminhamento imediato ao PS obstétrico.**')
        md.append('\n**Sinais de alarme detectados:**')
        for a in r.get('alertas_urgencia', []):
            md.append(f'- {a}')

    if r.get('orientacoes_especificas'):
        md.append(f"\n### Orientações à equipe\n\n{r['orientacoes_especificas']}")

    if r.get('exames_agendados'):
        md.append('\n### Exames agendados (rotina por IG e risco)')
        for ex in r['exames_agendados']:
            md.append(f"- **{ex['exame']}** — {ex['prazo']}")

    ac = r.get('acompanhamento') or {}
    if ac:
        md.append(f"\n### Acompanhamento\n"
                  f"**{ac.get('periodicidade')}** — próxima consulta em "
                  f"**{ac.get('proxima_consulta_em_dias')} dias**")
        if ac.get('profissionais_envolvidos'):
            md.append(f"_{', '.join(ac['profissionais_envolvidos'])}_")

    md.append(_render_trace_e_fontes(r))
    return '\n'.join(md)


def _render_prevencao(state: dict) -> str:
    r = state.get('resposta_estruturada', {})
    perfil = r.get('perfil') or {}

    md = [f"## Plano preventivo — {perfil.get('nome', '?')} "
          f"({perfil.get('idade', '?')}a)"]

    atrasados = r.get('exames_atrasados', [])
    devidos = r.get('exames_devidos', [])
    if not devidos:
        md.append('\n✅ **Paciente em dia com todos os rastreamentos populacionais.** '
                  'Manter periodicidade.')
    else:
        if atrasados:
            md.append('\n### ⚠️ Exames em atraso')
            for a in atrasados:
                icon = PRIORIDADE_ICON.get(a.get('prioridade', ''), '⚪')
                md.append(f"- {icon} **{a['exame']}** — {a['motivo']}")
        a_vencer = [d for d in devidos if d.get('status') == 'a_vencer']
        if a_vencer:
            md.append('\n### 📅 A vencer (próximos 90 dias)')
            for d in a_vencer:
                md.append(f"- **{d['exame']}** — {d['motivo']}")

    if r.get('orientacoes_preventivas'):
        md.append(f"\n### Orientações preventivas\n\n{r['orientacoes_preventivas']}")

    if r.get('agendamentos_propostos'):
        md.append('\n### Agendamentos propostos')
        for ag in r['agendamentos_propostos']:
            md.append(f"- **{ag['exame']}** → {ag['especialidade']} | "
                      f"data: {ag['data_proposta']} (prioridade {ag['prioridade']})")

    if r.get('lembretes'):
        md.append('\n### Mensagens de lembrete (para envio)')
        for lb in r['lembretes']:
            md.append(f"- _[{lb.get('canal', 'sms')}]_ {lb.get('texto', '')}")

    md.append(_render_trace_e_fontes(r))
    return '\n'.join(md)


def _render_risco_ml(state: dict) -> str:
    r = state.get('resposta_estruturada') or state
    modo = r.get('modo') or '?'
    md = [f'## Risco gestacional (ML) — modo `{modo}`']
    if modo == 'degradado':
        md.append('\n⚠️ **Modo degradado:** o modelo supervisionado não estava disponível. '
                  'A classificação abaixo veio da regra determinística `CRITERIOS_ALTO_RISCO`.')
    if modo == 'bypass_regra':
        md.append('\n🚨 **Encaminhamento imediato** por sinal de alarme obstétrico. O modelo não foi executado.')
    if r.get('requer_intervencao_humana'):
        iv = r.get('intervencao') or {}
        md.append('\n### Dados incompletos')
        md.append(iv.get('pergunta') or 'Completar campos obrigatórios.')
        if r.get('campos_faltantes'):
            md.append('**Campos:** ' + ', '.join(r['campos_faltantes']))
    if r.get('erros_validacao'):
        md.append('\n### Erros de validação')
        for e in r['erros_validacao']:
            md.append(f"- `{e.get('campo')}`: {e.get('mensagem')}")
    pred = r.get('prediction')
    if pred:
        md.append(f'\n**Classificação:** `{pred}`')
    probs = r.get('probabilities') or {}
    if probs:
        md.append(
            f"**Probabilidade alto risco:** {probs.get('alto_risco')}  |  "
            f"**Limiar operacional:** {r.get('threshold')}"
        )
    elif r.get('threshold') is not None:
        md.append(f'**Limiar:** {r.get("threshold")}')
    if r.get('regras_disparadas'):
        md.append('\n**Regras de alarme disparadas:**')
        for x in r['regras_disparadas']:
            md.append(f'- {x}')
    if r.get('top_features'):
        md.append('\n**Variáveis que mais contribuíram para esta classificação:**')
        for t in r['top_features']:
            md.append(f"- `{t.get('feature')}` ({t.get('direction')}): {t.get('contribution')}")
    if r.get('dados_imputados'):
        md.append('\n**Campos opcionais imputados:** ' + ', '.join(r['dados_imputados']))
    fontes = r.get('fontes') or []
    if fontes:
        md.append('\n**Fontes recuperadas:**')
        for f in fontes:
            md.append(f"- `{f.get('doc_id')}` ({f.get('category')})")
    else:
        md.append('\n_Nenhuma fonte documental recuperada nesta execução._')
    if r.get('resposta_texto'):
        md.append('\n### Síntese\n')
        md.append(r['resposta_texto'])
    md.append('\n' + (r.get('safety_notice') or ''))
    md.append(r.get('aviso_dados_sinteticos') or '')
    if r.get('raciocinio'):
        md.append('\n<details><summary>Trace</summary>\n')
        for linha in r['raciocinio']:
            md.append(f'- {linha}')
        md.append('\n</details>')
    return '\n'.join(md)


# =============================================================================
# UI principal
# =============================================================================

def build_ui(agent, conn, default_usuario: str = 'sessao_demo',
             workflows: dict | None = None):
    """Constroi e devolve um `gr.Blocks` pronto para `.launch()`.

    Args:
        agent: agente LangChain (do `lib.agent.build_agent`)
        conn: conexão SQLite
        default_usuario: identificador do profissional na sessão
        workflows: dict opcional com chaves 'triagem', 'violencia', 'obstetrico',
                   'prevencao' apontando para os workflows LangGraph compilados.
                   Se omitido, só as tabs Consulta livre e checklist aparecem.
    """
    try:
        import gradio as gr
    except ImportError as e:
        raise ImportError('gradio não instalado. Rode: pip install gradio') from e

    from .agent import run_consulta

    workflows = workflows or {}
    wf_triagem    = workflows.get('triagem')
    wf_violencia  = workflows.get('violencia')
    wf_obstetrico = workflows.get('obstetrico')
    wf_prevencao  = workflows.get('prevencao')
    wf_risco_ml   = workflows.get('risco_ml')

    pacientes_choices = _lista_pacientes(conn)
    historico_estado: dict[str, Any] = {'mensagens': []}

    # ---- handlers da sidebar e do chat livre ----

    def on_usuario_change(novo):
        tools_mod.set_usuario_atual(novo.strip() or 'sessao_demo')
        return f'Profissional ativo: `{tools_mod.get_usuario_atual()}`'

    def on_paciente_change(pid):
        return _alertas_paciente(conn, pid)

    def on_chat(mensagem: str, chat_history: list, paciente_id):
        if not mensagem.strip():
            return chat_history, ''
        out = run_consulta(
            agent,
            pergunta=mensagem,
            paciente_id=paciente_id,
            historico=historico_estado['mensagens'],
        )
        historico_estado['mensagens'] = out['mensagens']

        resposta = out['resposta']
        if out['tool_calls']:
            tc_lines = ['\n\n<details><summary>🔧 Ferramentas usadas</summary>\n']
            for c in out['tool_calls']:
                args_str = ', '.join(f'{k}={v!r}' for k, v in (c.get('args') or {}).items())
                tc_lines.append(f'- `{c["tool"]}({args_str})`')
            tc_lines.append('\n</details>')
            resposta = resposta + '\n'.join(tc_lines)

        # Gradio 6.0 messages format: lista de dicts {role, content}
        chat_history = chat_history + [
            {'role': 'user', 'content': mensagem},
            {'role': 'assistant', 'content': resposta},
        ]
        return chat_history, ''

    def on_limpar():
        historico_estado['mensagens'] = []
        return [], ''

    # ---- handler do checklist heurístico de violência ----

    def on_checklist_violencia(*sinais_checked):
        sinais_ativos = [chave for (chave, _), check in zip(SINAIS_VIOLENCIA, sinais_checked) if check]
        if not sinais_ativos:
            return '_(selecione ao menos um sinal observado)_'
        av = tools_mod.avaliar_padrao_violencia(sinais_ativos)
        out = [f'## Avaliação heurística\n',
               f'**Score:** {av["score"]}  |  **Nível:** `{av["nivel"]}`']
        out.append('\n**Sinais presentes:**')
        for d in av['sinais_descricoes']:
            out.append(f'- {d}')
        out.append(f'\n**Conduta sugerida:**\n\n{av["conduta_sugerida"]}')
        if av['encaminhamentos']:
            out.append('\n**Encaminhamentos:**')
            for e in av['encaminhamentos']:
                out.append(f'- {e}')
        return '\n'.join(out)

    # ---- handlers dos 4 workflows LangGraph ----

    def on_wf_triagem(queixa, paciente_id):
        if not queixa or not queixa.strip():
            return '_(digite a queixa principal)_'
        if wf_triagem is None:
            return '⚠️ Workflow não disponível — passe `workflows={"triagem": ...}` em `build_ui`.'
        state = wf_triagem.invoke({'queixa': queixa, 'paciente_id': paciente_id})
        return _render_triagem(state)

    def on_wf_violencia(descricao, paciente_id, confirmacao):
        if not descricao or not descricao.strip():
            return '_(digite a descrição do caso clínico)_'
        if wf_violencia is None:
            return '⚠️ Workflow não disponível.'
        prof = tools_mod.get_usuario_atual()
        state = wf_violencia.invoke({
            'descricao_caso': descricao,
            'paciente_id': paciente_id,
            'profissional': prof,
            'confirmacao_clinica': bool(confirmacao),
        })
        return _render_violencia_wf(state)

    def on_wf_obstetrico(descricao, ig_semanas, paciente_id):
        if not descricao or not descricao.strip():
            return '_(digite a descrição clínica)_'
        if wf_obstetrico is None:
            return '⚠️ Workflow não disponível.'
        payload = {'descricao_caso': descricao, 'paciente_id': paciente_id}
        if ig_semanas and int(ig_semanas) > 0:
            payload['ig_semanas'] = int(ig_semanas)
        state = wf_obstetrico.invoke(payload)
        return _render_obstetrico(state)

    def on_wf_prevencao(paciente_id):
        if not paciente_id:
            return '_(selecione uma paciente na sidebar primeiro)_'
        if wf_prevencao is None:
            return '⚠️ Workflow não disponível.'
        state = wf_prevencao.invoke({'paciente_id': paciente_id})
        return _render_prevencao(state)

    def on_wf_risco_ml(payload_json, descricao, forcar_deg, paciente_id):
        if wf_risco_ml is None:
            return '⚠️ Workflow não disponível.'
        try:
            dados = json.loads(payload_json or '{}')
        except json.JSONDecodeError as exc:
            return f'JSON inválido: {exc}'
        try:
            state = wf_risco_ml.invoke({
                'dados_clinicos': dados,
                'descricao_clinica': descricao or '',
                'paciente_id': paciente_id,
                'usuario': tools_mod.get_usuario_atual(),
                'forcar_degradado': bool(forcar_deg),
            })
            return _render_risco_ml(state)
        except Exception as exc:  # noqa: BLE001 — CA / RNF-17
            return (
                'Não foi possível concluir a estratificação. '
                'Revise o payload (11 campos obrigatórios) e tente de novo. '
                f'Detalhe técnico: `{type(exc).__name__}`.'
            )

    def on_carregar_paciente_ml(paciente_id):
        if not paciente_id:
            return (
                '{\n'
                '  "idade": 28,\n'
                '  "imc_pre_gestacional": 24.0,\n'
                '  "ig_semanas": 22,\n'
                '  "gestacoes": 2,\n'
                '  "partos": 1,\n'
                '  "abortos": 0,\n'
                '  "pas_mmhg": 118,\n'
                '  "pad_mmhg": 72,\n'
                '  "has_cronica": false,\n'
                '  "diabetes_previo": false,\n'
                '  "gemelaridade": false\n'
                '}'
            )
        try:
            from .ml.schema import features_de_paciente
            payload, ausentes = features_de_paciente(conn, int(paciente_id))
            defaults = {
                'imc_pre_gestacional': 24.0,
                'pas_mmhg': 120,
                'pad_mmhg': 80,
                'has_cronica': False,
                'diabetes_previo': False,
                'gemelaridade': False,
            }
            for k, v in defaults.items():
                if k not in payload:
                    payload[k] = v
            return json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception as exc:
            return f'// Erro ao carregar paciente {paciente_id}: {exc}'

    # ---- layout ----

    css = """
    /* Garantir contraste e legibilidade no tema claro */
    .alertas-box {
        background-color: #fffaf0 !important;
        color: #78350f !important;
        padding: 12px;
        border-left: 4px solid #d97706;
        border-radius: 4px;
    }
    .alertas-box, .alertas-box *, .alertas-box p, .alertas-box span, .alertas-box div {
        color: #78350f !important;
    }

    .out-box {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        padding: 16px;
        border-left: 4px solid #2563eb;
        border-radius: 4px;
        min-height: 200px;
    }
    .out-box, .out-box *, .out-box p, .out-box h1, .out-box h2, .out-box h3, .out-box h4,
    .out-box li, .out-box span, .out-box div, .out-box summary, .out-box details, .out-box strong {
        color: #0f172a !important;
    }
    .out-box code {
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
    }

    /* Garantir contraste e legibilidade no tema escuro (Dark Mode) */
    .dark .alertas-box, [data-theme='dark'] .alertas-box {
        background-color: #2d2006 !important;
        color: #fef3c7 !important;
        border-left: 4px solid #f59e0b;
    }
    .dark .alertas-box *, [data-theme='dark'] .alertas-box * {
        color: #fef3c7 !important;
    }

    .dark .out-box, [data-theme='dark'] .out-box {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border-left: 4px solid #3b82f6;
    }
    .dark .out-box *, [data-theme='dark'] .out-box *,
    .dark .out-box p, .dark .out-box h1, .dark .out-box h2, .dark .out-box h3, .dark .out-box h4,
    .dark .out-box li, .dark .out-box span, .dark .out-box div, .dark .out-box summary, .dark .out-box details, .dark .out-box strong {
        color: #f8fafc !important;
    }
    .dark .out-box code {
        background-color: #334155 !important;
        color: #38bdf8 !important;
    }

    /* Correção global para inputs e textareas */
    input, textarea, select {
        color: var(--body-text-color) !important;
    }
    """

    with gr.Blocks(title='Assistente Clínico — Saúde da Mulher',
                   theme=gr.themes.Soft(), css=css) as app:
        gr.Markdown(
            '# Assistente Clínico — Saúde da Mulher\n'
            '_Apoio à equipe de saúde do hospital. Não substitui avaliação clínica._'
        )

        with gr.Row():
            # ---- Sidebar ----
            with gr.Column(scale=1):
                gr.Markdown('### Sessão')
                usuario = gr.Textbox(
                    label='Profissional logado',
                    value=default_usuario,
                    info='Identificador registrado em log_acesso (LGPD)',
                )
                usuario_status = gr.Markdown(f'Profissional ativo: `{default_usuario}`')

                gr.Markdown('### Paciente em contexto')
                paciente = gr.Dropdown(
                    choices=pacientes_choices,
                    label='Paciente',
                    value=None,
                    interactive=True,
                )

                alertas_md = gr.Markdown(
                    '_(selecione uma paciente)_',
                    elem_classes='alertas-box',
                )

                usuario.change(on_usuario_change, inputs=usuario, outputs=usuario_status)
                paciente.change(on_paciente_change, inputs=paciente, outputs=alertas_md)

            # ---- Main ----
            with gr.Column(scale=3):
                with gr.Tabs():

                    # === TAB 1 — Chat livre ===
                    with gr.Tab('💬 Consulta livre'):
                        gr.Markdown(
                            '_Pergunta livre ao assistente, que escolhe quais '
                            'ferramentas chamar e cita protocolos quando aplicável._'
                        )
                        chatbot = gr.Chatbot(type='messages', height=460, label='Diálogo clínico')
                        with gr.Row():
                            entrada = gr.Textbox(
                                placeholder='Ex.: Conduta em LSIL em paciente <25a; '
                                            'posologia de misoprostol p/ aborto retido',
                                lines=2, scale=8, show_label=False,
                            )
                            enviar = gr.Button('Enviar', scale=1, variant='primary')
                        with gr.Row():
                            limpar = gr.Button('Limpar conversa', size='sm')

                        enviar.click(on_chat, inputs=[entrada, chatbot, paciente],
                                    outputs=[chatbot, entrada])
                        entrada.submit(on_chat, inputs=[entrada, chatbot, paciente],
                                      outputs=[chatbot, entrada])
                        limpar.click(on_limpar, outputs=[chatbot, entrada])

                    # === TAB 2 — Triagem Ginecológica ===
                    with gr.Tab('🩺 Triagem Ginecológica'):
                        gr.Markdown(
                            '**Fluxo LangGraph:** queixa → análise de risco (RAG) → '
                            'classificação de urgência → exames sugeridos → '
                            'orientações → agendamento.'
                        )
                        tri_queixa = gr.Textbox(
                            label='Queixa principal (texto livre)', lines=4,
                            placeholder='Ex.: Paciente 32a, sangramento intenso há 3 dias, '
                                        'dor pélvica forte irradiando para ombro, '
                                        'atraso menstrual de 8 semanas.',
                        )
                        tri_btn = gr.Button('Realizar triagem', variant='primary')
                        tri_out = gr.Markdown(elem_classes='out-box')
                        tri_btn.click(on_wf_triagem,
                                     inputs=[tri_queixa, paciente],
                                     outputs=tri_out)

                    # === TAB 3 — Detecção de Violência ===
                    with gr.Tab('🛡️ Detecção de Violência'):
                        with gr.Tabs():
                            with gr.Tab('Workflow completo (LangGraph)'):
                                gr.Markdown(
                                    '**Fluxo LangGraph:** extração de sinais → '
                                    'matriz determinística → protocolo de segurança → '
                                    'equipe acionada → SINAN + log_acesso.'
                                )
                                vio_desc = gr.Textbox(
                                    label='Descrição do caso clínico', lines=5,
                                    placeholder='Ex.: Paciente 28a comparece com lesões '
                                                'equimóticas em locais não-expostos, '
                                                'em múltiplas fases de cicatrização. '
                                                'Acompanhante recusou deixar a paciente '
                                                'sozinha. Histórico de 3 atendimentos '
                                                'prévios. Isolamento social progressivo.',
                                )
                                vio_confirm = gr.Checkbox(
                                    label='Confirmação clínica (autoriza registro SINAN no DB)',
                                    value=False,
                                )
                                vio_btn = gr.Button('Avaliar e registrar', variant='primary')
                                vio_out = gr.Markdown(elem_classes='out-box')
                                vio_btn.click(on_wf_violencia,
                                             inputs=[vio_desc, paciente, vio_confirm],
                                             outputs=vio_out)

                            with gr.Tab('Checklist heurístico (rápido)'):
                                gr.Markdown(
                                    'Selecione sinais clínicos observados. '
                                    'Avaliação determinística sem LLM.'
                                )
                                sinais_checks = []
                                with gr.Row():
                                    with gr.Column():
                                        for chave, desc in SINAIS_VIOLENCIA[:6]:
                                            sinais_checks.append(
                                                gr.Checkbox(label=desc, value=False))
                                    with gr.Column():
                                        for chave, desc in SINAIS_VIOLENCIA[6:]:
                                            sinais_checks.append(
                                                gr.Checkbox(label=desc, value=False))
                                cl_btn = gr.Button('Avaliar checklist', variant='primary')
                                cl_out = gr.Markdown(elem_classes='out-box')
                                cl_btn.click(on_checklist_violencia,
                                            inputs=sinais_checks, outputs=cl_out)

                    # === TAB 4 — Obstétrico ===
                    with gr.Tab('🤰 Atendimento Obstétrico'):
                        gr.Markdown(
                            '**Fluxo LangGraph:** dados gestante → risco gestacional → '
                            'detecção de alarmes (MS/FEBRASGO) → orientações → '
                            'exames de rotina por IG → acompanhamento.'
                        )
                        obs_desc = gr.Textbox(
                            label='Descrição clínica', lines=5,
                            placeholder='Ex.: Gestante 34a, G3P2A0, IG 32 semanas pela DUM. '
                                        'Quadro de cefaleia intensa há 24h, escotomas, '
                                        'edema súbito de face, dor epigástrica em barra. '
                                        'HAS gestacional diagnosticada na semana 28.',
                        )
                        obs_ig = gr.Number(
                            label='IG (semanas) — opcional, será extraído da descrição se vazio',
                            value=None, precision=0,
                        )
                        obs_btn = gr.Button('Avaliar gestação', variant='primary')
                        obs_out = gr.Markdown(elem_classes='out-box')
                        obs_btn.click(on_wf_obstetrico,
                                     inputs=[obs_desc, obs_ig, paciente],
                                     outputs=obs_out)

                    # === TAB 5 — Prevenção ===
                    with gr.Tab('📅 Prevenção e Rastreamento'):
                        gr.Markdown(
                            '**Fluxo LangGraph:** histórico → exames devidos '
                            '(regras MS: papanicolau, mamografia) → orientações → '
                            'agendamento automático → lembretes.'
                        )
                        gr.Markdown(
                            '⚠️ **Selecione uma paciente na sidebar** antes de gerar o plano.'
                        )
                        prev_btn = gr.Button('Gerar plano preventivo', variant='primary')
                        prev_out = gr.Markdown(elem_classes='out-box')
                        prev_btn.click(on_wf_prevencao,
                                      inputs=[paciente], outputs=prev_out)

                    # === TAB 6 — Risco Gestacional (ML) ===
                    with gr.Tab('📈 Risco Gestacional (ML)'):
                        gr.Markdown(
                            '**Campos obrigatórios (11):** `idade`, `imc_pre_gestacional`, '
                            '`ig_semanas`, `gestacoes`, `partos`, `abortos`, `pas_mmhg`, '
                            '`pad_mmhg`, `has_cronica`, `diabetes_previo`, `gemelaridade`.\n\n'
                            'Opcionais podem faltar (imputados). Obrigatórios ausentes **não** são imputados.\n\n'
                            '_Resultado de apoio à decisão. Dados sintéticos. Não substitui avaliação clínica._'
                        )
                        with gr.Row():
                            ml_load_btn = gr.Button(
                                '📂 Carregar dados da paciente selecionada (sidebar)',
                                size='sm',
                            )
                        ml_json = gr.Textbox(
                            label='Payload JSON das features',
                            lines=12,
                            value=(
                                '{\n'
                                '  "idade": 28,\n'
                                '  "imc_pre_gestacional": 24.0,\n'
                                '  "ig_semanas": 22,\n'
                                '  "gestacoes": 2,\n'
                                '  "partos": 1,\n'
                                '  "abortos": 0,\n'
                                '  "pas_mmhg": 118,\n'
                                '  "pad_mmhg": 72,\n'
                                '  "has_cronica": false,\n'
                                '  "diabetes_previo": false,\n'
                                '  "gemelaridade": false\n'
                                '}'
                            ),
                        )
                        ml_load_btn.click(
                            on_carregar_paciente_ml,
                            inputs=[paciente],
                            outputs=[ml_json],
                        )
                        ml_desc = gr.Textbox(
                            label='Descrição clínica (regras de alarme)',
                            lines=3,
                            placeholder='Opcional. Ex.: cefaleia intensa, escotomas, epigastralgia.',
                        )
                        ml_deg = gr.Checkbox(label='Forçar modo degradado (demo)', value=False)
                        ml_btn = gr.Button('Estratificar risco', variant='primary')
                        ml_out = gr.Markdown(elem_classes='out-box')
                        ml_btn.click(
                            on_wf_risco_ml,
                            inputs=[ml_json, ml_desc, ml_deg, paciente],
                            outputs=ml_out,
                        )

        gr.Markdown(
            '\n_Dados clínicos sintéticos. Acesso a registros de violência auditado '
            'em `log_acesso` (LGPD). Tech Challenge FIAP — Fase 3._'
        )

    return app
