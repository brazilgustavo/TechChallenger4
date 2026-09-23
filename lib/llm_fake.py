"""Dublê determinístico de chat (sem BaseChatModel — evita conflito de versões LangChain)."""
from __future__ import annotations

from typing import Any


class _Msg:
    def __init__(self, content: str):
        self.content = content


class FakeChatModel:
    """Respostas fixas por padrão no prompt. Mesma entrada → mesma saída."""

    def _gerar_texto(self, prompt: str) -> str:
        baixo = prompt.lower()
        if 'lsil' in baixo or 'lesão intraepitelial de baixo grau' in baixo:
            if '25' in baixo or 'jovem' in baixo or '<25' in baixo or 'menor de 25' in baixo:
                return (
                    '**Conduta Clínica — LSIL em Pacientes < 25 anos (Diretrizes INCA/MS):**\n\n'
                    '1. **Recomendação:** Repetir a citologia oncótica em **12 meses** (não encaminhar imediatamente à colposcopia).\n'
                    '2. **Justificativa:** Em mulheres jovens com menos de 25 anos, a taxa de regressão espontânea das lesões de baixo grau (LSIL) associadas ao HPV é elevada (supera 80%).\n'
                    '3. **Encaminhamento:** Se na citologia de controle após 12 meses mantiver LSIL ou evoluir para HSIL, encaminhar para colposcopia.\n\n'
                    '**Fonte consultada:** Diretrizes Brasileiras para o Rastreamento do Câncer do Colo do Útero (INCA / Ministério da Saúde).'
                )
            return (
                '**Conduta Clínica — LSIL (Lesão Intraepitelial de Baixo Grau):**\n\n'
                '1. **Pacientes ≥ 25 anos:** Repetir a citologia oncótica (Papanicolau) em **6 meses** na USF.\n'
                '2. **Se segundo resultado for negativo:** Retornar ao rastreamento trienal de rotina.\n'
                '3. **Se mantiver LSIL ou piorar (ex.: HSIL, ASC-H):** Encaminhar para colposcopia.\n\n'
                '**Fonte consultada:** Diretrizes Brasileiras para o Rastreamento do Câncer do Colo do Útero (INCA/MS).'
            )

        if 'misoprostol' in baixo or 'aborto' in baixo:
            return (
                '**Protocolo Clínico — Indução / Esvaziamento Uterino com Misoprostol (MS/FEBRASGO):**\n\n'
                '1. **Aborto Retido (< 12 semanas):** Misoprostol 800 mcg via vaginal a cada 3 a 4 horas (máximo 3 doses) ou sublingual.\n'
                '2. **Contraindicações:** Cicatriz uterina prévia corporal/clássica, alergia ao princípio ativo, suspeita de gestação ectópica.\n'
                '3. **Monitoramento:** Acompanhamento de sangramento e dor pélvica; confirmação ultrassonográfica de esvaziamento completo.\n\n'
                '**Fonte consultada:** Manual de Atenção à Mulher com Abortamento (Ministério da Saúde).'
            )

        if 'papanicolau' in baixo or 'citologia' in baixo or 'rastreamento' in baixo:
            return (
                '**Rastreamento do Câncer do Colo do Útero (Papanicolau — MS):**\n\n'
                '1. **Público-alvo:** Mulheres de 25 a 64 anos que já tiveram atividade sexual.\n'
                '2. **Periodicidade:** A cada 3 anos, após dois exames anuais consecutivos com resultado negativo.\n'
                '3. **Interrupção:** Aos 64 anos em mulheres com ao menos dois exames negativos nos últimos 5 anos.\n\n'
                '**Fonte consultada:** Cadernos de Atenção Básica nº 13 — Controle dos Cânceres do Colo do Útero e da Mama (MS).'
            )

        if 'mamografia' in baixo or 'mama' in baixo or 'bi-rads' in baixo:
            return (
                '**Rastreamento Mamográfico (INCA / MS):**\n\n'
                '1. **Faixa Etária:** 50 a 69 anos (bienal para rastreamento populacional assintomático).\n'
                '2. **Alto Risco Familiar:** Iniciar aos 35 anos ou 10 anos antes do caso mais precoce na família.\n'
                '3. **Conduta por BI-RADS:** BI-RADS 1 ou 2 = manter rastreio; BI-RADS 3 = repetir em 6 meses; BI-RADS 4 ou 5 = encaminhar para biópsia.\n\n'
                '**Fonte consultada:** Diretrizes para o Controle do Câncer de Mama (INCA/MS).'
            )

        if 'violência' in baixo or 'violencia' in baixo or 'sinan' in baixo or 'agressão' in baixo:
            return (
                '**Protocolo de Atendimento em Situações de Violência (MS):**\n\n'
                '1. **Acolhimento e Escuta Qualificada:** Atendimento em espaço privativo garantindo sigilo e não-julgamento.\n'
                '2. **Notificação Compulsória:** Preencher a Ficha SINAN de violência interpessoal/autoprovocada em até 24h para casos graves.\n'
                '3. **Profilaxias (se violência sexual < 72h):** Anticoncepção de emergência (Levonorgestrel 1,5 mg), PEP para HIV (28 dias) e profilaxia de ISTs.\n\n'
                '**Fonte consultada:** Norma Técnica de Prevenção e Tratamento dos Agravos Resultantes da Violência Sexual (MS).'
            )

        if 'alto_risco' in baixo or 'alto risco' in baixo:
            return (
                'As variáveis que mais contribuíram para esta classificação foram as listadas no payload. '
                'Encaminhar ao pré-natal de alto risco conforme o resultado do modelo. '
                'Não alterar as probabilidades informadas.'
            )
        if 'incompleto' in baixo or 'ausentes' in baixo:
            return 'Não houve predição. Completar os campos obrigatórios listados no payload.'
        if 'bypass' in baixo or 'emerg' in baixo:
            return 'Encaminhamento imediato por regra determinística de alarme obstétrico.'

        return (
            '**Consulta Clínica ao Assistente (Saúde da Mulher):**\n\n'
            '1. **Orientações Gerais:** Para condutas em ginecologia, obstetrícia e rastreamento preventivo, os protocolos recomendam avaliar o histórico clínico e exames complementares.\n'
            '2. **Protocolos Integrados:** Rastreamento de câncer de colo (INCA), pré-natal de baixo e alto risco (FEBRASGO/MS) e atendimento a urgências obstétricas.\n\n'
            '**Fonte consultada:** Protocolos Clínicos e Diretrizes Terapêuticas em Saúde da Mulher (Ministério da Saúde).'
        )

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        if isinstance(input, str):
            return _Msg(self._gerar_texto(input))
        if isinstance(input, list):
            texto = '\n'.join(getattr(m, 'content', str(m)) for m in input)
            return _Msg(self._gerar_texto(texto))
        return _Msg(self._gerar_texto(str(input)))

    def bind_tools(self, tools, **kwargs):
        return self
