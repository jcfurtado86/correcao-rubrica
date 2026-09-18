# Data Model — MVP Correção Assistida por Rubrica

Entidades da [spec](spec.md#key-entities), já com campos, relações, regras e transições de
estado. Os nomes seguem o português do domínio, como no Extenda. Toda tabela tem `id`, e as que
registram eventos têm `criado_em` (todas, exceto `Criterio`, `Nivel`, `Trecho` e
`AlocacaoResposta`); esses dois campos ficam omitidos abaixo. Conferido contra os modelos em
2026-09-18.

```
Usuario ─┬─< Rubrica ─< VersaoRubrica ─< Criterio ─< Nivel
         │                   │
         ├─< Lote >──────────┘ (versão congelada)
         │    ├─< Resposta
         │    └─< Rodada ─< Execucao ─< Trecho
         │          └─< Consolidado (rodada × resposta × critério)
         ├─< SessaoCorrecao ─< Decisao
         └─< Estudo ─< Participacao
                  └─< AlocacaoResposta (metade A/B)
```

## core

### Usuario
Estende `AbstractUser`, sem username, com login por e-mail (JWT via simplejwt).

| Campo | Tipo | Regra |
|---|---|---|
| email | e-mail, único | identificador de acesso |
| nome | texto | |
| papel | `DOCENTE` \| `PESQUISADOR` | padrão `DOCENTE` |

## rubricas

### Rubrica
| Campo | Tipo | Regra |
|---|---|---|
| dono | FK Usuario | só o dono vê e edita (FR-027) |
| titulo, descricao | texto | |

### VersaoRubrica
| Campo | Tipo | Regra |
|---|---|---|
| rubrica | FK Rubrica | |
| numero | int | único por rubrica, sequencial |
| congelada | bool | vira `true` quando a primeira rodada de um lote que a usa é confirmada (FR-002) |
| hash | sha256 | JSON canônico de critérios e níveis, gravado ao congelar |

Regra: versão congelada não aceita alteração nem em si nem em seus critérios e níveis. Editar
uma rubrica cuja versão vigente está congelada cria `numero + 1` como cópia editável.

### Criterio
| Campo | Tipo | Regra |
|---|---|---|
| versao | FK VersaoRubrica | |
| ordem | int | contígua a partir de 1 |
| nome, descricao | texto | |
| peso | decimal ≥ 0 | padrão 1 |
| tipo | `OBJETIVO` \| `INTERPRETATIVO` | usado para análise de divergência por tipo |

Regra: versão sem critério não pode ser usada em lote.

### Nivel
| Campo | Tipo | Regra |
|---|---|---|
| criterio | FK Criterio | ≥ 2 por critério |
| ordem | int | posição ordinal, contígua a partir de 1, base das métricas adjacente e ponderada |
| codigo | texto | `N1`…`Nk`, gerado da ordem, é o valor do enum na saída do modelo |
| rotulo, descritor | texto | |
| pontuacao | decimal | |

## lotes

### Lote
| Campo | Tipo | Regra |
|---|---|---|
| dono | FK Usuario | |
| titulo, enunciado | texto | enunciado obrigatório |
| versao_rubrica | FK VersaoRubrica (PROTECT) | |
| n_execucoes | int 1–10 | padrão 5 |
| limiar_acordo | decimal (0,5; 1,0] | padrão 0,8 |
| min_validas | int ≥ 1, ≤ n_execucoes | padrão 3 |
| provedor_llm, modelo_llm | texto | `dumb`/`dublê` ou `gemini`/`gemini-…`. Escolhidos na criação entre os do catálogo do servidor (`GET /modelos/`); padrão de `LLM_PROVIDER` / `GEMINI_MODEL` |
| teto_usd | decimal | padrão de configuração |
| sintetico | bool | lote de teste, permitido fora do nível pago (R9) |

Os parâmetros ficam congelados quando a primeira rodada é confirmada.

### Resposta
| Campo | Tipo | Regra |
|---|---|---|
| lote | FK Lote | |
| codigo | texto | `R001`…, único por lote, sem relação com a ordem ou o identificador originais |
| texto | texto | **já anonimizado**, imutável depois da carga |
| hash_texto | sha256 | |
| n_substituicoes | int | quantas marcações de anonimização foram aplicadas (nunca o conteúdo) |
| aviso | `VAZIA` \| `LONGA` \| nulo | FR-007. Limite padrão de 15.000 caracteres, e resposta longa não é truncada: fica fora da avaliação até decisão da docente |

Nenhum campo guarda nome, e-mail, matrícula ou linha original da planilha.

## avaliacao

### Rodada
| Campo | Tipo | Regra |
|---|---|---|
| lote | FK Lote | |
| numero | int | 1 = original, ≥ 2 = reaplicação |
| semente_base | int | sorteada na criação, e nova em cada reaplicação |
| versao_prompt | texto | versão vigente na criação (hoje `avaliar_criterio_v2`); retomar a rodada usa a dela |
| provedor, modelo | texto | copiados do lote |
| custo_estimado_usd, custo_acumulado_usd, teto_usd | decimal | acumulado com atualização atômica |
| custo_previsto_chamada_usd | decimal | estimado ÷ chamadas: valor reservado antes de cada chamada (teto) |
| confirmada_por | FK Usuario | quem aprovou o custo |
| status | ver abaixo | |
| concluida_em | instante, nulo | |

A rodada nasce `EM_EXECUCAO` na confirmação (a estimativa não é gravada como rodada). `ESTIMADA`
existe no modelo, mas não é usada.

```
(confirmar) ──► EM_EXECUCAO ──tudo concluído──► CONCLUIDA
                           │   ▲                 └─falhas restantes─► COM_FALHAS ──retomar──┐
                           │   └──────────retomar (teto elevado)────────────────────────────┤
                           └──teto atingido──► PAUSADA_TETO                                 │
                               EM_EXECUCAO ◄─────────────────────────────────────────────────┘
```

### Execucao
Uma avaliação de um par (resposta, critério) numa rodada. Única por
`(rodada, resposta, criterio, indice)`.

| Campo | Tipo | Regra |
|---|---|---|
| rodada, resposta, criterio | FK | |
| indice | int 1..N | |
| semente | int | `hash(semente_base, resposta, criterio, indice)` (R3) |
| status | `PENDENTE` → `EM_ANDAMENTO` → `CONCLUIDA` \| `FALHOU` | `FALHOU` = chamada não completou após os retries |
| valida | bool, nulo até concluir | |
| motivo_invalidez | `JSON_INVALIDO` \| `NIVEL_FORA` \| `SEM_TRECHO` \| `TRECHO_NAO_LOCALIZADO` \| `TRECHO_CURTO` \| `INCOERENTE_SEM_EVIDENCIA` | nulo se válida |
| nivel_codigo | texto | `N1`…`Nk` ou `SEM_EVIDENCIA` |
| nivel | FK Nivel, nulo | resolvido de `nivel_codigo` |
| justificativa | texto | |
| resposta_bruta | texto | JSON devolvido pelo modelo, para auditoria |
| tokens_entrada, tokens_saida, tokens_raciocinio | int | de `usage_metadata` |
| custo_usd, latencia_ms, tentativas | | |
| erro | texto, nulo | última falha de chamada |
| iniciada_em, concluida_em | instante, nulo | `iniciada_em` marca a entrada em `EM_ANDAMENTO`. Execução parada nesse estado há mais de `EXECUCAO_ABANDONADA_APOS_S` (10 min) é considerada abandonada (worker caiu) e volta para `PENDENTE` ao retomar |

### Trecho
| Campo | Tipo | Regra |
|---|---|---|
| execucao | FK Execucao | |
| texto_citado | texto | como veio do modelo |
| localizado | bool | R5 |
| inicio, fim | int, nulo | posições no `Resposta.texto` |

### Consolidado
Derivado das execuções válidas. Único por `(rodada, resposta, criterio)` e recalculável a
qualquer momento (R6).

| Campo | Tipo | Regra |
|---|---|---|
| estado | `CONVERGENTE` \| `DIVERGENTE` \| `SEM_EVIDENCIA` \| `INDETERMINADO` | |
| modal_codigo | texto | código modal (inclui `SEM_EVIDENCIA`); vazio sem votos. Em empate, o nível que apareceu primeiro |
| nivel_modal | FK Nivel, nulo | nível do modal (nulo se `SEM_EVIDENCIA`), exibido só se `CONVERGENTE` |
| acordo | decimal | votos do modal / válidas |
| n_validas | int | |
| distribuicao | JSON `{codigo: votos}` | |
| limiar_usado, min_validas_usado | | cópia dos parâmetros no cálculo |
| calculado_em | instante | |

Consolidado só existe para par cujas execuções saíram todas da fila. Par sem consolidado
(resposta longa, rodada em curso) é exibido como `INDISPONIVEL`.

Prioridade na fila (FR-016): `INDETERMINADO`, `DIVERGENTE`, `SEM_EVIDENCIA` e `INDISPONIVEL` antes
de `CONVERGENTE`, depois por código. A resposta herda o pior estado entre seus critérios.

## revisao

### SessaoCorrecao
Uma abertura de uma resposta por uma docente.

| Campo | Tipo | Regra |
|---|---|---|
| docente, resposta | FK | |
| participacao | FK Participacao, nulo | preenchido quando a correção faz parte de um estudo |
| condicao | `COM_APOIO` \| `SEM_APOIO` | fora de estudo é sempre `COM_APOIO`; no estudo, imposta pela alocação |
| rodada | FK Rodada, nulo | rodada cujas sugestões foram exibidas (a de referência do lote, ou a fixada no estudo); nula em `SEM_APOIO` |
| aberta_em | instante | |
| tempo_ativo_ms | int | acumulado na **última decisão**: é a métrica (R11). Sessão sem decisão fica com 0 e não entra na conta |
| tempo_total_ms | int | último valor da batida periódica (a cada 30 s). Diagnóstico, não é métrica |

### Decisao
| Campo | Tipo | Regra |
|---|---|---|
| sessao | FK SessaoCorrecao | a condição vem da sessão |
| resposta, docente, participacao | FK (participacao nula fora de estudo) | copiados da sessão para a restrição de vigência |
| criterio | FK Criterio | deve pertencer à versão da rubrica do lote |
| nivel | FK Nivel | valor decidido, deve pertencer ao critério |
| estado_exibido | `CONVERGENTE` \| `DIVERGENTE` \| `SEM_EVIDENCIA` \| `INDETERMINADO` \| `INDISPONIVEL` \| `OCULTO` | foto do que a docente viu |
| nivel_sugerido | FK Nivel, nulo | foto da sugestão exibida (só se convergente) |
| tipo | `CONFIRMACAO` \| `ALTERACAO` \| `ESCOLHA` \| `CEGA` | derivado: igual à sugestão / diferente / sem sugestão exibida / condição sem apoio |
| motivo | texto, opcional | |
| tempo_ativo_ms | int | acumulado da sessão no momento da decisão |
| substitui | FK Decisao, nulo | histórico (FR-017, cenário 3) |
| vigente | bool | exatamente uma vigente por (resposta, critério, docente, participacao): restrição única parcial com `nulls_distinct=False`, para valer também fora de estudo |
| criado_em | instante | |

Resposta **finalizada** = todos os critérios da versão com decisão vigente daquela docente. Só
respostas finalizadas entram na exportação de notas (FR-019).
Nota da resposta = Σ (pontuação do nível decidido × peso do critério).

Não existe endpoint de decisão em lote (FR-018). Cada decisão referencia uma sessão aberta
daquela resposta.

## estudos

### Estudo
| Campo | Tipo | Regra |
|---|---|---|
| pesquisador | FK Usuario (papel PESQUISADOR) | |
| titulo | texto | |
| lote, rodada | FK | rodada cujas sugestões serão exibidas, precisa estar `CONCLUIDA` |
| semente_alocacao | int | |
| status | `PREPARACAO` → `EM_ANDAMENTO` → `ENCERRADO` | alocação das metades feita ao iniciar |
| iniciado_em | instante, nulo | |

Regras de criação: só PESQUISADOR, o lote precisa ser dele e a rodada precisa estar
`CONCLUIDA`. Só respostas elegíveis (sem aviso: nem vazias, nem longas) entram no estudo.

### AlocacaoResposta
Única por `(estudo, resposta)`. `metade`: `A` \| `B`, estratificada por "a resposta tem ao menos
um critério não convergente na rodada do estudo" (R12). Equilíbrio de ±1 no total e por estrato.

### Participacao
| Campo | Tipo | Regra |
|---|---|---|
| estudo, docente | FK | única por par |
| posicao | int | ordem do convite, única por estudo |
| braco | `1` (A sem apoio, B com apoio) \| `2` (A com apoio, B sem apoio), nulo até iniciar | rodízio pela posição |
| ordem | `SEM_PRIMEIRO` \| `COM_PRIMEIRO`, vazio até iniciar | rodízio pela posição |
| concluida_em | instante, nulo | |

Condição de uma resposta para um participante = função de (`metade`, `braco`). O servidor usa
essa função para decidir se a pré-avaliação é devolvida (FR-025).
