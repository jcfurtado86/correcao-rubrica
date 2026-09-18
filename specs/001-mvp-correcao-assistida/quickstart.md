# Quickstart — validação ponta a ponta do MVP

Roteiro para provar que o MVP cumpre a [spec](spec.md). Os cenários V1 a V6, V8 e V9 rodam com
o dublê (modelo "Dublê" no lote), sem custo nem rede. O V7 usa o Gemini real e custa menos de
US$ 1. Comandos conferidos contra o stack em 2026-09-18.

## Pré-requisitos

- Docker + Docker Compose
- `.env` a partir de `.env.example` (nunca versionado). Para o V7: `GEMINI_API_KEY` de projeto
  **com faturamento** (a mesma do Extenda) e `GEMINI_PAID_TIER=true`. Com a chave, os modelos
  Gemini aparecem para escolha na criação do lote. `LLM_PROVIDER` só define o padrão.

## Subir

```bash
docker compose up -d                       # db, redis, backend, worker, frontend
docker compose exec backend python src/manage.py migrate
docker compose exec backend python src/manage.py createsuperuser   # papel PESQUISADOR
docker compose exec backend python src/manage.py carregar_exemplo  # rubrica 4×4 (docs/modelos/)
```

`carregar_exemplo` só cria a rubrica e deixa a planilha `dados_sinteticos/turma_ficticia.xlsx`
(40 respostas com identificadores plantados nas colunas e dentro dos textos) para ser importada
pela interface. A importação faz parte do teste.

Testes automatizados (unitários, integração e contrato, em 8 processos; nenhum chama modelo real):

```bash
docker compose exec backend pytest        # ou, no host: cd backend && .venv/bin/pytest
cd frontend && npm test                   # funções do frontend (vitest)
```

Se `requirements-dev.txt` mudou, reconstrua a imagem antes (`docker compose build backend worker`).

## Cenários

| # | Cenário | Como | Resultado esperado | Cobre |
|---|---|---|---|---|
| V1 | Carga anônima | Criar lote pela interface, importar `turma_ficticia.xlsx`, mapear colunas, baixar a chave | 40 respostas `R001…`. Chave baixada uma vez. `docker compose exec backend python src/manage.py auditar_identificadores /dados_sinteticos/identificadores_plantados.txt` varre banco, logs e respostas brutas do modelo e retorna **0 ocorrências** | US1, FR-005/006, SC-003 |
| V2 | Estimativa e teto | Pedir pré-avaliação | Tela mostra 800 chamadas e custo estimado, e só executa com confirmação. Com teto baixo, a rodada para em `PAUSADA_TETO`, e retomar com teto maior conclui sem repetir execuções | FR-010/011 |
| V3 | Âncora | Abrir respostas após a rodada | Toda sugestão tem trecho destacado. As respostas roteirizadas com "trecho inventado" aparecem com execuções inválidas (`TRECHO_NAO_LOCALIZADO`), fora da contagem | US1, FR-009, SC-002 |
| V4 | Incerteza | Fila do lote | Roteiros unânime → `Convergente 5/5`; 4-1 → `Convergente 4/5`; 3-2 → `Divergente` com as 2 alternativas; 2-2-1 → `Divergente`; sem evidência → `Sem evidência`; tudo inválido → `Indeterminado`. Os não convergentes vêm primeiro | US2, FR-013–016 |
| V5 | Decisão e notas | Decidir 10 respostas completas e 5 parciais, alterar uma decisão | `notas.csv` tem 10 linhas. O histórico mostra a decisão substituída. Não há botão de aprovar em lote | US3, FR-017–019, SC-004 |
| V6 | Métricas reproduzíveis | Reaplicar o lote, abrir o painel e baixar `exportacao.zip`, depois rodar `python analysis/reproduzir_metricas.py exportacao.zip` | O script imprime as mesmas métricas do painel e termina com `OK: 0 divergências` | US4, FR-021–023, SC-006 |
| V7 | Gemini real | Lote sintético de 10 respostas × 4 critérios × N=5 com o modelo `gemini-3.6-flash` escolhido no lote (ou `python3 e2e/v7_modelo_real.py`) | 200 chamadas concluídas (retries absorvem 503). Custo real ≤ 1,2 × estimativa. ≥ 95% das execuções válidas | FR-012, SC-005 |
| V8 | Estudo protocolo A | Criar estudo com a rodada do V6, convidar 8 e-mails fictícios, iniciar | 2 participantes por célula (braço × ordem). Numa resposta da metade sem apoio, a resposta da API tem só `"estado": "OCULTO"` (conferir no DevTools). Exportação com tempos por condição | US5, FR-024/025 |
| V9 | Modelo de rubrica | Exportar a rubrica, importar com outro usuário | Critérios, níveis e descritores iguais, sem dados de lote | US6, FR-003 |

## Automação e resultado (2026-09-18)

Cada cenário tem script em [`e2e/`](../../e2e/README.md): V1–V3 `us1.py`, V4 `us2.py`, V5
`us3.py`, V6 `us4.py`, V7 `v7_modelo_real.py`, V8 `us5.py`, V9 `us6.py`. Todos passaram na
data acima. O V7, com o `gemini-3.6-flash` real, deu 100% de execuções válidas, 200 chamadas em
126 s e custo real de 0,66 × a estimativa (detalhes em [research R7](research.md)).

## Bloqueios de pesquisa (fora do sistema)

- Declaração ou aprovação ética aplicável ao estudo com docentes e termo de cessão das respostas
  reais, antes de carregar lote real.
- Parecer de tratamento de dados (canvas), incluindo o envio de texto anonimizado ao Google em
  nível pago ([research R9](research.md#r9-privacidade-e-lgpd)).
