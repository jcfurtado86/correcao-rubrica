---
description: "Tarefas de implementação do MVP de correção assistida por rubrica"
---

# Tasks: MVP — Correção Assistida por Rubrica com Aferição de Consistência

**Input**: documentos de `specs/001-mvp-correcao-assistida/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: incluídos. A constituição ("Fluxo de Desenvolvimento e Portões de Qualidade") exige
testes automatizados para verificação de âncora, consolidação, anonimização e métricas antes
da integração, e o quickstart depende de testes de integração e contrato. Nenhum teste chama o
modelo real: todos usam `LLM_PROVIDER=dumb`.

**Organization**: tarefas agrupadas por história da spec. A história 1 é o incremento
mínimo demonstrável. As histórias 2 e 3 completam o núcleo P1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: história da spec (US1…US6)

## Path Conventions

Aplicação web no formato do Extenda: `backend/src/<app Django>/`, `backend/tests/`,
`frontend/src/`, e na raiz `analysis/`, `dados_sinteticos/` e `docs/`. Referência de código
para copiar e adaptar: `~/Projetos/extenda/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: esqueleto do repositório, dependências e contêineres

- [X] T001 Criar a estrutura de diretórios do plan.md: `backend/src/{config,core,conectores,rubricas,lotes,avaliacao,revisao,estudos,metricas}/` (cada app Django com `__init__.py`, `apps.py`, `models.py`, `admin.py`, `migrations/__init__.py`), `backend/tests/{unit,integration,contract}/`, `frontend/`, `analysis/`, `dados_sinteticos/`, `docs/`
- [X] T002 Criar `backend/requirements.txt` com as mesmas versões do Extenda (`Django==5.2.15`, `djangorestframework==3.17.1`, `djangorestframework-simplejwt==5.5.1`, `drf-spectacular==0.29.0`, `django-environ==0.14.0`, `psycopg[binary]==3.3.4`, `celery==5.6.3`, `redis==6.4.0`, `google-genai==2.10.0`, `gunicorn==23.0.0`, `openpyxl==3.1.5`, `django-allauth==65.19.1`) mais `numpy`, `scikit-learn`, `statsmodels` e `krippendorff`, fixados na versão resolvida na instalação. Criar também `backend/requirements-dev.txt` (`-r requirements.txt`, `pytest==8.4.2`, `pytest-django==4.12.0`, `pytest-cov==6.3.0`, `ruff==0.15.20`)
- [X] T003 Criar o projeto Django em `backend/src/manage.py` e `backend/src/config/{settings.py,urls.py,wsgi.py,asgi.py}`:
  - `settings.py` 12-factor com django-environ, todas as apps de T001 registradas e `AUTH_USER_MODEL = "core.Usuario"`;
  - `LANGUAGE_CODE="pt-br"`, `TIME_ZONE="America/Belem"`, `USE_TZ=True`;
  - `FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]` e `FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024`, para o upload nunca tocar o disco (research R9);
  - variáveis `LLM_PROVIDER` (padrão `"dumb"`), `GEMINI_API_KEY`, `GEMINI_MODEL` (padrão `"gemini-3.6-flash"`), `GEMINI_PAID_TIER` (bool, padrão `False`), `TETO_USD_PADRAO` (padrão 10), `LLM_CONCORRENCIA` (padrão 8), `LLM_RATE_LIMIT` (padrão `"120/m"`), `TOKENS_SAIDA_ESTIMADOS` (padrão 1050), `LIMITE_CARACTERES_RESPOSTA` (padrão 15000)
- [X] T004 [P] Criar `backend/src/config/celery.py` (app `correcao`, `autodiscover_tasks`) e importá-lo em `backend/src/config/__init__.py`. Em settings: `CELERY_BROKER_URL` do ambiente, `CELERY_TASK_ACKS_LATE=True`, `CELERY_WORKER_PREFETCH_MULTIPLIER=1` e `CELERY_TASK_ALWAYS_EAGER` lido do ambiente (verdadeiro nos testes)
- [X] T005 [P] Criar os arquivos de implantação `backend/Dockerfile`, `docker-compose.yml` e `.env.example`:
  - `backend/Dockerfile`, a partir de `~/Projetos/extenda/backend/Dockerfile` (`python:3.12-slim`, sem Tesseract/poppler/catdoc);
  - `docker-compose.yml` com os serviços `db` (`postgres:16`), `redis` (`redis:7-alpine`), `backend` (`runserver` em dev), `worker` (`celery -A config worker -c ${LLM_CONCORRENCIA}`) e `frontend` (`node:22-alpine`, `npm run dev`);
  - `.env.example` com todas as variáveis de T003/T004 e o comentário "GEMINI_PAID_TIER=true só com chave de projeto com faturamento; nunca nível gratuito".
