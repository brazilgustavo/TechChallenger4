# Roteiro Completo de Treino e Gravação do Vídeo (15 min)
## Guardiã AI — Inteligência Artificial para Saúde e Segurança da Mulher

**Duração-alvo:** 14 minutos e 20 segundos (margem de segurança sobre o limite oficial de 15 minutos).  
**Formato:** Screencast com narração em 1080p 30fps (utilizando OBS Studio ou Loom).  
**Estilo:** Apresentação prática conduzida pela UI Gradio (demonstrando a jornada completa de apoio ao profissional).

---

## ⏱️ Tabela de Estrutura & Cronograma

| Bloco | Duração | Minutagem | O que Mostrar na Tela | Conteúdo & Foco |
|---|---|---|---|---|
| **1. Abertura** | 0:30 | 0:00 - 0:30 | `README.md` no VSCode | Apresentação, objetivo Guardiã AI, público-alvo, dados sintéticos |
| **2. Arquitetura** | 1:30 | 0:30 - 2:00 | `ARQUITETURA.md` / `README.md` | Diagrama das 4 camadas (Dados, Inteligência, Orquestração, UI) |
| **3. ML & Fine-Tuning** | 2:30 | 2:00 - 4:30 | Notebooks 02, 03 e `comparacao.json` | Dataset 8k, QLoRA Llama 3.2 3B, modelo LogReg (PR-AUC 0,590, recall 0,955, limiar 0,278) |
| **4. Stack & RAG** | 1:10 | 4:30 - 5:40 | `lib/tools.py` e `lib/templates/` | 10 Tools, 5 Workflows LangGraph, 4 Templates de Documentos |
| **5. Demo UI Gradio (★)** | 6:00 | 5:40 - 11:40 | Interface Gradio (6 abas) | **Jornada Completa**: Sidebar, Chat, Triagem, Violência, Obstétrico, Prevenção, Risco ML |
| **6. LGPD & Governança** | 1:20 | 11:40 - 13:00 | UI `log_acesso` + Notebook 10 | Registro de auditoria LGPD + Relatório gerencial e epidemiológico |
| **7. Encerramento** | 1:20 | 13:00 - 14:20 | `README.md` (Limitações) + GitHub | Decisões de arquitetura (validação sem latência), limitações e encerramento |
| **TOTAL** | **14:20** | | | **Margem de 40s para o limite de 15:00 min** |

---

## 🎬 Roteiro Fala por Fala (Teleprompter de Treino)

### 🎙️ Bloco 1 — Abertura e Contexto (0:00 – 0:30)

* **Tela:** Header do `README.md` no VSCode.
* **Texto para Falar:**
> "Olá! Meu nome é [SEU NOME], aluno da Pós Tech FIAP em IA para Devs. Apresento o Tech Challenge da Fase 5: a **Guardiã AI**, um sistema de Inteligência Artificial especializado em **Saúde e Segurança da Mulher**."
> 
> "A aplicação é voltada para a equipe de saúde — médicos, enfermeiros e residentes — funcionando como uma ferramenta de apoio à decisão clínica e acolhimento. Trabalha estritamente com dados sintéticos e combina Machine Learning clássico, Fine-Tuning de LLM com QLoRA, RAG em diretrizes do Ministério da Saúde e FEBRASGO, 10 ferramentas LangChain e 5 workflows LangGraph, todos entregues em uma interface Gradio com total conformidade LGPD."

---

### 🎙️ Bloco 2 — Visão Geral da Arquitetura (0:30 – 2:00)

* **Tela:** Diagrama de Arquitetura no `README.md` ou `ARQUITETURA.md`.
* **Texto para Falar:**
> "A arquitetura do projeto é dividida em quatro camadas principais:"
> 
> "1. **Camada de Dados:** Banco SQLite `hospital.db` com schemas relacionais para prontuários, exames, vacinas, registros de violência e a tabela auditada `log_acesso`."
> "2. **Camada de Inteligência:** Integração do modelo de Machine Learning treinado para estratificação de risco gestacional e do modelo Llama 3.2 3B fine-tuned via QLoRA."
> "3. **Camada de Orquestração:** Agente LangChain ReAct com 10 ferramentas estruturadas e 5 grafos LangGraph com StateGraph explícito para triagem ginecológica, detecção de violência, atendimento obstétrico, prevenção e risco ML."
> "4. **Camada de Apresentação:** Interface web interativa em Gradio com 6 abas dedicadas e painel de contexto."

---

### 🎙️ Bloco 3 — Machine Learning & Fine-Tuning (2:00 – 4:30)

