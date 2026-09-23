# Roadmap de Testes e Guia de Homologação

**Projeto:** Assistente Clínico Hospitalar em Saúde da Mulher  
**Versão:** 1.0.0  
**Data:** 2026-09-21  
**Público-alvo:** Desenvolvedores, QA e Avaliadores Acadêmicos  

---

## 1. Visão Geral e Pré-requisitos

Este documento orienta o processo de testes **automatizados** e **manuais (interface Gradio)** do sistema.

### Pré-requisitos de Ambiente
- Python 3.11+
- Ambiente virtual configurado (`.venv`)
- Dependências instaladas (`requirements.txt`, `requirements-ml.txt`, `pytest`, `shap`)

### Como Inicializar o Ambiente Local
```bash
# 1. Ativar o ambiente virtual (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 2. Gerar o dataset e treinar os modelos de ML (se primeira execução)
python scripts/train.py --gerar-dataset
python scripts/train.py

# 3. Executar os testes automatizados (suíte completa)
python -m pytest -q

# 4. Iniciar o servidor da interface web Gradio
python scripts/app.py
```
> O servidor estará acessível no navegador em: **`http://localhost:7860`**

---

## 2. Testes Automatizados (Pytest)

A suíte cobre 88 testes automatizados divididos em 4 níveis:

```text
tests/
├── unit/         # Testes unitários (schema, validadores, explicabilidade, modelo)
├── integration/  # Testes de integração (workflos LangGraph, auditoria DB, RAG)
├── e2e/          # Testes de ponta a ponta da UI Gradio e fluxos completos
└── regression/   # Testes de estabilidade e determinismo de resposta
```

### Comandos Úteis de Teste
```bash
# Executar todos os testes com saída resumida
python -m pytest -q

# Executar com relatório de cobertura de código (coverage)
python -m pytest --cov=lib tests/

# Executar apenas testes de uma categoria específica (ex: E2E)
python -m pytest tests/e2e/
```

---

## 3. Roteiro de Homologação Manual (Interface Web)

### 📌 Módulo 0: Barra Lateral (Contexto da Sessão e Prontuário)
- **Passo 1:** No campo **Profissional logado**, altere para `Dr. Silva (CRM 12345)`.
  - *Resultado esperado:* O texto de status atualiza para `Profissional ativo: Dr. Silva (CRM 12345)`.
- **Passo 2:** No dropdown **Paciente**, selecione `Ana Borges (id=2, n. 2007)`.
  - *Resultado esperado:* O painel amarelo exibe a idade (19 anos), DUM, método contraceptivo (COC) e status dos exames preventivos sem erros.

---

### 💬 Módulo 1: Aba 1 — Consulta Livre (Chat)
- **Cenário 1 (LSIL em jovem):** Pergunta: `Qual a conduta para achado de LSIL na citologia em paciente menor de 25 anos?`
  - *Resultado esperado:* Resposta detalhada informando a recomendação de repetição em 12 meses (Diretrizes INCA/MS) devido à alta taxa de regressão espontânea do HPV em jovens.
- **Cenário 2 (LSIL em paciente ≥ 25a):** Pergunta: `Qual a conduta para LSIL em paciente de 30 anos?`
  - *Resultado esperado:* Recomendação de repetição em 6 meses na USF.
- **Cenário 3 (Procedimento com Misoprostol):** Pergunta: `Qual a posologia de misoprostol para aborto retido?`
  - *Resultado esperado:* Dose de 800 mcg via vaginal a cada 3-4h (máx 3 doses), contraindicações e orientações de monitoramento.
- **Cenário 4 (Violência Sexual):** Pergunta: `Quais as profilaxias para atendimento de violência sexual < 72h?`
  - *Resultado esperado:* Profilaxia de HIV (PEP 28 dias), Anticoncepção de Emergência e profilaxia de ISTs não-virais + Notificação SINAN.

---

### 🩺 Módulo 2: Aba 2 — Triagem Ginecológica
- **Cenário 1 (Urgência / Emergência):** Queixa: `Paciente de 32 anos com sangramento vaginal abundante há 3 dias, dor pélvica forte irradiando para ombro e atraso menstrual de 8 semanas.`
  - *Resultado esperado:* Triagem identifica sinal de alarme (`emergencia`), pula exames ambulatoriais e gera encaminhamento imediato.
- **Cenário 2 (Queixa ambulatorial de rotina):** Queixa: `Paciente com leucorréia esbranquiçada e prurido há 5 dias, sem dor ou sangramento.`
  - *Resultado esperado:* Classificação `rotina`/`agendado`, com sugestão de exames (ex: bacterioscopia) e orientações.

---

### 🛡️ Módulo 3: Aba 3 — Detecção de Violência
- **Cenário 1 (Checklist Heurístico Rápido):** Marque os checkboxes `Lesões em locais não-expostos` e `Acompanhante controlador`. Clique em **Avaliar checklist**.
  - *Resultado esperado:* Retorna score, nível de alerta (`alta_suspeita`), conduta em ambiente reservado e encaminhamentos da rede.