- [X] T006 [P] Criar o frontend em `frontend/` com Vite 6 + React 18.3.1 + TypeScript 5.7.3 + react-router-dom 7.18.1 + vitest (`frontend/package.json`, `vite.config.ts` com proxy `/api` → backend, `tsconfig.json`, `src/main.tsx`, `src/App.tsx`)
- [X] T007 [P] Criar `backend/pyproject.toml` com a configuração do ruff (a mesma do Extenda) e do pytest (`DJANGO_SETTINGS_MODULE=config.settings`, `pythonpath=["src"]`, `testpaths=["tests"]`). Criar `backend/tests/conftest.py` com as fixtures `docente`, `outra_docente`, `pesquisador`, `api` (APIClient autenticado por JWT) e `settings_dublê` (força `LLM_PROVIDER="dumb"` e `CELERY_TASK_ALWAYS_EAGER=True`)
- [X] T008 [P] Criar `README.md` na raiz com o objetivo do projeto (link para o canvas e a spec), o comando de subida e um link para `specs/001-mvp-correcao-assistida/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: usuário, autenticação, permissões, conector de LLM com dublê, preços e dados sintéticos

**⚠️ CRITICAL**: nenhuma história começa antes desta fase

- [X] T009 Criar `Usuario` em `backend/src/core/models.py`, estendendo `AbstractUser`, "login por e-mail":
  - `email` único como `USERNAME_FIELD`;
  - `nome`;
  - `papel` em {`DOCENTE`, `PESQUISADOR`}, "padrão `DOCENTE`";
  - manager que cria usuário e superusuário sem username (superusuário com papel `PESQUISADOR`).

  Registrar no `backend/src/core/admin.py` e gerar a migração.
- [X] T010 Configurar a autenticação em `backend/src/config/settings.py` e `backend/src/core/` com simplejwt e login por e-mail, **sem allauth** (ver "Desvios registrados" no plan.md): rotas `/api/auth/token/`, `/api/auth/token/refresh/` e `/api/auth/me/` em `backend/src/core/urls.py`; `SIMPLE_JWT` como no Extenda (60 min / 7 dias, rotação); sem autocadastro
- [X] T011 [P] Criar `backend/src/core/permissions.py` (`EhDono` pelo campo `dono`, `EhPesquisador` por `papel == "PESQUISADOR"`) e `backend/src/core/exceptions.py`, com um handler DRF que devolve `{"detail": "...", "codigo": "..."}` (formato de erro de contracts/api.md). Configurar em settings `REST_FRAMEWORK`: autenticação JWT, `IsAuthenticated` como padrão, `drf_spectacular.openapi.AutoSchema` e esse handler
- [X] T012 Montar `backend/src/config/urls.py` com `/admin/`, `/api/schema/`, `/api/docs/` (drf-spectacular), `/api/auth/` e `include` das `urls.py` de cada app sob `/api/`
- [X] T013 [P] Criar a interface de provedor em `backend/src/conectores/llm.py`, no padrão da factory do Extenda (`~/Projetos/extenda/backend/src/conectores/llm.py`):
  - classe `LLMProvider` com `modelo: str` e o método `avaliar(sistema: str, usuario: str, esquema: dict, semente: int) -> ResultadoLLM`;
  - dataclass `ResultadoLLM(texto: str, tokens_entrada: int, tokens_saida: int, tokens_raciocinio: int, latencia_ms: int)`;
  - exceção `IAIndisponivel` (erro recuperável: 429, 503, rede) e `ErroLLM` (não recuperável);
  - `registrar_provedor(nome, classe)` e `get_llm(nome=None)` lendo `settings.LLM_PROVIDER`.
- [X] T014 [P] Criar `GeminiLLMProvider` em `backend/src/conectores/gemini.py` com `google-genai`:
  - `genai.Client(api_key=settings.GEMINI_API_KEY)` guardado numa **variável local** até a resposta chegar, por causa da armadilha de GC documentada no Extenda (research R8);
  - `GenerateContentConfig(system_instruction=sistema, response_mime_type="application/json", response_json_schema=esquema, seed=semente)`, **sem definir temperatura** (R3);
  - tokens de `usage_metadata.prompt_token_count`, `candidates_token_count` e `thoughts_token_count` (0 se ausente);
  - `google.genai.errors.ServerError` 5xx, `ClientError` 429 e erros de rede mapeados para `IAIndisponivel`; demais erros para `ErroLLM`;
  - registrar como `"gemini"`.
- [X] T015 [P] Criar `DubleLLMProvider` em `backend/src/conectores/duble.py`, registrado como `"dumb"` e sem rede:
  - lê do prompt do usuário o texto entre `<<<` e `>>>` e o enum de níveis do esquema;
  - se o texto contém `[[cenario:X]]`, segue o roteiro X pelo `indice` derivado da semente (o índice vai no prompt de sistema como `#indice=i`). Roteiros:
    - `unanime`: todas no 2º nível;
    - `4-1`: índices 1–4 no 2º nível e 5 no 3º;
    - `3-2`: 1–3 no 2º e 4–5 no 3º;
    - `2-2-1`: 1–2 no 2º, 3–4 no 3º e 5 no 1º;
    - `sem_evidencia`: todas `SEM_EVIDENCIA` com trechos vazios;
    - `trecho_inventado`: índices 1–2 citam frase inexistente e 3–5 são válidas no 2º nível;
    - `json_invalido`: devolve `"{nivel:"`.
  - sem marcador, escolhe o nível de forma pseudoaleatória pela semente;
  - o trecho é a primeira frase do texto sem o marcador, com ≥ 3 palavras;
  - tokens fictícios fixos (entrada = len(prompt)//4, saída 150, raciocínio 0);
  - guarda todos os prompts recebidos numa lista de classe `prompts_recebidos`, para a auditoria de identificadores.
- [X] T016 [P] Criar a tabela de preços em `backend/src/conectores/precos.py`, com vigência (research R2):
  - `gemini-3.6-flash` e `gemini-3.8-flash`: US$ 0,75 / 3,75 por 1M até 2026-12-31 e 1,50 / 7,50 a partir de 2027-01-01;
  - `gemini-2.5-flash`: 0,30 / 2,50;
  - `gemini-2.5-flash-lite`: 0,10 / 0,40;
  - `dublê`: 0 / 0.

  Função `custo_usd(modelo, tokens_entrada, tokens_saida_mais_raciocinio, data) -> Decimal`, que levanta erro para modelo sem preço.
- [X] T017 [P] Escrever `backend/tests/unit/test_precos.py` (virada de vigência em 2027-01-01, modelo desconhecido) e `backend/tests/unit/test_duble.py` (cada roteiro de T015 produz a sequência esperada de níveis para os índices 1–5, e o trecho é substring do texto, exceto em `trecho_inventado`)
- [X] T018 [P] Criar `dados_sinteticos/gerar_turma_ficticia.py`. Ele gera `turma_ficticia.xlsx` e `turma_ficticia.csv` (separador `;`) com 40 linhas e colunas no formato do Moodle: `Sobrenome`, `Nome`, `Endereço de email`, `Número de identificação`, `Resposta 1`. As respostas tratam do enunciado "Explique a diferença entre verificação e validação de software e dê um exemplo de cada uma", e o conjunto inclui:
  - 7 respostas com os marcadores `[[cenario:...]]` de T015, um por roteiro;
  - 2 vazias;
  - 1 com mais de 15.000 caracteres;
  - 2 duplicadas;
  - 5 que citam no texto o próprio nome, e-mail, CPF (com e sem máscara) ou matrícula;
  - 1 que cita o nome de um colega.

  Gera também `dados_sinteticos/identificadores_plantados.txt`, com todos os nomes, e-mails, CPFs e matrículas usados, um por linha.
- [X] T019 [P] Criar a base do frontend: `frontend/src/services/api.ts` (fetch com JWT, renovação por refresh e erro no formato `{detail, codigo}`), `frontend/src/services/auth.tsx` (contexto de sessão), `frontend/src/pages/Login.tsx` e o roteamento protegido em `frontend/src/App.tsx`, com layout e menu (Rubricas, Lotes, Estudos)

**Checkpoint**: login funciona, `pytest` roda, e `get_llm()` devolve o dublê ou o Gemini conforme o `.env`

---

## Phase 3: User Story 1 — Pré-avaliação ancorada de um lote (Priority: P1) 🎯 MVP

**Goal**: rubrica → importação anonimizada → estimativa → rodada com N execuções → tela da resposta com as execuções e os trechos destacados

**Independent Test**: com `turma_ficticia.xlsx` e o dublê, criar a rubrica, importar, pré-avaliar e verificar que (a) todo trecho de execução válida está destacado e existe no texto e (b) `auditar_identificadores` encontra 0 identificadores plantados no banco, nos logs e nos prompts (quickstart V1–V3)

### Tests for User Story 1 ⚠️

> Escrever primeiro e ver falhar

- [X] T020 [P] [US1] Escrever `backend/tests/unit/test_anonimizacao.py` (contracts/importacao.md), cobrindo:
  - e-mail vira `[EMAIL]`;
  - CPF `000.000.000-00` e 11 dígitos viram `[CPF]`;
  - "sequências de 8 a 14 dígitos" viram `[MATRICULA]`;
  - nomes da própria linha **e de outra linha** viram `[ESTUDANTE]`, sem acento e sem caixa, "com limite de palavra": o nome "Ana" não altera "análise";
  - palavras de nome com < 3 letras são ignoradas;
  - `n_substituicoes` confere com as substituições feitas.
- [X] T021 [P] [US1] Escrever `backend/tests/unit/test_ancora.py` (research R5), cobrindo:
  - trecho exato;
  - diferenças de espaço e quebra de linha;
  - aspas e hífens tipográficos;
  - caixa;
  - `inicio` e `fim` apontando para o texto **original**;
  - trecho com reticências, com < 3 palavras e não localizado são inválidos;
  - `SEM_EVIDENCIA` com trechos → `INCOERENTE_SEM_EVIDENCIA`;
  - nível com lista vazia → `SEM_TRECHO`;
  - 1 trecho não localizado entre 2 invalida a execução.
- [X] T022 [P] [US1] Escrever `backend/tests/unit/test_importacao.py`, cobrindo:
  - CSV com `,` e com `;`, UTF-8 com e sem BOM, e XLSX (primeira planilha);
  - recusa acima de 10 MB e de 1.000 linhas;
  - avisos `VAZIA`, `LONGA` (> 15.000 caracteres) e `DUPLICADA`;
  - códigos `R001…` únicos e em ordem diferente da do arquivo (semente fixa no teste);
  - CSV da chave com `codigo,identificador`;
  - nenhuma coluna de identificação no retorno da importação, exceto dentro da chave.
- [X] T023 [P] [US1] Escrever `backend/tests/integration/test_rodada.py` (Celery eager, dublê), cobrindo:
  - a rodada cria `respostas elegíveis × critérios × N` execuções;
  - resposta `VAZIA` gera execuções `SEM_EVIDENCIA` válidas sem chamar o provedor;
  - resposta `LONGA` não gera execução;
  - execuções válidas têm `Trecho.localizado=True` com offsets;
  - `trecho_inventado` gera 2 inválidas `TRECHO_NAO_LOCALIZADO`;
  - `json_invalido` gera `JSON_INVALIDO`;
  - `IAIndisponivel` em todas as tentativas leva a `FALHOU` com `erro`;
  - teto baixo leva a `PAUSADA_TETO` com as restantes em `PENDENTE`;
  - `retomar` com teto maior conclui sem reexecutar nenhuma `CONCLUIDA` (contar chamadas ao dublê);
  - lote não sintético com `LLM_PROVIDER="gemini"` e `GEMINI_PAID_TIER=False` é recusado com `codigo="nivel_gratuito"`;
  - sementes distintas por índice e iguais ao recalcular a mesma rodada.
- [X] T024 [P] [US1] Escrever `backend/tests/integration/test_sem_identificadores.py`. Ele importa `turma_ficticia.csv` (lote não sintético, dublê), executa a rodada e procura cada linha de `identificadores_plantados.txt`, sem acento e sem caixa, em três lugares: todas as colunas de texto de todas as tabelas, a captura de logs (`caplog`) e `DubleLLMProvider.prompts_recebidos`. O resultado esperado é 0 ocorrências (SC-003)
- [X] T025 [P] [US1] Escrever `backend/tests/contract/test_api_us1.py`, conferindo formatos e status de `contracts/api.md` nas seções Rubricas (POST/GET/PUT, 201 com nova versão quando congelada), Lotes e importação (prévia sem gravar nada; importação única por lote), Rodadas (estimativa, recusa sem `confirmar`, progresso, retomar) e `GET /respostas/{id}/execucoes/` (outra docente recebe 404)

### Implementation for User Story 1

- [X] T026 [P] [US1] Criar os modelos em `backend/src/rubricas/models.py`, conforme data-model.md:
  - `Rubrica(dono FK Usuario, titulo, descricao)`;
  - `VersaoRubrica(rubrica, numero "único por rubrica, sequencial", congelada bool, hash sha256 nulo)`;
  - `Criterio(versao, ordem "contígua a partir de 1", nome, descricao, peso "decimal ≥ 0, padrão 1", tipo OBJETIVO|INTERPRETATIVO)`;
  - `Nivel(criterio, ordem "contígua a partir de 1", codigo "N1…Nk gerado da ordem", rotulo, descritor, pontuacao decimal)`.

  `save()` e `delete()` levantam erro se a versão estiver congelada. Gerar a migração.
- [X] T027 [P] [US1] Criar os modelos em `backend/src/lotes/models.py`:
  - `Lote(dono, titulo, enunciado obrigatório, versao_rubrica FK PROTECT, n_execucoes "int 1–10, padrão 5", limiar_acordo "decimal (0,5; 1,0], padrão 0,8", min_validas "int ≥ 1, ≤ n_execucoes, padrão 3", provedor_llm, modelo_llm, teto_usd, sintetico bool)`, com validação em `clean()`;
  - `Resposta(lote, codigo "único por lote", texto imutável, hash_texto sha256, n_substituicoes int, aviso VAZIA|LONGA|null)`, sem nenhum campo de identificador.

  Gerar a migração.
- [X] T028 [P] [US1] Criar os modelos em `backend/src/avaliacao/models.py`:
  - `Rodada(lote, numero, semente_base, versao_prompt, provedor, modelo, custo_estimado_usd, custo_acumulado_usd, teto_usd, confirmada_por, status ESTIMADA|EM_EXECUCAO|PAUSADA_TETO|CONCLUIDA|COM_FALHAS)`;
  - `Execucao(rodada, resposta, criterio, indice, semente, status PENDENTE|EM_ANDAMENTO|CONCLUIDA|FALHOU, valida null, motivo_invalidez JSON_INVALIDO|NIVEL_FORA|SEM_TRECHO|TRECHO_NAO_LOCALIZADO|TRECHO_CURTO|INCOERENTE_SEM_EVIDENCIA|null, nivel_codigo, nivel FK null, justificativa, resposta_bruta, tokens_entrada, tokens_saida, tokens_raciocinio, custo_usd, latencia_ms, tentativas, erro)` com `UniqueConstraint(rodada, resposta, criterio, indice)`;
  - `Trecho(execucao, texto_citado, localizado, inicio null, fim null)`.

  Gerar a migração.
- [X] T029 [US1] Registrar no Django admin (backoffice do pesquisador) os modelos de T026–T028 em `backend/src/{rubricas,lotes,avaliacao}/admin.py`, com `Execucao` e `Trecho` só leitura, filtros por `rodada`, `status`, `valida` e `motivo_invalidez`, e `Resposta` sem edição de `texto`
- [X] T030 [US1] Implementar `backend/src/rubricas/services.py`:
  - `criar_rubrica(dono, dados)`: versão 1, "≥ 1 critério, ≥ 2 níveis", `ordem` e `codigo` derivados da posição;
  - `atualizar_rubrica(rubrica, dados)`: edita a vigente se não estiver congelada; caso contrário cria `numero + 1`;
  - `congelar(versao)`: `hash` = sha256 do JSON canônico (`sort_keys=True`) de critérios e níveis.

  Implementar também `serializers.py`, `views.py` e `urls.py` do app para `GET/POST /rubricas/`, `GET/PUT /rubricas/{id}/`, com permissão `EhDono`.
- [X] T031 [P] [US1] Implementar `backend/src/lotes/anonimizacao.py` como funções puras sem ORM: `termos_de_identificacao(linhas, colunas)` e `anonimizar(texto, termos) -> (texto, n_substituicoes)`, com a ordem de substituição de contracts/importacao.md (e-mail, CPF, matrícula, nomes)
- [X] T032 [US1] Implementar `backend/src/lotes/importacao.py`:
  - `ler_planilha(arquivo_em_memoria)`: CSV UTF-8 ou UTF-8-BOM com separador detectado por `csv.Sniffer`, ou XLSX pela primeira planilha com `openpyxl` `read_only`; limites de 10 MB e 1.000 linhas;
  - `previa(...)`: colunas, 5 linhas de amostra e total;
  - `importar(lote, arquivo, coluna_resposta, colunas_identificacao, gerar_chave)`: anonimiza em memória, embaralha, atribui `R001…`, grava só `Resposta`, calcula os avisos, monta a chave CSV em memória e a devolve em base64 **sem gravar**; recusa segunda importação no mesmo lote.
- [X] T033 [US1] Implementar `backend/src/lotes/{serializers,views,urls}.py` para `POST /lotes/`, `POST /lotes/{id}/importacao/previa/`, `POST /lotes/{id}/importacao/`, `GET /lotes/{id}/` e `GET /lotes/{id}/respostas/`, conforme contracts/api.md. A validação de `POST /lotes/` exige que a versão da rubrica pertença ao dono
- [X] T034 [P] [US1] Criar o prompt versionado `backend/src/avaliacao/prompts/avaliar_criterio_v1.md` (sistema: avaliar só o critério informado; copiar trechos literais, sem parafrasear e sem reticências; `SEM_EVIDENCIA` com lista vazia quando a resposta não trata do critério) e `backend/src/avaliacao/prompt.py`, com:
  - `VERSAO_PROMPT = "avaliar_criterio_v1"`;
  - `montar(lote, criterio, resposta, indice) -> (sistema, usuario)`: enunciado, critério com níveis e descritores, e resposta entre `<<<` e `>>>`;
  - `esquema(criterio) -> dict`, conforme `contracts/llm-saida.schema.json`, com o enum dos códigos do critério mais `SEM_EVIDENCIA`.
- [X] T035 [P] [US1] Implementar `backend/src/avaliacao/ancora.py` como funções puras, conforme research R5: `normalizar_com_mapa(texto) -> (normalizado, mapa)` e `localizar(texto, trecho) -> (inicio, fim) | None`, com mínimo de 3 palavras e reticências rejeitadas
- [X] T036 [P] [US1] Implementar `backend/src/avaliacao/validacao.py` como função pura `validar(texto_resposta, json_bruto, codigos_validos) -> ResultadoValidacao(valida, motivo_invalidez, nivel_codigo, justificativa, trechos[(texto_citado, localizado, inicio, fim)])`, com as regras de R5 e os motivos de data-model.md
- [X] T037 [P] [US1] Implementar `backend/src/avaliacao/sementes.py`: `semente(semente_base, resposta_id, criterio_id, indice)` = `int(sha256(f"{semente_base}:{resposta_id}:{criterio_id}:{indice}").hexdigest(), 16) % 2**31` (research R3)
- [X] T038 [P] [US1] Implementar `backend/src/avaliacao/estimativa.py` (research R7):
  - `n_chamadas` = respostas elegíveis (sem `LONGA` nem `VAZIA`) × critérios × N;
  - tokens de entrada = soma de `len(sistema + usuario) // 4` dos prompts montados;
  - tokens de saída = `TOKENS_SAIDA_ESTIMADOS` por chamada, substituído pela média observada do lote quando houver ≥ 10 execuções concluídas;
  - custo por `precos.custo_usd` na data de hoje.

  Devolve o formato de `POST /lotes/{id}/rodadas/estimativa/`.
- [X] T039 [US1] Implementar a tarefa Celery `executar_execucao(execucao_id)` em `backend/src/avaliacao/tasks.py`:
  - sai se a execução não estiver `PENDENTE` (idempotência);
  - reserva o custo previsto com `UPDATE ... SET custo_acumulado_usd = custo_acumulado_usd + previsto WHERE custo_acumulado_usd + previsto <= teto_usd`; se nenhuma linha for afetada, marca a rodada `PAUSADA_TETO` e sai deixando `PENDENTE`;
  - marca `EM_ANDAMENTO`, monta o prompt com a semente da execução, chama `get_llm().avaliar`, valida, grava tokens, custo real (ajusta o acumulado pela diferença real − previsto), latência e resposta bruta, e marca `CONCLUIDA`;
  - `autoretry_for=(IAIndisponivel,)`, `retry_backoff=True`, `retry_jitter=True`, `max_retries=6`, `rate_limit=settings.LLM_RATE_LIMIT`;
  - no esgotamento, marca `FALHOU` com `erro` e devolve a reserva;
  - ao final, chama `atualizar_status_rodada`.
- [X] T040 [US1] Implementar `backend/src/avaliacao/services.py`:
  - `criar_rodada(lote, usuario, reaplicacao, confirmar, teto_usd)`:
    - recusa sem `confirmar`;
    - recusa com `codigo="nivel_gratuito"` se o provedor não for `dumb`, o lote não for `sintetico` e `GEMINI_PAID_TIER` não for verdadeiro;
    - recusa reaplicação sem rodada 1 concluída;
    - congela a versão da rubrica e os parâmetros do lote;
    - sorteia `semente_base` com `secrets.randbelow(2**31)`;
    - cria as execuções em `bulk_create` (as de `VAZIA` já `CONCLUIDA`, `SEM_EVIDENCIA`, válidas, custo 0);
    - enfileira as `PENDENTE`.
  - `retomar(rodada, teto_usd=None)`: reenfileira `PENDENTE` e `FALHOU`, zerando `tentativas`.
  - `atualizar_status_rodada(rodada)`: `CONCLUIDA` se não houver pendentes nem falhas; `COM_FALHAS` se não houver pendentes, mas houver falhas.
- [X] T041 [US1] Implementar `backend/src/avaliacao/{serializers,views,urls}.py` para `POST /lotes/{id}/rodadas/estimativa/`, `POST /lotes/{id}/rodadas/`, `GET /rodadas/{id}/`, `POST /rodadas/{id}/retomar/` e `GET /respostas/{id}/execucoes/?rodada=`, conforme contracts/api.md, com permissão de dono do lote ou pesquisador
- [X] T042 [US1] Criar o comando `backend/src/lotes/management/commands/auditar_identificadores.py <arquivo>`. Ele varre sem acento e sem caixa todas as colunas `CharField`/`TextField` de todos os modelos e os arquivos de log configurados, e imprime ocorrências por tabela/campo e o total. Sai com código 1 se o total for maior que 0 (quickstart V1)
- [X] T043 [P] [US1] Criar as páginas de rubrica `frontend/src/pages/Rubricas.tsx` (lista) e `frontend/src/pages/RubricaEditor.tsx` (formulário dinâmico de critérios, com tipo e peso, e de níveis, com rótulo, pontuação e descritor; mínimo de 2 níveis; aviso "esta versão está em uso: salvar cria a versão N+1")
- [X] T044 [P] [US1] Criar `frontend/src/pages/LoteNovo.tsx` (título, enunciado, rubrica, parâmetros avançados recolhidos: N, limiar, mínimo de válidas, teto, sintético) e `frontend/src/pages/Importacao.tsx`:
  - upload e prévia em tabela;
  - seletores "coluna da resposta" e "colunas de identificação";
  - opção de gerar chave;
  - avisos;
  - download automático da chave com o alerta "Guarde este arquivo. Ele não poderá ser gerado de novo."
- [X] T045 [US1] Criar `frontend/src/pages/Rodada.tsx`: estimativa (chamadas, custo e teto editável), botão "Confirmar e executar", barra de progresso com consulta a `GET /rodadas/{id}/` a cada 3 s, estados `PAUSADA_TETO` e `COM_FALHAS` com botão "Retomar"
- [X] T046 [P] [US1] Criar o componente `frontend/src/components/TextoComDestaques.tsx`. Ele recebe `texto` e `destaques: {inicio, fim, cor, rotulo}[]`, divide o texto em segmentos quando há sobreposição e renderiza `<mark>` com `title`. Teste em `frontend/src/components/TextoComDestaques.test.tsx` (sobreposição, destaques adjacentes, texto sem destaque)
- [X] T047 [US1] Criar `frontend/src/pages/RespostaInspecao.tsx`, alimentada por `GET /respostas/{id}/execucoes/`: texto com os trechos das execuções válidas destacados, com uma cor por critério. Para cada critério, lista as execuções com índice, nível, justificativa e, nas inválidas, o motivo

**Checkpoint**: US1 funciona sozinha. Quickstart V1, V2 e V3 passam com o dublê

---

## Phase 4: User Story 2 — Declaração de incerteza (Priority: P1)

**Goal**: consolidado por par, com os estados convergente, divergente, sem evidência e indeterminado; fila que prioriza os não convergentes; cartões na tela da resposta

**Independent Test**: rodada com os 7 roteiros do dublê; cada resposta roteirizada mostra o estado esperado (quickstart V4) e a fila começa pelos não convergentes

### Tests for User Story 2 ⚠️

- [X] T048 [P] [US2] Escrever `backend/tests/unit/test_consolidacao.py` (research R6), cobrindo:
  - 5/5 → `CONVERGENTE` com acordo 1,0;
  - 4-1 → `CONVERGENTE` com 0,8;
  - 3-2 → `DIVERGENTE`;
  - 2-2-1 → `DIVERGENTE`;
  - modal `SEM_EVIDENCIA` com acordo ≥ limiar → `SEM_EVIDENCIA`;
  - `n_validas < min_validas` → `INDETERMINADO`;
  - `limiar ≤ 0,5` → erro;
  - `nivel_modal` preenchido mesmo quando divergente;
  - justificativa representativa = a da execução válida de menor índice;
  - recálculo com limiar 0,6 muda 3-2 para `CONVERGENTE`.
- [X] T049 [P] [US2] Escrever `backend/tests/integration/test_incerteza.py` (dublê, `turma_ficticia`): cada resposta com `[[cenario:X]]` termina no estado esperado; `trecho_inventado` termina `CONVERGENTE` com `n_validas=3`; `json_invalido` termina `INDETERMINADO`; `GET /lotes/{id}/fila/` devolve primeiro as respostas cujo pior estado é não convergente; a `Sugestao` divergente sai **sem** `nivel_sugerido`

### Implementation for User Story 2

- [X] T050 [US2] Criar `Consolidado(rodada, resposta, criterio, estado CONVERGENTE|DIVERGENTE|SEM_EVIDENCIA|INDETERMINADO, nivel_modal FK null, acordo decimal, n_validas, distribuicao JSON, limiar_usado, min_validas_usado)` em `backend/src/avaliacao/models.py`, com `UniqueConstraint(rodada, resposta, criterio)`. Gerar a migração e registrar no admin como só leitura
- [X] T051 [US2] Implementar `backend/src/avaliacao/consolidacao.py` como função pura `consolidar(votos: list[(indice, nivel_codigo)], limiar, min_validas) -> (estado, nivel_modal_codigo, acordo, n_validas, distribuicao)`, mais `representativa_por_nivel(execucoes_validas)`, conforme R6
- [X] T052 [US2] Chamar `recalcular_consolidado(rodada, resposta, criterio)` em `backend/src/avaliacao/services.py` sempre que a última execução do par sair de `PENDENTE`/`EM_ANDAMENTO`, a partir de `executar_execucao` e de `criar_rodada` (para as `VAZIA`). Criar o comando `backend/src/avaliacao/management/commands/recalcular_consolidados.py --rodada ID`
- [X] T053 [US2] Implementar `backend/src/avaliacao/sugestao.py`, com `sugestao(consolidado, condicao) -> dict` no formato exato de "Sugestao (por critério)" de contracts/api.md: convergente com `nivel_sugerido`, `acordo`, justificativa e trechos; divergente com `nivel_sugerido: null` e `alternativas` por nível votado, cada uma com justificativa e trechos da representativa; sem evidência e indeterminado sem `nivel_sugerido`; `SEM_APOIO` → só `{"criterio", "estado": "OCULTO"}`
- [X] T054 [US2] Implementar `GET /lotes/{id}/fila/` em `backend/src/revisao/{views,urls}.py` (app já criada em T001, ainda sem modelos): `estado_pior` da resposta pela prioridade de data-model.md, ordenado por prioridade e depois por código. `n_decididos` e `n_criterios` ficam 0 e total até a US3
- [X] T055 [P] [US2] Criar `frontend/src/pages/Fila.tsx`: lista com o selo do estado pior (cores: divergente, sem evidência e indeterminado em destaque; convergente neutro), contagem por estado no topo e link para a resposta
- [X] T056 [US2] Criar os componentes `frontend/src/components/CartaoCriterio.tsx` (convergente: nível e "5/5", justificativa, trechos destacados no texto ao passar o mouse) e `frontend/src/components/Distribuicao.tsx` (divergente: "Divergente, 3× N2 e 2× N3", uma alternativa por nível com justificativa e trechos, nenhum nível pré-selecionado). Usá-los em `frontend/src/pages/Resposta.tsx`, com a lista bruta de T047 num painel recolhido "Execuções" visível só ao dono ou ao pesquisador

**Checkpoint**: US1 + US2. Quickstart V4 passa

---

## Phase 5: User Story 3 — Decisão docente registrada (Priority: P1)

**Goal**: sessão de correção, decisão por critério com histórico, tempo ativo medido e notas só de respostas finalizadas

**Independent Test**: decidir 10 respostas completas e 5 parciais e alterar uma decisão. `notas.csv` traz 10 linhas, o histórico mostra a substituição e não existe decisão em lote (quickstart V5)

### Tests for User Story 3 ⚠️

- [X] T057 [P] [US3] Escrever `backend/tests/integration/test_decisoes.py`, cobrindo:
  - `tipo` derivado: igual à sugestão → `CONFIRMACAO`; diferente → `ALTERACAO`; sem sugestão exibida → `ESCOLHA`;
  - nova decisão no mesmo critério marca a anterior `vigente=False` e aponta `substitui`;
  - "exatamente uma vigente por (resposta, critério, docente, participacao)";
  - nível de outro critério é recusado;
  - decisão sem sessão aberta daquela resposta é recusada;
  - `tempo_ativo_ms` da sessão = o da última decisão;
  - `notas.csv` traz só respostas finalizadas, com nota = Σ pontuação × peso;
  - não existe rota que aceite lista de decisões.
- [X] T058 [P] [US3] Escrever `backend/tests/contract/test_api_revisao.py`: formatos de `POST /respostas/{id}/sessoes/` (`sessao`, `texto`, `condicao`, `criterios:[Sugestao]`, `decisoes_vigentes`), `POST /sessoes/{id}/decisoes/`, `PATCH /sessoes/{id}/`, `GET /respostas/{id}/historico/` e `GET /lotes/{id}/notas.csv`
- [X] T059 [P] [US3] Escrever `frontend/src/services/tempoAtivo.test.ts` (vitest com timers falsos): conta com a aba visível; pausa em `visibilitychange` oculto; pausa após 60 s sem teclado ou mouse; retoma com nova interação

### Implementation for User Story 3

- [X] T060 [US3] Criar os modelos em `backend/src/revisao/models.py`:
  - `SessaoCorrecao(docente, resposta, condicao COM_APOIO|SEM_APOIO, rodada FK null, aberta_em, tempo_ativo_ms)`;
  - `Decisao(sessao, criterio, nivel, estado_exibido CONVERGENTE|DIVERGENTE|SEM_EVIDENCIA|INDETERMINADO|OCULTO, nivel_sugerido FK null, tipo CONFIRMACAO|ALTERACAO|ESCOLHA|CEGA, motivo opcional, tempo_ativo_ms, substitui FK self null, vigente bool)`.

  Adicionar `UniqueConstraint` parcial (`condition=Q(vigente=True)`) sobre (resposta via sessão, critério, docente). Como a constraint não atravessa FK, desnormalizar `resposta` e `docente` em `Decisao`. O campo `participacao` entra na US5. Gerar a migração e registrar no admin como só leitura.
- [X] T061 [US3] Implementar `backend/src/revisao/services.py`:
  - `abrir_sessao(docente, resposta, condicao="COM_APOIO")`: usa a rodada mais recente `CONCLUIDA`/`COM_FALHAS` e devolve as sugestões via `avaliacao.sugestao`;
  - `registrar_decisao(sessao, criterio, nivel, motivo, tempo_ativo_ms)`: `transaction.atomic`, snapshot de `estado_exibido` e `nivel_sugerido`, derivação de `tipo`, substituição da vigente;
  - `atualizar_tempo(sessao, tempo_ativo_ms)`;
  - `finalizada(resposta, docente)`;
  - `nota(resposta, docente)`.
- [X] T062 [US3] Implementar `backend/src/revisao/{serializers,views,urls}.py` para `POST /respostas/{id}/sessoes/`, `POST /sessoes/{id}/decisoes/`, `PATCH /sessoes/{id}/`, `GET /respostas/{id}/historico/` e `GET /lotes/{id}/notas.csv` (colunas `codigo, <nome de cada critério>, nota_total`). Completar a fila de T054 com `n_decididos` e `finalizada`
- [X] T063 [P] [US3] Implementar `frontend/src/services/tempoAtivo.ts`: classe `CronometroAtivo`, com `iniciar()`, `acumuladoMs()` e `parar()`, a regra de pausa de research R11 e batida `PATCH` a cada 30 s
- [X] T064 [US3] Transformar `frontend/src/pages/Resposta.tsx` em tela de correção:
  - abre a sessão ao entrar;
  - para cada critério: botões de nível (atalhos de teclado 1–9 no critério em foco) e campo de motivo opcional;
  - convergente: "Confirmar N3" (Enter);
  - divergente, sem evidência e indeterminado: exige a escolha explícita de um nível;
  - envia `tempo_ativo_ms` com cada decisão;
  - selo "Finalizada" quando todos os critérios estão decididos;
  - botão "Próxima da fila";
  - gaveta "Histórico".
- [X] T065 [US3] Adicionar à página do lote (`frontend/src/pages/Lote.tsx`) o resumo (respostas, finalizadas, por estado), os links para a fila e para a rodada, e o botão "Baixar notas (CSV)" com a legenda "só respostas com todos os critérios decididos"

**Checkpoint**: núcleo P1 completo (US1 + US2 + US3). Quickstart V1–V5 passam. **Aqui o MVP pode ir para o primeiro teste com o orientador**

---

## Phase 6: User Story 4 — Painel de consistência e relatório (Priority: P2)

**Goal**: métricas por critério, reaplicação, sensibilidade ao limiar e exportação reproduzível

**Independent Test**: reaplicar, abrir o painel, exportar e rodar `analysis/reproduzir_metricas.py`, que termina com `OK: 0 divergências` (quickstart V6)

### Tests for User Story 4 ⚠️

- [ ] T066 [P] [US4] Escrever `backend/tests/unit/test_calculos.py` com fixtures calculadas à mão:
  - concordância exata e adjacente (±1 posição ordinal);
  - QWK igual a `sklearn.metrics.cohen_kappa_score(weights="quadratic")`;
  - concordância seletiva e cobertura;
  - taxa de divergência por critério e por tipo;
  - acordo médio do modal e κ de Fleiss (`statsmodels.stats.inter_rater.fleiss_kappa`);
  - estabilidade entre rodadas;
  - α de Krippendorff ordinal (`krippendorff.alpha(level_of_measurement="ordinal")`);
  - ancoragem;
  - mediana de tempo por condição.
- [ ] T067 [P] [US4] Escrever `backend/tests/integration/test_exportacao_reproducao.py`: rodada, reaplicação e decisões com o dublê; baixar `exportacao.zip`; conferir arquivos e colunas de `contracts/exportacao.md`; executar `analysis/reproduzir_metricas.py` por subprocess e exigir saída `OK: 0 divergências`

### Implementation for User Story 4

- [ ] T068 [US4] Implementar `backend/src/metricas/calculos.py` com as funções puras da tabela de research R10, recebendo listas e dicionários simples (sem ORM), para serem importáveis pelo script de análise
- [ ] T069 [US4] Implementar `backend/src/metricas/painel.py` e `GET /lotes/{id}/painel/?rodada=&limiar=` em `backend/src/metricas/{views,urls}.py`. Ele monta as entradas a partir do banco (modal da rodada × decisão vigente do dono), recalcula os estados em memória quando `limiar` é informado, sem gravar, e devolve as métricas por critério e no total, incluindo a estabilidade entre rodadas quando houver reaplicação
- [ ] T070 [US4] Implementar `backend/src/metricas/exportacao.py` e `GET /lotes/{id}/exportacao.zip`, com os arquivos, colunas e regras de `contracts/exportacao.md`: docentes como `D01…`; `?incluir_texto=1` e `?incluir_motivos=1`; `metricas.json` gerado pelas mesmas funções do painel
- [ ] T071 [P] [US4] Criar `analysis/reproduzir_metricas.py` e `analysis/requirements.txt`. O script é independente do backend e importa só `numpy`, `scikit-learn`, `statsmodels` e `krippendorff` (copia as fórmulas; não importa `backend`). Lê o ZIP, recalcula tudo, compara com `metricas.json` (tolerância 1e-9) e imprime `OK: 0 divergências` ou a lista de diferenças, saindo com código 1
- [ ] T072 [US4] Criar `frontend/src/pages/Painel.tsx`: seletor de rodada e de limiar (0,6 / 0,8 / 1,0) e tabela por critério com o tipo e todas as métricas de R10. Adicionar o botão "Reaplicar lote" (estimativa e confirmação, reaproveitando T045) e "Exportar dados (ZIP)". Antes de qualquer gráfico, carregar a skill `dataviz`

**Checkpoint**: quickstart V6 passa

---

## Phase 7: User Story 5 — Protocolo A com docentes (Priority: P2)

**Goal**: estudo com lote comum, metades A e B, braços e ordem balanceados, ocultação no servidor, painel e exportação do estudo

**Independent Test**: estudo com 8 convidados fictícios: 2 por célula, resposta da metade sem apoio com só `"estado": "OCULTO"`, exportação com tempos por condição (quickstart V8)

### Tests for User Story 5 ⚠️

- [ ] T073 [P] [US5] Escrever `backend/tests/unit/test_alocacao.py`: metades de tamanho igual (±1) e proporção de divergentes parecida (diferença ≤ 1 resposta por estrato); alocação determinística com a mesma semente; 8 participantes → 2 por célula (braço × ordem); `condicao(metade, braco)` com a tabela completa
- [ ] T074 [P] [US5] Escrever `backend/tests/integration/test_estudo.py`, cobrindo:
  - só PESQUISADOR cria estudo;
  - a rodada precisa estar `CONCLUIDA`;
  - depois de `iniciar`, não entra participante novo;
  - o participante recebe 404 em lotes fora do estudo e em `GET /respostas/{id}/execucoes/`;
  - na condição sem apoio, o JSON inteiro da sessão não contém nenhuma das chaves `nivel_sugerido`, `acordo`, `justificativa`, `trechos` ou `alternativas`;
  - decisões do estudo não se misturam com as do dono do lote;
  - a exportação do estudo traz `P01…` e `alocacao.csv`.

### Implementation for User Story 5

- [ ] T075 [US5] Criar os modelos em `backend/src/estudos/models.py`:
  - `Estudo(pesquisador, titulo, lote, rodada, semente_alocacao, status PREPARACAO|EM_ANDAMENTO|ENCERRADO)`;
  - `AlocacaoResposta(estudo, resposta, metade A|B)` com `UniqueConstraint(estudo, resposta)`;
  - `Participacao(estudo, docente, posicao, braco 1|2, ordem SEM_PRIMEIRO|COM_PRIMEIRO, concluida_em)` com `UniqueConstraint(estudo, docente)`.

  Adicionar por migração `participacao` (FK null) a `SessaoCorrecao` e `Decisao` em `backend/src/revisao/models.py`, e incluir `participacao` na constraint de vigência.
- [ ] T076 [P] [US5] Implementar `backend/src/estudos/alocacao.py` como funções puras: `dividir_metades(respostas_com_estado, semente)`, estratificada por divergente ou não; `alocar_participantes(n)`, em rodízio pelas 4 células; `condicao(metade, braco)` (braço 1: A→`SEM_APOIO`, B→`COM_APOIO`; braço 2: o inverso); `blocos(participacao)`, na ordem sem/com ou com/sem
- [ ] T077 [US5] Implementar `backend/src/estudos/services.py`:
  - `criar_estudo`;
  - `convidar(estudo, emails)`: cria `Usuario` sem senha utilizável com papel `DOCENTE` (ou reaproveita o existente) e envia o link de definição de senha gerado com `PasswordResetTokenGenerator` (rota `POST /api/auth/definir-senha/`); em dev, `EMAIL_BACKEND` de console, e a resposta devolve os links ao pesquisador;
  - `iniciar(estudo)`: aloca as metades e os participantes na ordem de aceite;
  - `minha_tarefa(participacao)`: bloco atual, próxima resposta sem finalização e progresso.
- [ ] T078 [US5] Implementar `backend/src/estudos/{serializers,views,urls}.py` para as rotas de "Estudos" de contracts/api.md. `POST /estudos/{id}/respostas/{rid}/sessoes/` reutiliza `revisao.services.abrir_sessao` com a `condicao` **imposta** por `alocacao.condicao` e `participacao` preenchida, e usa `sugestao(..., "SEM_APOIO")` para devolver `OCULTO` (FR-025). Permissões: participante só no próprio estudo; pesquisador só nos estudos que criou
- [ ] T079 [US5] Estender `backend/src/metricas/painel.py` e `exportacao.py` para o estudo: concordância da IA com decisões cegas e com assistidas, ancoragem, α de Krippendorff entre cegos (referência humana), mediana de tempo por condição e por participante, e `alocacao.csv`, com os participantes como `P01…`. Criar as rotas `GET /estudos/{id}/painel/` e `GET /estudos/{id}/exportacao.zip`
- [ ] T080 [P] [US5] Criar `frontend/src/pages/Estudos.tsx` e `frontend/src/pages/EstudoDetalhe.tsx` (pesquisador): criar a partir de lote e rodada; colar a lista de e-mails para convite; "Iniciar" com resumo da alocação; progresso por participante; painel e exportação do estudo
- [ ] T081 [US5] Criar `frontend/src/pages/Participacao.tsx` (participante): faixa fixa com o bloco atual ("Bloco 1 de 2: sem apoio" / "com apoio"), reutilizando `Resposta.tsx` em modo estudo (sem painel de execuções, sem histórico de outros e sem acesso a outras telas) e avançando pelo `minha-tarefa`

**Checkpoint**: quickstart V8 passa. O estudo com docentes pode ser agendado

---

## Phase 8: User Story 6 — Modelo de rubrica reutilizável (Priority: P3)

**Goal**: exportar e importar rubrica como arquivo JSON

**Independent Test**: exportar, importar com outro usuário e comparar critérios, níveis e descritores (quickstart V9)

- [ ] T082 [P] [US6] Escrever `backend/tests/unit/test_modelo_rubrica.py`: a volta completa (exportar e importar) preserva critérios, níveis, descritores, pesos e tipos; o arquivo não contém `dono`, ids nem lotes; `versao_formato` desconhecida é recusada
- [ ] T083 [US6] Implementar `backend/src/rubricas/modelo.py` (`exportar(versao) -> dict` com `versao_formato: 1`, e `importar(dono, dict)`, que reutiliza `criar_rubrica`) e as rotas `GET /rubricas/{id}/modelo/` e `POST /rubricas/importar-modelo/` em `backend/src/rubricas/{views,urls}.py`
- [ ] T084 [P] [US6] Adicionar os botões "Exportar modelo" e "Importar modelo" em `frontend/src/pages/Rubricas.tsx`. Criar `docs/modelos/verificacao-validacao.json` como primeiro modelo público

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T085 Criar o comando `backend/src/rubricas/management/commands/carregar_exemplo.py`, que cria para o superusuário a rubrica 4×4 "Verificação e validação", com os critérios Conceituação (objetivo), Distinção (objetivo), Exemplificação (interpretativo) e Clareza (interpretativo), e níveis com descritores (quickstart "Subir")
- [ ] T086 [P] Configurar `LOGGING` em `backend/src/config/settings.py` com um filtro que remove `texto`, `resposta_bruta` e `justificativa` de qualquer registro, e garantir que nenhuma view ou tarefa registre o texto da resposta. Criar as settings de produção (`DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_*`) em `backend/src/config/settings.py` por variável de ambiente
- [ ] T087 [P] Escrever `docs/manual-docente.md` (entrega "manual de uso" do canvas): criar rubrica, importar planilha do Moodle, ler estimativa e teto, interpretar convergente, divergente, sem evidência e indeterminado, corrigir, exportar notas e guardar a chave
- [ ] T088 [P] Escrever o rascunho `docs/parecer-tratamento-dados.md` a partir de research R9, para revisão do orientador: dados tratados, anonimização na carga, envio de texto anonimizado ao Google só em nível pago (com os trechos dos termos), retenção, cláusula de idade e o que muda para a educação básica
- [ ] T089 [P] (Opcional, só se houver GPU para o estudo, research R14) Criar `OllamaLLMProvider` em `backend/src/conectores/ollama.py`, com `format` = esquema e `seed`, registrado como `"ollama"`, mais a entrada de preço 0 em `precos.py`
- [ ] T090 Rodar os cenários V1–V6, V8 e V9 de `quickstart.md` com o dublê e corrigir o que falhar. Rodar `ruff check` e `pytest --cov` exigindo ≥ 90% de cobertura em `ancora.py`, `consolidacao.py`, `anonimizacao.py`, `alocacao.py` e `calculos.py`
- [ ] T091 Rodar o V7 de `quickstart.md` com o Gemini real (lote sintético de 10 respostas × 4 critérios × 5, cerca de 200 chamadas e menos de US$ 1 pela estimativa de R7), com a chave paga do Extenda e `GEMINI_PAID_TIER=true`. Registrar em `research.md` R7 os tokens médios, o custo real × estimado, a taxa de execuções válidas e as falhas absorvidas por retry. Ajustar `TOKENS_SAIDA_ESTIMADOS` se o custo real passar de 1,2 × a estimativa

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende do Setup e bloqueia todas as histórias
- **US1 (Phase 3)**: depende da Foundational
- **US2 (Phase 4)**: depende da US1 (consome execuções e rodadas)
- **US3 (Phase 5)**: depende da US2 (a sessão devolve `Sugestao`)
- **US4 (Phase 6)**: depende da US3 (concordância exige decisões)
- **US5 (Phase 7)**: depende da US3 (sessões e decisões) e da US4 (painel e exportação)
- **US6 (Phase 8)**: depende só da US1 (rubricas) e pode ser feita a qualquer momento depois dela
- **Polish (Phase 9)**: T085–T089 podem começar depois da US1. T090 e T091 vêm depois das histórias desejadas

### Within Each User Story

- Testes escritos e falhando antes da implementação
- Modelos → serviços puros → serviços com ORM/tarefas → views → frontend
- Funções puras (`anonimizacao`, `ancora`, `validacao`, `sementes`, `estimativa`, `consolidacao`, `alocacao`, `calculos`) antes de quem as usa

### Parallel Opportunities

- Setup: T004–T008 em paralelo depois de T003
- Foundational: T011, T013–T019 em paralelo depois de T009/T010
- US1: T020–T025 (testes) em paralelo; T026–T028 (modelos) em paralelo; T031 e T034–T038 (funções puras) em paralelo; T043, T044 e T046 (frontend) em paralelo com o backend
- US4: T071 (script independente) em paralelo com T068–T070
- US6 inteira em paralelo com US2–US5

---

## Parallel Example: User Story 1

```bash
# Testes da US1, juntos:
Task: "T020 test_anonimizacao.py"   Task: "T021 test_ancora.py"   Task: "T022 test_importacao.py"
Task: "T023 test_rodada.py"         Task: "T024 test_sem_identificadores.py"   Task: "T025 test_api_us1.py"

# Modelos, juntos:
Task: "T026 rubricas/models.py"     Task: "T027 lotes/models.py"  Task: "T028 avaliacao/models.py"

# Funções puras, juntas:
Task: "T031 anonimizacao.py"  Task: "T035 ancora.py"  Task: "T036 validacao.py"
Task: "T037 sementes.py"      Task: "T038 estimativa.py"  Task: "T034 prompt.py"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2
2. Phase 3 (US1): **parar e validar** com V1–V3. Já é demonstrável: rubrica, carga anônima e pré-avaliação ancorada
3. Phases 4 e 5 (US2, US3): **núcleo P1 completo**, a versão de teste com o orientador (V1–V5)
4. Uma rodada real com o Gemini (T091) antes de convidar docentes

### Incremental Delivery

1. US1 → demo interna
2. US2 + US3 → teste com o orientador e primeiros lotes reais cedidos (depois do parecer, T088)
3. US4 → métricas para o TCC e o artigo
4. US5 → estudo com 8 a 12 docentes (depois da aprovação ética)
5. US6 → repositório público e oficina

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente
- Commit ao fim de cada tarefa ou grupo lógico
- Nunca carregar lote real antes de T024 passar e de o parecer (T088) ser revisado
- Nenhum teste chama o Gemini. O único consumo real planejado é o T091
