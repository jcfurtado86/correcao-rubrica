# Implementation Plan: MVP — Correção Assistida por Rubrica com Aferição de Consistência

**Branch**: `001-mvp-correcao-assistida` | **Date**: 2026-09-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-mvp-correcao-assistida/spec.md`

## Summary

Aplicação web em que a docente define uma rubrica, importa respostas discursivas anonimizadas
na carga e recebe, para cada par (resposta, critério), uma pré-avaliação feita por N execuções
independentes do Gemini. Cada execução precisa citar trechos literais do texto, verificados no
servidor. O consolidado declara convergência ou divergência, nunca um valor único quando as
execuções discordam, e a docente decide tudo, com registro e tempo medido. Painel e exportação
produzem as métricas do TCC (concordância, estabilidade em reaplicação, divergência, tempo). Um
módulo de estudo implementa o protocolo A (metades contrabalançadas com e sem apoio) para 8 a
12 docentes.

Abordagem técnica: stack do Extenda (Django + DRF + Celery + React), com o Gemini 3.6 Flash
atrás de uma factory de provedores com dublê determinístico. Uma tarefa Celery por execução,
com retry e teto de custo, e sementes distintas por execução para medir a variação sem
escondê-la ([research R3](research.md#r3-piloto-variabilidade-sementes-e-âncoras-medido)).

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript 5.7 (frontend)

**Primary Dependencies**: Django 5.2, djangorestframework, drf-spectacular, simplejwt,
Celery 5 + redis, google-genai, openpyxl, scikit-learn, statsmodels,
krippendorff. Frontend: React 18, react-router 7, Vite 6

**Storage**: PostgreSQL 16 (sem pgvector). Redis só como broker do Celery

**Testing**: pytest + pytest-django + pytest-xdist (unit / integration / contract, 8 processos),
com o dublê `dumb` roteirizado no lugar do modelo. Vitest para funções do frontend (cronômetro de
tempo ativo, destaque de trechos). Playwright (Python) para os e2e por história contra o stack.
ruff. Estado em 2026-09-18: 176 testes no backend (cobertura 92%; módulos puros de 96% a 100%),
9 no frontend e 6 e2e

**Target Platform**: servidor Linux com Docker Compose. Navegador desktop recente

**Project Type**: aplicação web (API + SPA + worker)

**Performance Goals**: rodada de 800 chamadas em ≤ 30 min (≥ 0,45 chamada/s, concorrência 8).
Medido no V7: 1,6 chamada/s. Fila e tela de resposta em < 1 s para lote de até 200 respostas

**Constraints**: nenhum identificador de estudante persistido; só nível pago do Gemini para dado
real; teto de custo por rodada; texto nunca truncado; pré-avaliação oculta no servidor na
condição sem apoio

**Scale/Scope**: até 200 respostas por lote, 10 critérios, N ≤ 10 (≤ 20 mil execuções por
rodada); até 30 docentes; cerca de 12 telas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano cumpre | Estado |
|---|---|---|
| I. Decisão docente soberana | Nota só existe como soma de decisões vigentes. `notas.csv` só com respostas finalizadas. Nenhum endpoint de decisão em lote. `Decisao` guarda sugestão exibida, valor decidido, tipo, autor, instante e tempo | ✅ |
| II. Ancoragem obrigatória | Verificação de trecho no servidor (R5). Execução sem trecho localizado é inválida e não vota. `SEM_EVIDENCIA` é estado próprio e nunca vira nível | ✅ |
| III. Incerteza como informação | N execuções com sementes distintas, todas persistidas. Consolidação por limiar (R6). Divergente sai sem `nivel_sugerido` pela API. Fila prioriza não convergentes | ✅ |
| IV. Privacidade desde a carga | Upload em memória. Colunas de identificação descartadas. Varredura no texto. Chave de reidentificação entregue uma vez. Auditoria automatizada (V1). Nível pago obrigatório (R9) | ✅ |
| V. Rastreabilidade | Execução guarda modelo, versão do prompt, hash da rubrica, semente, tokens, custo e resposta bruta. Versão congelada. Exportação + script de reprodução (SC-006) | ✅ |
| VI. Simplicidade e custo | Um repositório e um compose. Provedor atrás de interface única. Estimativa, teto e cache por rodada. **Celery + Redis é infraestrutura extra**: ver Complexity Tracking | ⚠️ justificado |

Reavaliação pós-desenho (Fase 1): data-model e contratos mantêm todos os itens acima. A
ocultação na condição sem apoio ficou no servidor ([api.md](contracts/api.md#sugestao-por-critério)),
o que reforça o FR-025. Nenhuma violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/001-mvp-correcao-assistida/
├── spec.md
├── plan.md              # este arquivo
├── research.md          # Fase 0: decisões, piloto medido, preços, LGPD
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1: roteiro de validação V1–V9
├── contracts/
│   ├── api.md                  # REST
│   ├── llm-saida.schema.json   # saída exigida do modelo
│   ├── importacao.md           # planilha, anonimização, chave
│   └── exportacao.md           # dados de pesquisa
├── checklists/requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

Estado real em 2026-09-18:

```text
backend/
├── src/
│   ├── config/           # settings (12-factor), urls, celery.py
│   ├── core/             # Usuario, autenticacao (JWT, definir-senha), permissions, exceptions, logs
│   ├── conectores/       # llm.py (interface/factory), gemini.py, duble.py, precos.py, catalogo.py
│   ├── rubricas/         # modelos, services (versão/congelamento/hash), modelo.py (JSON), carregar_exemplo
│   ├── lotes/            # Lote, Resposta; importacao.py, anonimizacao.py, auditoria.py (+ comando)
│   ├── avaliacao/        # Rodada, Execucao, Trecho, Consolidado
│   │   ├── prompts/avaliar_criterio_v1.md, avaliar_criterio_v2.md (vigente)
│   │   ├── prompt.py, ancora.py, validacao.py, sementes.py, consolidacao.py   # puros
│   │   ├── estimativa.py, sugestao.py, services.py, tasks.py (executar_execucao)
│   │   └── management/commands/recalcular_consolidados.py
│   ├── revisao/          # SessaoCorrecao, Decisao; fila.py, services.py, notas.csv
│   ├── estudos/          # Estudo, AlocacaoResposta, Participacao; alocacao.py (puro), services.py
│   └── metricas/         # calculos.py (puro), painel.py, estudo.py, exportacao.py
├── tests/{unit,integration,contract}/ + conftest.py, fabricas.py
├── requirements.txt / requirements-dev.txt / pyproject.toml (ruff, pytest -n 8)
└── Dockerfile
frontend/src/
├── pages/            # Login, DefinirSenha, Rubricas, RubricaEditor, Lotes, LoteNovo, Lote,
│                     # Importacao, Rodada, Fila, Resposta, RespostaInspecao, Painel,
│                     # Estudos, EstudoDetalhe, Participacao
├── components/       # PainelDeCorrecao, CartaoCriterio, Distribuicao, TextoComDestaques,
│                     # destaques.ts (+ teste), graficos/{BarrasAgrupadas,BarrasEmpilhadas,Dica}
└── services/         # api.ts, auth.tsx, tipos.ts, useCarregar.ts, tempoAtivo.ts (+ teste)
analysis/reproduzir_metricas.py   # independente do backend: lê o ZIP e recalcula (SC-006)
e2e/                              # Playwright por história + V7 com modelo real (ver e2e/README.md)
dados_sinteticos/                 # gerador da turma fictícia + identificadores plantados
docs/                             # manual da docente, rascunho do parecer, modelos/ de rubrica
specs/001-mvp-correcao-assistida/piloto/   # script do piloto de variabilidade (R3)
docker-compose.yml                # db, redis, backend, worker, frontend (portas 55433/6380/8810/5183)
.env.example
```

**Structure Decision**: aplicação web no formato do Extenda (`backend/src/<apps Django>` +
`frontend/`). Os módulos de domínio críticos (`ancora`, `consolidacao`, `anonimizacao`,
`alocacao`, `calculos`) são funções puras sem ORM, testáveis isoladamente, que a constituição
exige com teste antes da integração. `analysis/` fica fora do backend de propósito: é o
verificador independente das métricas.

## Desvios registrados na implementação

Resumo do que mudou em relação ao desenho acima e às descrições das tarefas. Os documentos da
feature (spec, data-model, contratos, research, quickstart) já refletem o estado real.

- **Escolha do modelo por lote**: catálogo `GET /modelos/` (dublê e, com chave, os Gemini) e
  `provedor_llm`/`modelo_llm` escolhidos ao criar o lote.
- **Modelo local descartado** pelo orientador. Um adaptador Ollama chegou a ser escrito e foi
  removido (T089).
- **Prompt v2 e robustez do Gemini** depois do V7 real: ausência de conteúdo vira sem evidência,
  teto de 8.192 tokens de saída e timeout de 60 s. A rodada guarda a versão do prompt (R7).
- **Nova tentativa manual na tarefa** (`self.retry` com espera exponencial), em vez de
  `autoretry_for`, com laço síncrono nos testes; recuperação de execução abandonada e
  `visibility_timeout` de 10 min (R8).
- **Rotas além do desenho original**: `GET /lotes/`, `GET /lotes/{id}/rodadas/`,
  `GET /respostas/{id}/execucoes/` e `/sugestoes/`, `GET /modelos/`, `GET /estudos/`,
  `GET /estudos/{id}/`, `/criterios/`, `/encerrar/` e `POST /auth/definir-senha/`
  ([api.md](contracts/api.md)).
- **Estudo**: só respostas elegíveis, participantes na ordem do convite, ordem das respostas
  embaralhada por participante (R12).
- **allauth dispensado** (2026-09-18, fase de implementação): no Extenda ele serve para
  autocadastro, verificação de e-mail e login social, e nada disso existe aqui (FR-026: contas só
  por convite ou admin). O login usa simplejwt com e-mail. O convite de estudo usa
  `PasswordResetTokenGenerator` do Django para o link de definição de senha. Menos dependência,
  mesmo resultado (Princípio VI).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Celery + Redis (fila externa, Princípio VI) | ~800 chamadas por rodada com retry e backoff (o piloto recebeu 503 e uma latência de 38 s), `rate_limit`, concorrência controlada e retomada. É o stack já operado no Extenda (diretriz do orientador), com compose e worker prontos para copiar | Fila na própria tabela do Postgres (`SKIP LOCKED`) evitaria o Redis, mas exigiria escrever à mão retry, backoff, rate limit e supervisão do worker, sem reuso do Extenda |
