# Contrato da API REST

Base `/api/`, JSON, autenticação JWT (simplejwt) com `Authorization: Bearer <access>`. O OpenAPI
é gerado pelo drf-spectacular em `/api/schema/` (interface em `/api/docs/`). Este arquivo fixa o
comportamento que os testes de contrato verificam e está conferido contra o código de
2026-09-18.

**Erros**: `{"detail": "...", "codigo": "..."}`. Erro de validação de campos traz também
`"campos": {campo: [mensagens]}`, com `codigo: "invalido"`. Recurso de outra pessoa responde `404`
(não se revela que existe). Ação reservada ao pesquisador responde `403`.

**Permissões** (FR-026/027): a docente só acessa os próprios recursos. O participante de estudo
acessa apenas as respostas do lote do estudo, pelas rotas de estudo. O pesquisador acessa os
estudos que criou e o lote comum deles.

## Autenticação

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `POST /auth/token/` | `{email, password}` → `{access, refresh}` | limite `THROTTLE_LOGIN` por IP (padrão 10/min). Acesso vale 60 min e renovação 7 dias, com rotação |
| `POST /auth/token/refresh/` | `{refresh}` → `{access, refresh}` | |
| `GET /auth/me/` | `{id, email, nome, papel}` | |
| `POST /auth/definir-senha/` | `{uid, token, senha}` → `{email}` | anônimo. Link do convite. Vale uma vez (o token muda com a senha). Senha passa pelos validadores do Django (`senha_fraca`); link inválido gera `link_invalido` |

## Rubricas

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `GET /rubricas/` | `[{id, titulo, descricao, versao_vigente: {id, numero, congelada}, n_criterios, criado_em}]` | só as da usuária |
| `POST /rubricas/` | `{titulo, descricao?, criterios:[{nome, descricao?, peso?, tipo?, niveis:[{rotulo, pontuacao, descritor?}]}]}` → `201` Rubrica | ≥ 1 critério e ≥ 2 níveis por critério. `ordem` e `codigo` (`N1…`) são derivados da posição |
| `GET /rubricas/{id}/` | Rubrica | |
| `PUT /rubricas/{id}/` | mesmo corpo do POST → Rubrica | edita a versão vigente (`200`). Se ela está congelada, cria a versão seguinte (`201`) |
| `GET /rubricas/{id}/modelo/` | arquivo JSON `{versao_formato: 1, titulo, descricao, criterios}` | sem dono, ids nem lotes (US6) |
| `POST /rubricas/importar-modelo/` | multipart `arquivo` (até 1 MB) → `201` Rubrica | `modelo_invalido` para JSON ruim ou `versao_formato` desconhecida |

**Rubrica**: `{id, titulo, descricao, versao: {id, numero, congelada, hash, em_uso, criterios: [{id, ordem, nome, descricao, peso, tipo, niveis: [{id, ordem, codigo, rotulo, descritor, pontuacao}]}]}}`.

## Modelos de linguagem

| Método e rota | Resposta | Regras |
|---|---|---|
| `GET /modelos/` | `[{provedor, modelo, rotulo, entrada_por_milhao, saida_por_milhao}]` | catálogo do servidor: o dublê sempre; os Gemini só com `GEMINI_API_KEY` configurada. Preços em US$ por milhão de tokens, na data de hoje |