- **Cenário 2 (Workflow Completo com SINAN):** Digite a descrição do caso, marque `Confirmação clínica` e clique em **Avaliar e registrar**.
  - *Resultado esperado:* Registra a notificação no banco de dados (`notificacao_sinan = 1`) e salva a linha de auditoria em `log_acesso`.

---

### 🤰 Módulo 4: Aba 4 — Atendimento Obstétrico
- **Cenário 1 (Alarme de Pré-eclâmpsia Grave):** Descrição: `Gestante 34a, IG 32 semanas, cefaleia intensa há 24h, visão turva com escotomas e dor epigástrica em barra.`
  - *Resultado esperado:* Dispara alarme 🚨 **EMERGÊNCIA OBSTÉTRICA — encaminhamento imediato ao PS obstétrico**, listando os sinais de alarme detectados.
- **Cenário 2 (Acompanhamento Habitual):** Descrição: `Gestante 24a, G1P0A0, IG 16 semanas, sem queixas.`
  - *Resultado esperado:* Classificação `habitual`, agenda de exames de rotina por IG (USG obstétrica, glicemia, sorologias) e periodicidade das consultas.

---

### 📅 Módulo 5: Aba 5 — Prevenção e Rastreamento
- **Passo:** Selecione uma paciente na sidebar (ex: paciente com exames atrasados) e clique em **Gerar plano preventivo**.
- *Resultado esperado:* Calcula exames populacionais devidos (Papanicolau trienal 25-64a, Mamografia bienal 50-69a), prioridades e gera texto de lembretes (SMS/WhatsApp).

---

### 📈 Módulo 6: Aba 6 — Risco Gestacional (ML)
- **Cenário 1 (Auto-carregamento de Prontuário):**
  - Selecione a paciente na sidebar.
  - Clique em **`📂 Carregar dados da paciente selecionada (sidebar)`**.
  - *Resultado esperado:* O campo de payload JSON é preenchido com idade, IG e histórico de gestações/partos/abortos do SQLite da paciente.
- **Cenário 2 (Predição ML & SHAP):**
  - Clique em **`Estratificar risco`**.
  - *Resultado esperado:* Retorna a classificação (`habitual` ou `alto_risco`), probabilidade, limiar (`0.278`), lista de variáveis com maior contribuição (explicabilidade local **SHAP**) e linha gravada em `predicoes_ml`.
- **Cenário 3 (Bypass por Alarme Obstétrico):**
  - No campo de descrição clínica, digite `cefaleia intensa e escotomas`. Clique em **Estratificar risco**.
  - *Resultado esperado:* Retorna modo `bypass_regra` apontando encaminhamento imediato antes do modelo.

---

## 4. Matriz de Homologação (Checklist de Aceite)

| # | Teste / Aba | Entrada | Resultado Esperado | Status |
|---|---|---|---|---|
| TC-01 | Sidebar | Seleção de paciente ID #2 | Prontuário exibido no card | ✅ |
| TC-02 | Aba 1 (Chat) | Pergunta sobre LSIL < 25a | Resposta oficial INCA de repetição em 12m | ✅ |
| TC-03 | Aba 1 (Chat) | Pergunta sobre Misoprostol | Posologia e contraindicações de aborto retido | ✅ |
| TC-04 | Aba 2 (Triagem) | Sangramento abundante + dor | Rota de emergência imediata | ✅ |
| TC-05 | Aba 3 (Violência) | Checklist com 2 sinais | Score de alerta + conduta reservada | ✅ |
| TC-06 | Aba 4 (Obstétrico) | Cefaleia + escotomas (IG 32w) | Alerta pré-eclâmpsia grave (PS obstétrico) | ✅ |
| TC-07 | Aba 5 (Prevenção) | Paciente com Papanicolau > 3 anos | Exame marcado em atraso com prioridade | ✅ |
| TC-08 | Aba 6 (ML) | Botão Carregar Paciente | JSON populado do SQLite | ✅ |
| TC-09 | Aba 6 (ML) | Invocação com payload válido | Classificação + Probabilidade + SHAP | ✅ |
| TC-10 | UI / CSS | Alternância Tema Claro / Tema Escuro | Leitura limpa e alto contraste em todos os textos | ✅ |

---

## 5. Rastreabilidade de Erros e Logs de Auditoria

Em caso de comportamento inesperado durante os testes:

1. **Verificar os logs no terminal:** Todas as chamadas de banco e invocação dos workflows registram eventos em tempo real.
2. **Consultar tabelas de auditoria do SQLite:**
   ```sql
   -- Log de auditoria LGPD (consultas de violência)
   SELECT * FROM log_acesso ORDER BY timestamp DESC LIMIT 5;

   -- Log de auditoria de predições ML
   SELECT * FROM predicoes_ml ORDER BY timestamp DESC LIMIT 5;
   ```
