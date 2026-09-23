# Roadmap de Novas Implementações e Finalização

**Projeto:** Assistente Clínico Hospitalar em Saúde da Mulher  
**Data:** 2026-09-21  
**Branch:** `feat/evolucao-ml-risco-gestacional`  

---

## Status Geral das Fases

- [x] **Fase 1: Configuração do Ambiente e Suíte de Testes Local**
  - [x] Criar ambiente virtual local `.venv` com dependências atualizadas.
  - [x] Executar pipeline de treinamento de modelos (`scripts/train.py`).
  - [x] Rodar e validar 100% da suíte de testes (88 testes verdes em `pytest`).

- [x] **Fase 2: Integração Prontuário ↔ Formulário ML na UI (6ª Aba)**
  - [x] Adicionar botão de carregamento rápido no formulário ML (`lib/ui.py`).
  - [x] Conectar o manipulador `on_carregar_paciente_ml` à função `features_de_paciente` (`lib/ml/schema.py`) para preencher automaticamente o payload JSON.
  - [x] Adicionar teste automatizado E2E em `tests/e2e/test_ui_aba_ml.py`.

- [x] **Fase 3: Otimização do RAG (Chunking e Indexação Chroma)**
  - [x] Reduzir `CHUNK_SIZE` para 1000 caracteres e `CHUNK_OVERLAP` para 200 no pipeline de indexação para adequação à janela de 128 tokens do `paraphrase-multilingual-MiniLM-L12-v2`.
  - [x] Garantir suporte a citações estruturadas com `doc_id` e metadados em `lib/workflows/common.py`.

- [x] **Fase 4: Explicabilidade Avançada (SHAP) e Auditoria de Segurança**
  - [x] Instalar `shap` (v0.51.0) e validar explicabilidade via `TreeExplainer` no modelo de Random Forest em `lib/ml/explain.py`.
  - [x] Validar compatibilidade sem regressões na suíte de testes.

- [x] **Fase 5: Evidências Visuais e Preparação da Entrega Final**
  - [x] Executar gerador de artefatos de demonstração `scripts/run_demo.py` para gerar os 4 modos operacionais (`D1_sucesso`, `D2_incompleto`, `D3_emergencia`, `D4_degradado`) em `artifacts/demo/`.
  - [x] Criar o documento oficial de testes e guia de homologação [`docs/testes/ROADMAP_DE_TESTES.md`](../testes/ROADMAP_DE_TESTES.md).

---

## Log de Progresso

| Data | Fase / Tarefa | Descrição do Progresso | Status |
|---|---|---|---|
| 2026-09-21 | Inicialização | Roadmap de novas implementações criado | 🟢 Criado |
| 2026-09-21 | Fase 1 | Ambiente virtual `.venv` criado, dataset gerado e 4 modelos treinados; 88 testes pytest passando 100% | 🟢 Concluído |
| 2026-09-21 | Fase 2 | Botão "Carregar dados da paciente selecionada" e handler `on_carregar_paciente_ml` adicionados à 6ª aba do Gradio (`lib/ui.py`) com teste E2E | 🟢 Concluído |
| 2026-09-21 | Fase 3 | Otimização do chunking de RAG (1000/200 chars) para adequação à janela de embeddings | 🟢 Concluído |
| 2026-09-21 | Fase 4 | Biblioteca `shap` instalada e ativada para explicabilidade local via `TreeExplainer` no Random Forest | 🟢 Concluído |
| 2026-09-21 | Fase 5 | Criado o `ROADMAP_DE_TESTES.md` com guia completo de homologação tela a tela e matriz de 10 casos de aceite | 🟢 Concluído |
