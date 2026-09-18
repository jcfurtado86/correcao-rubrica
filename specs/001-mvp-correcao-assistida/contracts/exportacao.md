# Contrato de exportação (dados de pesquisa)

`GET /lotes/{id}/exportacao.zip` e `GET /estudos/{id}/exportacao.zip`. É a entrada do script
`analysis/reproduzir_metricas.py` (SC-006). CSV UTF-8, separador `,`, decimal `.`, instantes
em ISO-8601 UTC. Nenhum arquivo contém identificador de estudante ou nome de docente.
Docentes aparecem como `D01…`, e no estudo como `P01…`.

| Arquivo | Uma linha por | Colunas |
|---|---|---|
| `metadados.json` | — | lote, rubrica (versão e hash, critérios e níveis com ordem e pontuação), parâmetros (N, limiar, min_validas), rodadas (número, modelo, versão do prompt, semente_base, custos), versão do sistema, data da exportação |
| `respostas.csv` | resposta | `codigo, n_caracteres, n_substituicoes, aviso, metade` (texto só com `?incluir_texto=1`) |
| `execucoes.csv` | execução | `rodada, codigo, criterio, indice, semente, status, valida, motivo_invalidez, nivel_codigo, nivel_ordem, n_trechos, n_trechos_localizados, tokens_entrada, tokens_saida, tokens_raciocinio, custo_usd, latencia_ms, tentativas` |
| `consolidados.csv` | rodada × resposta × critério | `rodada, codigo, criterio, estado, modal_codigo, nivel_modal_ordem, acordo, n_validas, distribuicao_json, limiar_usado` |
| `decisoes.csv` | decisão (vigentes e substituídas) | `decisao_id, docente, dono_do_lote, participante, codigo, criterio, condicao, estado_exibido, nivel_sugerido_ordem, nivel_decidido_ordem, tipo, tem_motivo, tempo_ativo_ms, vigente, substitui, instante` |
| `sessoes.csv` | sessão | `sessao_id, docente, dono_do_lote, participante, codigo, condicao, rodada, tempo_ativo_ms, n_decisoes, aberta_em` |
| `alocacao.csv` | só estudo: participante | `participante, braco, ordem` (a metade de cada resposta está em `respostas.csv`) |
| `metricas_estudo.json` | só estudo | o painel do estudo sem e-mails; no lugar de `metricas.json` |
| `metricas.json` | — | `{limiar, por_rodada: {"1": painel, "2": painel}}`: os mesmos números do painel, para conferência automática com o script |

Convenções: `criterio` é a posição do critério na rubrica (1..k) e os níveis entram pela
posição ordinal. Booleanos são `1`/`0` e ausência é campo vazio. `dono_do_lote = 1` e
`participante` vazio identificam as decisões e sessões da docente dona do lote fora de estudo,
que são a base da concordância do painel do lote. O tempo por resposta é a soma do tempo ativo
das sessões com ao menos uma decisão.

`motivo` (texto livre da decisão) só sai com `?incluir_motivos=1`, porque pode conter
comentário sobre a resposta.