## Lotes e importação

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `GET /lotes/` | `[LoteResumo]` | só os da usuária |
| `POST /lotes/` | `{titulo, enunciado, versao_rubrica, n_execucoes?, limiar_acordo?, min_validas?, provedor_llm?, modelo_llm?, teto_usd?, sintetico?}` → `201` Lote | validações do [data-model](../data-model.md#lote). A versão da rubrica tem que ser da usuária. O par provedor/modelo tem que estar em `GET /modelos/` |
| `GET /lotes/{id}/` | Lote | dono ou pesquisador de estudo sobre o lote |
| `POST /lotes/{id}/importacao/previa/` | multipart `arquivo` → `{colunas, amostra (5 linhas), total_linhas}` | nada é gravado |
| `POST /lotes/{id}/importacao/` | multipart `arquivo`, `coluna_resposta`, `colunas_identificacao` (repetido), `gerar_chave` → `201` `{n_respostas, avisos:[{codigo, tipo}], chave_reidentificacao: {nome_arquivo, conteudo_base64} \| null}` | regras em [importacao.md](importacao.md). Uma vez por lote (`409 ja_importado`) |
| `GET /lotes/{id}/respostas/` | `[{id, codigo, n_caracteres, n_substituicoes, aviso}]` | sem texto |

**LoteResumo**: `{id, titulo, enunciado, versao_rubrica, rubrica_titulo, n_execucoes, limiar_acordo, min_validas, provedor_llm, modelo_llm, teto_usd, sintetico, criado_em, n_respostas}`.
**Lote**: LoteResumo + `{avisos: {VAZIA: n, LONGA: n}, versao: {id, numero, rubrica}, criterios: [critério com níveis], rodadas: [{id, numero, status, modelo}]}`.

## Rodadas

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `POST /lotes/{id}/rodadas/estimativa/` | `{}` → `{n_chamadas, respostas_elegiveis, criterios, n_execucoes, tokens_entrada_est, tokens_saida_est, custo_estimado_usd, teto_usd, base_saida: configuracao\|observada, preco_vigente: {modelo, entrada_por_milhao, saida_por_milhao}}` | não chama o modelo. Entrada = caracteres dos prompts ÷ 4; saída = `TOKENS_SAIDA_ESTIMADOS` ou a média observada do lote (R7) |
| `GET /lotes/{id}/rodadas/` | `[Rodada]` | |
| `POST /lotes/{id}/rodadas/` | `{confirmar: true, reaplicacao?: bool, teto_usd?}` → `201` Rodada `EM_EXECUCAO` | recusas: `confirmacao_necessaria`; `nivel_gratuito` (lote não sintético com Gemini sem `GEMINI_PAID_TIER`); `rodada_existente` (`409`, use reaplicação); `sem_rodada_concluida` (reaplicação sem a rodada 1 finalizada); `sem_respostas`. Congela a versão da rubrica |
| `GET /rodadas/{id}/` | Rodada | o frontend consulta a cada 3 s |
| `POST /rodadas/{id}/retomar/` | `{teto_usd?}` → Rodada | reenfileira `PENDENTE` e `FALHOU`, e recupera `EM_ANDAMENTO` abandonada há mais de 10 min. Seguro repetir |
| `GET /respostas/{id}/execucoes/?rodada=N` | `{id, codigo, texto, aviso, rodada, criterios: [{criterio, nome, ordem, execucoes: [{indice, status, valida, motivo_invalidez, nivel_codigo, justificativa, erro, trechos: [{texto_citado, localizado, inicio, fim}]}]}]}` | inspeção das execuções brutas, só para o dono do lote ou o pesquisador. Sem `rodada`, usa a mais recente |

**Rodada**: `{id, lote, numero, status, provedor, modelo, versao_prompt, custo_estimado_usd, custo_acumulado_usd, teto_usd, criado_em, concluida_em, total, pendentes, concluidas, invalidas, falhas}`.

## Revisão

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `GET /lotes/{id}/fila/` | `{rodada, contagem: {estado: n}, respostas: [{resposta, codigo, estado_pior, estados: {estado: n}, n_decididos, n_criterios, finalizada}]}` | não convergentes primeiro (FR-016), depois por código. `INDISPONIVEL` conta como não convergente. Decididos = decisões vigentes da usuária fora de estudo |
| `GET /respostas/{id}/sugestoes/` | `{id, codigo, texto, aviso, rodada, criterios: [Sugestao]}` | leitura, só para o dono do lote ou o pesquisador |
| `POST /respostas/{id}/sessoes/` | → `201` `{sessao, resposta, codigo, texto, aviso, condicao, rodada, criterios: [Sugestao], decisoes_vigentes: [Decisao]}` | só o dono do lote. Usa a rodada de referência (a última finalizada) |
| `POST /sessoes/{id}/decisoes/` | `{criterio, nivel, motivo?, tempo_ativo_ms}` → `201` Decisao | uma por chamada: lista no corpo é recusada (`decisao_em_lote_proibida`). Substitui a vigente anterior. Recusas: `criterio_invalido`, `nivel_invalido`, `tempo_invalido` |
| `PATCH /sessoes/{id}/` | `{tempo_ativo_ms}` → `{sessao}` | batida periódica (diagnóstico). A métrica usa o tempo da última decisão |
| `GET /respostas/{id}/historico/` | `[Decisao]` em ordem cronológica, inclusive as substituídas | só o dono do lote |
| `GET /lotes/{id}/notas.csv` | CSV `codigo, <nome de cada critério>, nota_total` (pontos × peso) | só respostas com todos os critérios decididos (FR-019) |

**Decisao**: `{id, criterio, nivel, nivel_codigo, tipo: CONFIRMACAO|ALTERACAO|ESCOLHA|CEGA, estado_exibido, nivel_sugerido, motivo, tempo_ativo_ms, vigente, substitui, criado_em}`.

### Sugestao (por critério)

```jsonc
// COM_APOIO, convergente
{ "criterio": 12, "estado": "CONVERGENTE",
  "nivel_sugerido": {"id": 40, "codigo": "N3", "rotulo": "Adequado", "ordem": 3},
  "acordo": {"votos": 5, "validas": 5}, "justificativa": "…",
  "trechos": [{"inicio": 130, "fim": 211, "texto": "…"}] }

// COM_APOIO, divergente: sem nivel_sugerido, uma alternativa por nível votado (mais votada primeiro)
{ "criterio": 12, "estado": "DIVERGENTE", "nivel_sugerido": null, "acordo": {"votos": 3, "validas": 5},
  "alternativas": [{"nivel": {...}, "votos": 3, "justificativa": "…", "trechos": [...]},
                   {"nivel": {...}, "votos": 2, "justificativa": "…", "trechos": [...]}] }

// COM_APOIO, SEM_EVIDENCIA: sem nivel_sugerido, com acordo e justificativa
// COM_APOIO, INDETERMINADO: sem nivel_sugerido, com acordo e as alternativas que houver
// Sem consolidado (resposta longa, rodada em curso):
{ "criterio": 12, "estado": "INDISPONIVEL", "nivel_sugerido": null }

// SEM_APOIO (estudo): nenhum outro campo sai do servidor
{ "criterio": 12, "estado": "OCULTO" }
```

## Painel e exportação

| Método e rota | Resposta | Regras |
|---|---|---|
| `GET /lotes/{id}/painel/?rodada=N&limiar=x` | `{rodada, rodadas, limiar, recalculado, modelo, custo: {estimado_usd, acumulado_usd}, criterios: [Bloco + {criterio, nome, tipo}], total: Bloco, por_tipo: {OBJETIVO, INTERPRETATIVO}, tempo: {n_respostas, mediana_ms, media_ms}}` | padrão: rodada 1. `limiar` em (0,5; 1] recalcula os estados só para exibir, sem gravar |
| `GET /lotes/{id}/exportacao.zip?incluir_texto=1&incluir_motivos=1` | ver [exportacao.md](exportacao.md) | texto e motivos só quando pedidos |

**Bloco**: `{n_pares, estados, taxa_divergencia, taxa_nao_convergente, acordo_medio, fleiss, concordancia: {n, exata, adjacente, qwk}, seletiva: {cobertura, n_convergentes, n_nao_convergentes, exata_convergentes, exata_nao_convergentes}, estabilidade: {n, exata, qwk} | null, distribuicao_decidida}`. Definições no [research R10](../research.md#r10-métricas).

## Estudos

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `GET /estudos/` | `[Estudo]` | os criados pela usuária (`papel: PESQUISADOR`) e aqueles de que participa (`PARTICIPANTE`) |
| `POST /estudos/` | `{titulo, lote, rodada}` → `201` Estudo | só PESQUISADOR (`403`) e dono do lote. A rodada precisa estar `CONCLUIDA` (`rodada_nao_concluida`) |
| `GET /estudos/{id}/` | Estudo | pesquisador ou participante |
| `POST /estudos/{id}/convites/` | `{emails:[...]}` (1 a 50) → `201` `{convites:[{email, link, posicao}]}` | cria a conta sem senha (ou reaproveita). `link` para `/definir-senha/{uid}/{token}/`, nulo se a conta já tem senha. Recusa `estudo_iniciado` depois de iniciar |
| `POST /estudos/{id}/iniciar/` | → `{metade_A, metade_B, participantes:[{posicao, docente, braco, ordem}]}` | aloca metades (só respostas elegíveis) e braços (R12). Recusas: `estudo_iniciado`, `sem_participantes` |
| `POST /estudos/{id}/encerrar/` | → `{status}` | |
| `GET /estudos/{id}/criterios/` | `[critério com níveis]` | participante ou pesquisador |
| `GET /estudos/{id}/minha-tarefa/` | `{iniciado, concluido, bloco_atual: {numero, de, metade, condicao} \| null, proxima_resposta: {id, codigo} \| null, progresso: [{bloco, condicao, feitas, total}]}` | participante. A ordem dentro do bloco é embaralhada por participante |
| `POST /estudos/{id}/respostas/{rid}/sessoes/` | igual a `POST /respostas/{id}/sessoes/` | condição imposta pela alocação e rodada do estudo. Em `SEM_APOIO`, cada critério sai só como `{criterio, estado: "OCULTO"}`. Recusa `estudo_fechado` fora de `EM_ANDAMENTO` |
| `GET /estudos/{id}/painel/` | `{estudo, status, rodada, cegos, assistidos, ancoragem: {exata, exata_convergentes}, referencia_humana: {cegos, assistidos}, tempo: {SEM_APOIO, COM_APOIO, diferenca_pareada_mediana_ms, n_pareados}, participantes: [...]}` | só o pesquisador (participante recebe `403`). Inclui o e-mail dos participantes |
| `GET /estudos/{id}/exportacao.zip` | arquivos do lote restritos ao estudo + `alocacao.csv` + `metricas_estudo.json` (no lugar de `metricas.json`) | participantes `P01…` na ordem do convite, sem e-mail |

**Estudo**: `{id, titulo, status, papel, lote, lote_titulo, rodada, n_participantes, criado_em}`.