* **Tela:** Notebooks `02_gerar_dataset_sft.ipynb`, `03_treinar_qlora.ipynb` e `artifacts/metrics/comparacao.json`.
* **Texto para Falar:**
> "No módulo de Machine Learning, treinamos e comparamos modelos de classificação em um dataset de 8.000 registros gestacionais sintéticos. O modelo selecionado foi a **Regressão Logística**, alcançando **PR-AUC de 0,590** no conjunto de teste e **Recall de 0,955** no limiar de validação calibrado em **0,278** — garantindo alta sensibilidade para detecção de gestantes de risco."
> 
> "Para a linguagem natural, geramos um dataset de SFT com 6.414 pares de perguntas e respostas a partir de 39 documentos oficiais em 5 categorias clínicas. Aplicamos **QLoRA em 4 bits NF4** sobre o Llama 3.2 3B. A avaliação side-by-side demonstrou um salto de 33% para quase 100% no direcionamento correto de casos sensíveis para redes de apoio como SINAN e Ligue 180."

---

### 🎙️ Bloco 4 — Stack, Tools & Templates Clínicos (4:30 – 5:40)

* **Tela:** Navegação rápida no VSCode em `lib/tools.py` e na pasta `lib/templates/`.
* **Texto para Falar:**
> "Toda a lógica da aplicação utiliza 10 ferramentas LangChain estruturadas — incluindo prontuário, busca de exames atrasados, categorização de medicamentos na gestação e busca RAG."
> 
> "Além disso, disponibilizamos em `lib/templates/` 4 modelos de documentos clínicos padronizados: laudo de mamografia BI-RADS, receita de terapia hormonal com checklist FEBRASGO, ficha SINAN de notificação compulsória e relatório de atendimento à violência segundo a Norma Técnica do Ministério da Saúde. Vamos ver agora tudo isso funcionando na UI Gradio."

---

### 🎙️ Bloco 5 — Demonstração Prática na UI Gradio ★ (5:40 – 11:40)

* **Tela:** Interface Gradio aberta no navegador (`http://localhost:7860`).

#### 📍 5.0 Sidebar — Seleção de Paciente & Alertas (30s)
* **Ação:** Selecionar a paciente `Maria Silva` no dropdown.
* **Texto para Falar:**
> "Na sidebar, o profissional seleciona a paciente em atendimento. A interface auto-renderiza alertas instantâneos: mamografia atrasada há 4 anos marcado em vermelho (🔴) e indicação de registro prévio de violência sob sigilo (🔒)."

#### 📍 5.1 Tab 1: 💬 Consulta livre (45s)
* **Ação na UI:** Colar no chat:
  ```text
  Quais critérios para repetir citologia em paciente <25a com LSIL?
  ```
* **Texto para Falar:**
> "Na primeira aba, o profissional faz consultas em linguagem livre. O agente ativa a ferramenta RAG, busca no protocolo oficial do Ministério da Saúde e responde citando a fonte. O dropdown expansível detalha as ferramentas executadas."

#### 📍 5.2 Tab 2: 🩺 Triagem Ginecológica (1:00)
* **Ação na UI:** Ir para a Tab 2 e colar no campo de queixa:
  ```text
  Paciente 32 anos, sangramento intenso há 3 dias, dor pélvica forte irradiando para ombro, atraso menstrual de 8 semanas. Estável hemodinamicamente.
  ```
  Clicar em **Realizar triagem**.
* **Texto para Falar:**
> "Na segunda aba, o workflow de triagem analisa o relato. O LangGraph reconhece o atraso menstrual acompanhado de dor irradiando para o ombro como sinal de alerta para gestação ectópica rota, classifica o caso como emergência e indica o encaminhamento imediato."

#### 📍 5.3 Tab 3: 🛡️ Detecção de Violência & Segurança (1:30)
* **Ação na UI:** Ir para a Tab 3 e colar na descrição livre:
  ```text
  Paciente 28a comparece com lesões equimóticas em locais não-expostos (dorso, coxas) em múltiplas fases. Acompanhante não permite que a paciente fale a sós.
  ```
  Marcar o checkbox **Confirmação clínica** e clicar em **Avaliar e registrar**.
* **Texto para Falar:**
> "Esta é a aba de segurança da mulher. O workflow calcula o score de suspeita, ativa o protocolo de acolhimento sem acompanhante e aciona a notificação SINAN. Com a confirmação clínica, o registro é gravado no banco de dados com protocolo e id gerados."

#### 📍 5.4 Tab 4: 🤰 Atendimento Obstétrico (1:00)
* **Ação na UI:** Ir para a Tab 4 e colar na descrição clínica:
  ```text
  Gestante 34a, G3P2A0, IG 32 semanas. Cefaleia intensa há 24h, escotomas e dor epigástrica em barra.
  ```
  Clicar em **Avaliar gestação**.
