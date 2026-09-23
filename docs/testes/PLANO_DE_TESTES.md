# Plano de Testes e Estratégia de Homologação

**Projeto:** Assistente Clínico Hospitalar em Saúde da Mulher  

---

## Estrutura da Suíte Automatizada (Pytest)

- **Pirâmide de testes:** unit (`tests/unit`) → integration (`tests/integration`) → e2e (`tests/e2e`) → regression (`tests/regression`).
- **Fixtures (`tests/conftest.py`):** SQLite temporário, `FakeChatModel`, `FakeRetriever`, `CASO_OK`.
- **Total:** 88 testes automatizados (100% verdes).

---

## Guia de Homologação Manual

Para o roteiro completo de testes manuais da interface web Gradio (tela a tela, entradas de teste e resultados esperados), consulte o documentado:

👉 **[`ROADMAP_DE_TESTES.md`](ROADMAP_DE_TESTES.md)**
