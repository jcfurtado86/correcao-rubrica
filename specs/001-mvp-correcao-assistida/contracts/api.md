# Contrato da API REST

Base `/api/`, JSON, autenticação como no Extenda (allauth headless + JWT). O OpenAPI completo é
gerado pelo drf-spectacular em `/api/schema/`. Este arquivo fixa o comportamento que os testes
de contrato verificam. Erros seguem `{"detail": "...", "codigo": "..."}`.

Permissões (FR-026/027): a docente só acessa os próprios recursos. Participante de estudo acessa
apenas as respostas do lote do estudo, pela rota de estudo. O pesquisador acessa estudos que
criou.

## Rubricas

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `GET /rubricas/` | lista `{id, titulo, versao_vigente}` | |
| `POST /rubricas/` | `{titulo, descricao, criterios:[{nome, descricao, peso, tipo, niveis:[{rotulo, pontuacao, descritor}]}]}` → rubrica com versão 1 | ≥ 1 critério, ≥ 2 níveis. `ordem` e `codigo` são derivados da posição |
| `GET /rubricas/{id}/` | rubrica + versão vigente completa | |
| `PUT /rubricas/{id}/` | mesmo corpo do POST | se a vigente está congelada, cria nova versão e responde `201` com `versao` nova |
| `GET /rubricas/{id}/modelo/` | arquivo JSON do modelo (sem dono nem lotes) | P3 |
| `POST /rubricas/importar-modelo/` | multipart `arquivo` → rubrica nova | P3 |

## Lotes e importação

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `POST /lotes/` | `{titulo, enunciado, versao_rubrica, n_execucoes?, limiar_acordo?, min_validas?, modelo_llm?, teto_usd?, sintetico?}` | validações do [data-model](../data-model.md#lote) |
| `POST /lotes/{id}/importacao/previa/` | multipart `arquivo` → `{colunas:[...], amostra:[[...]×5], total_linhas}` | nada é gravado. A amostra só volta para quem enviou o arquivo |
| `POST /lotes/{id}/importacao/` | multipart `arquivo` + `{coluna_resposta, colunas_identificacao:[...], gerar_chave: bool}` → `{n_respostas, avisos:[{codigo, tipo}], chave_reidentificacao: {nome_arquivo, conteudo_base64} \| null}` | regras em [importacao.md](importacao.md). Só é aceita uma vez por lote |
| `GET /lotes/{id}/` | lote + contagens por estado | |
| `GET /lotes/{id}/respostas/` | `[{codigo, n_caracteres, aviso, estado_pior, finalizada}]` | sem texto na listagem |

## Rodadas

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `POST /lotes/{id}/rodadas/estimativa/` | `{reaplicacao: bool}` → `{n_chamadas, tokens_entrada_est, tokens_saida_est, custo_estimado_usd, teto_usd, preco_vigente}` | não chama o modelo, exceto `count_tokens` na amostra (R7) |
| `POST /lotes/{id}/rodadas/` | `{reaplicacao: bool, confirmar: true, teto_usd?}` → rodada `EM_EXECUCAO` | recusa se `confirmar` faltar. Recusa com `codigo: "nivel_gratuito"` se o lote não for sintético e `GEMINI_PAID_TIER` não for verdadeiro. Recusa reaplicação sem rodada 1 concluída |
| `GET /rodadas/{id}/` | `{status, pendentes, concluidas, invalidas, falhas, custo_acumulado_usd, teto_usd}` | o frontend consulta a cada 3 s |
| `POST /rodadas/{id}/retomar/` | `{teto_usd?}` | reenfileira `PENDENTE` e `FALHOU` |
| `GET /respostas/{id}/execucoes/?rodada=` | `{codigo, texto, criterios:[{criterio, execucoes:[{indice, status, valida, motivo_invalidez, nivel_codigo, justificativa, trechos:[{texto_citado, localizado, inicio, fim}]}]}]}` | inspeção das execuções brutas, só para o dono do lote ou o pesquisador. **Nunca** usada no fluxo do participante de estudo. Sem `rodada`, usa a mais recente |

## Revisão

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `GET /lotes/{id}/fila/` | `[{resposta, codigo, estado_pior, n_decididos, n_criterios}]` | ordem do FR-016, depois por código |
| `POST /respostas/{id}/sessoes/` | → `{sessao, texto, condicao, criterios:[Sugestao], decisoes_vigentes:[...]}` | abre uma sessão |
| `POST /sessoes/{id}/decisoes/` | `{criterio, nivel, motivo?, tempo_ativo_ms}` → decisão | uma por chamada. Substitui a vigente anterior (histórico) |
| `PATCH /sessoes/{id}/` | `{tempo_ativo_ms}` | batida periódica. Sessão sem decisão não entra na métrica |
| `GET /respostas/{id}/historico/` | decisões, inclusive as substituídas | |
| `GET /lotes/{id}/notas.csv` | `codigo, <critério…>, nota_total` | só respostas finalizadas (FR-019) |

### Sugestao (por critério)

```jsonc
// COM_APOIO, convergente
{ "criterio": 12, "estado": "CONVERGENTE", "nivel_sugerido": {"id": 40, "codigo": "N3", "rotulo": "Parcial"},
  "acordo": {"votos": 5, "validas": 5}, "justificativa": "…",
  "trechos": [{"inicio": 130, "fim": 211, "texto": "…"}] }

// COM_APOIO, divergente: sem nivel_sugerido, uma alternativa por nível votado
{ "criterio": 12, "estado": "DIVERGENTE", "nivel_sugerido": null, "acordo": {"votos": 3, "validas": 5},
  "alternativas": [{"nivel": {"codigo": "N3"}, "votos": 3, "justificativa": "…", "trechos": [...]},
                   {"nivel": {"codigo": "N4"}, "votos": 2, "justificativa": "…", "trechos": [...]}] }

// COM_APOIO, SEM_EVIDENCIA / INDETERMINADO: sem nivel_sugerido, com justificativa quando houver

// SEM_APOIO (estudo): nenhum outro campo sai do servidor
{ "criterio": 12, "estado": "OCULTO" }
```

## Painel e exportação

| Método e rota | Resposta | Regras |
|---|---|---|
| `GET /lotes/{id}/painel/?rodada=&limiar=` | métricas do [R10](../research.md#r10-métricas) por critério e no total | `limiar` recalcula os estados só para exibir, sem gravar (sensibilidade) |
| `GET /lotes/{id}/exportacao.zip` | ver [exportacao.md](exportacao.md) | |

## Estudos

| Método e rota | Corpo / resposta | Regras |
|---|---|---|
| `POST /estudos/` | `{titulo, lote, rodada}` | só PESQUISADOR. A rodada precisa estar `CONCLUIDA` |
| `POST /estudos/{id}/convites/` | `{emails:[...]}` | cria conta por convite (allauth) |
| `POST /estudos/{id}/iniciar/` | → `{metade_A: n, metade_B: n, participantes:[{docente, braco, ordem}]}` | aloca metades e braços (R12). Depois disso não entram novos participantes |
| `GET /estudos/{id}/minha-tarefa/` | `{bloco_atual: {metade, condicao}, proxima_resposta, progresso}` | para o participante |
| `POST /estudos/{id}/respostas/{rid}/sessoes/` | igual à sessão normal, com `condicao` imposta pela alocação | aplica `OCULTO` no servidor |
| `GET /estudos/{id}/painel/` | métricas do lote + referência humana, ancoragem e tempo por condição | |
| `GET /estudos/{id}/exportacao.zip` | idem, com `participante` pseudônimo (`P01`…) | |