* **Texto para Falar:**
> "No atendimento obstétrico, o fluxo analisa os sintomas por regex com base nas diretrizes da FEBRASGO. Cefaleia e dor em barra acionam o alerta de pré-eclâmpsia grave, ativando o bypass de emergência para pronto-atendimento obstétrico."

#### 📍 5.5 Tab 5: 📅 Prevenção e Rastreamento (45s)
* **Ação na UI:** Ir para a Tab 5 e clicar em **Gerar plano preventivo**.
* **Texto para Falar:**
> "A quinta aba cruza a idade e histórico da paciente selecionada com as diretrizes do Ministério da Saúde, constata o atraso na mamografia, sugere a conduta de rastreamento e redige textos padronizados para notificação via SMS ou WhatsApp."

#### 📍 5.6 Tab 6: 📈 Risco Gestacional (ML) (1:15)
* **Ação na UI:** Ir para a Tab 6, clicar em **Carregar dados da paciente selecionada (sidebar)** e em seguida clicar em **Estratificar risco**.
* **Texto para Falar:**
> "Na sexta aba, demonstramos o modelo de Machine Learning. Os 11 parâmetros clínicos da paciente são enviados ao pipeline da Regressão Logística. A interface calcula a probabilidade, aplica o limiar de 0,278, exibe as variáveis de maior peso (feature importance) e aciona o bypass se houver descrição de alarme."

---

### 🎙️ Bloco 6 — LGPD, Auditoria & Relatórios Gerenciais (11:40 – 13:00)

* **Tela:** Visualização da tabela `log_acesso` / Notebook `10_relatorio_utilizacao.ipynb`.
* **Texto para Falar:**
> "A governança e privacidade são mantidas rigorosamente: qualquer consulta a registros sigilosos de violência exige justificativa clínica mínima de 5 caracteres e gera log automático com timestamp e usuário em `log_acesso`."
> 
> "Além disso, o notebook 10 gera relatórios gerenciais sobre a cobertura de exames preventivos, taxas de adesão e indicadores epidemiológicos de acolhimento no hospital."

---

### 🎙️ Bloco 7 — Encerramento & Limitações (13:00 – 14:20)

* **Tela:** Seção de Limitações no `README.md` e link do repositório GitHub.
* **Texto para Falar:**
> "Em resumo, entregamos uma solução completa de IA para saúde e segurança da mulher combinando Dados + ML + LLM + RAG + Aplicação Gradio."
> 
> "Como limitações transparentes documentadas: a solução usa dados sintéticos para fins acadêmicos e requer validação clínica para ambiente real. Justificamos a decisão de arquitetura de aplicar validação determinística sem um segundo passe de LLM para preservar a resposta em tempo hábil para emergências."
> 
> "Todo o código, artefatos, notebooks e documentação estão disponíveis no repositório GitHub. Muito obrigado!"

---

## 📋 Textos Prontos para Copiar e Colar na Gravação

Tenha este bloco aberto ao lado para colar na UI durante a gravação:

| Tab na UI | Texto / Payload a Colar |
|---|---|
| **Tab 1 (Chat)** | `Quais critérios para repetir citologia em paciente <25a com LSIL?` |
| **Tab 2 (Triagem)** | `Paciente 32 anos, sangramento intenso há 3 dias, dor pélvica forte irradiando para ombro, atraso menstrual de 8 semanas. Estável hemodinamicamente.` |
| **Tab 3 (Violência)** | `Paciente 28a comparece com lesões equimóticas em locais não-expostos (dorso, coxas) em múltiplas fases. Acompanhante não permite que a paciente fale a sós.` |
| **Tab 4 (Obstétrico)** | `Gestante 34a, G3P2A0, IG 32 semanas. Cefaleia intensa há 24h, escotomas e dor epigástrica em barra.` |
| **Tab 5 (Prevenção)** | *(Apenas clicar no botão com a paciente Maria Silva selecionada na sidebar)* |
| **Tab 6 (Risco ML)** | *(Clicar em 'Carregar dados da paciente selecionada' e depois em 'Estratificar risco')* |

---

## 💡 Dicas de Ouro para Treino

1. **Fale em ritmo pausado:** Falar com clareza nos nomes das métricas (`PR-AUC 0,590`, `limiar 0,278`, `QLoRA 4-bits`).
2. **Citar Dados Sintéticos em voz alta:** É um requisito direto de avaliação do edital.
3. **Se a inferência demorar 5-10s:** Use o tempo de carregamento da UI para narrar o que a IA está fazendo (*"Neste momento o LangGraph está extraindo os sintomas via JSON estruturado e consultando o RAG..."*).
