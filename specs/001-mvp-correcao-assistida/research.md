# Research — MVP Correção Assistida por Rubrica

Fase 0 do plano. Cada item: decisão, razão e alternativas. Tudo o que está marcado
"medido" foi executado em 2026-09-18. O que não foi medido está marcado como estimativa.

## R1. Stack

**Decisão**: mesmo stack do projeto Extenda. Backend Python 3.12 + Django 5.2 + DRF +
drf-spectacular + simplejwt (login por e-mail; o allauth do Extenda foi dispensado, ver plan.md). Assíncrono com Celery + Redis. PostgreSQL 16.
Frontend React 18 + TypeScript + Vite 6 + react-router 7. Testes com pytest + pytest-django e
lint com ruff. Tudo em Docker Compose.

**Razão**: diretriz do orientador ("pegue o que estamos usando no extenda"). Há reuso direto de
padrões já validados lá: a factory de LLM com dublê determinístico (`conectores/llm.py`), a
medição de custo por chamada, o módulo de LGPD e o compose com worker. O Django admin serve de
backoffice do pesquisador para inspecionar execuções e decisões sem tela própria.

**Alternativas**: FastAPI + React (padrão do classup), rejeitada porque autenticação, convite
e admin teriam de ser refeitos, sem reuso do Extenda.

## R2. Modelo de linguagem

**Decisão**: Gemini via SDK `google-genai`, modelo padrão `gemini-3.6-flash` (o do Extenda),
configurado por `GEMINI_API_KEY` e `GEMINI_MODEL`. O modelo é parâmetro do lote e fica gravado
em cada execução, o que permite comparar modelos no mesmo lote.

**Disponibilidade (medido)**: a listagem de modelos com a chave do Extenda retorna, entre
outros, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3.5-flash`, `gemini-3.6-flash`,
`gemini-3.7-flash` e `gemini-3.8-flash`.

**Preço** (página oficial, consultada em 2026-09-18, US$ por 1M tokens):

| Modelo | Entrada | Saída (inclui raciocínio) | Observação |
|---|---|---|---|
| gemini-3.6-flash | 0,75 | 3,75 | Dobra a partir de 2027-01-01 (1,50 / 7,50) |
| gemini-3.8-flash | 0,75 | 3,75 | Mesma regra de 2027 |
| gemini-2.5-flash | 0,30 | 2,50 | |
| gemini-2.5-flash-lite | 0,10 | 0,40 | |

Modo batch custa 50% menos, mas é assíncrono (fora do MVP). A tabela de preços fica em
configuração, com data de vigência, porque o estudo pode cruzar a virada de 2027.

**Alternativas**: Claude (Anthropic), rejeitado por diretriz de usar o provedor já contratado.
Modelo local descartado pelo orientador (R14).

## R3. Piloto: variabilidade, sementes e âncoras (medido)

Mesmo enunciado ("verificação vs. validação"), mesmo critério interpretativo
("Exemplificação", 4 níveis) e mesma resposta sintética. Saída estruturada e temperatura
padrão.

| Modelo | Semente | Execuções | Distribuição | Trechos localizados |
|---|---|---|---|---|
| gemini-2.5-flash | nenhuma | 5 | N4 ×5 | 10/10 |
| gemini-3.6-flash | nenhuma | 5 | N3 ×3, N4 ×2 → divergente (0,6) | 10/10 |
| gemini-3.6-flash | fixa (11) | 3 | N4 ×3, saídas idênticas byte a byte | 6/6 |

Consumo por chamada (3.6-flash): entrada 357 tokens, saída visível de 132 a 160 tokens e
raciocínio de 613 a 913 tokens (média de 772). Latência típica de 5 a 8 s. A primeira rajada de
5 chamadas paralelas recebeu `503 UNAVAILABLE` ("high demand"), e uma chamada levou 38 s.

**Conclusões que viram decisão**:

1. **Sementes distintas por execução.** Semente fixa faz o modelo repetir a mesma resposta, o que
   esconde a instabilidade em vez de medi-la. O Extenda usa `seed=7` para extração de dados, e
   aqui isso seria errado. Cada execução usa
   `semente = hash(rodada.semente_base, resposta, critério, índice)`. Isso dá independência
   entre execuções e reprodutibilidade da rodada (auditoria). Reaplicação sorteia nova
   `semente_base`. O Google trata a reprodutibilidade por semente como "melhor esforço", então
   ela é registrada, mas não garantida.
2. **Temperatura no padrão.** Segue a nota do Extenda: para o Gemini 3 o Google recomenda não
   baixar a temperatura. A variação medida é a do modelo como é usado na prática, o mesmo
   cenário do teste preliminar do canvas.
3. **O raciocínio responde pela maior parte dos tokens de saída** e domina o custo. O MVP usa o
   nível de raciocínio padrão do modelo (não é configurável). Torná-lo parâmetro fica como
   variável de pesquisa futura, porque pode afetar a estabilidade.
4. **Resiliência é obrigatória.** Ver R8.

## R4. Saída estruturada

**Decisão**: `response_mime_type="application/json"` + `response_json_schema` (padrão do
Extenda), com esquema montado por critério. `nivel` é enum com os códigos dos níveis daquele
critério mais `SEM_EVIDENCIA`, e `trechos` é uma lista de strings. Contrato em
[contracts/llm-saida.schema.json](contracts/llm-saida.schema.json).

**Razão**: o piloto teve 13/13 respostas com JSON válido. O enum impede nível inexistente.
Mesmo assim, a resposta passa por validação do lado do servidor, e JSON inválido marca a
execução como inválida.

**Prompt**: arquivos versionados em `backend/src/avaliacao/prompts/` (v1 e v2, esta a vigente; ver R7). A
versão é gravada na rodada, e retomar uma rodada usa a versão dela. Uma chamada por par (resposta, critério): o critério
isolado evita efeito halo entre critérios e torna a divergência mensurável critério a critério.

## R5. Verificação de âncora

**Decisão**: a verificação é feita no servidor, nunca delegada ao modelo.

1. Normaliza o texto da resposta e o trecho: NFKC, aspas e hífens tipográficos para ASCII,
   espaços colapsados, casefold. Mantém um mapa posição-normalizada → posição-original.
2. Busca exata do trecho normalizado. Se achar, grava `inicio` e `fim` no texto original
   armazenado (já anonimizado).
3. Tolerâncias só de forma: aspas nas bordas do trecho são ignoradas e, se o trecho não for
   achado, tenta-se de novo sem a pontuação final (`.,;:!?`). Os dois textos são comparados em
   NFC.
4. Trecho vazio, com reticências, com menos de 3 palavras ou não localizado torna a execução
   **inválida**. Basta um trecho não localizado para invalidar a execução: citação inventada
   indica que a justificativa não é confiável.
5. `SEM_EVIDENCIA` exige lista de trechos vazia. O contrário (nível com lista vazia) é inválido.

Não há correspondência aproximada (fuzzy). Paráfrase não é âncora.

## R6. Consolidação

**Decisão**: sobre as execuções **válidas** de um par (resposta, critério) numa rodada:

- `n_validas < min_validas` (padrão 3) → **INDETERMINADO**.
- `acordo = votos do modal / n_validas`. `SEM_EVIDENCIA` conta como categoria de voto.
- `acordo ≥ limiar` (padrão 0,8; precisa ser > 0,5) e modal = nível → **CONVERGENTE**.
- `acordo ≥ limiar` e modal = `SEM_EVIDENCIA` → **SEM_EVIDENCIA**.
- Qualquer outro caso, inclusive empate → **DIVERGENTE**.

O nível modal é sempre guardado, mas só é **exibido** quando convergente. Guardá-lo permite
testar a hipótese SC-008a (concordância maior nos convergentes que nos divergentes). Como todas
as execuções são persistidas, o consolidado pode ser recalculado para outros limiares (0,6 /
0,8 / 1,0) na análise de sensibilidade, sem nova chamada ao modelo.

Justificativa representativa de cada nível: a da primeira execução válida (menor índice)
daquele nível. É determinística.

## R7. Custo e estimativa

**Estimativa antes da execução**:
`chamadas = respostas elegíveis × critérios × N` (vazias e longas não chamam o modelo). Entrada
estimada pelo tamanho real dos prompts montados (caracteres ÷ 4; não se usa `count_tokens`).
Saída estimada por `TOKENS_SAIDA_ESTIMADOS` (1.050, com raciocínio), trocada pela média observada
de entrada e saída quando o lote tem ao menos 10 execuções concluídas.

**Ordem de grandeza** (a partir do V7 medido abaixo, ~US$ 0,0028 por chamada): 40 respostas ×
4 critérios × 5 execuções = 800 chamadas ≈ US$ 2,30 por rodada no preço de 2026 e ≈ US$ 4,60 a
partir de 2027. Respostas mais longas que as da turma fictícia custam mais na entrada. O lote comum do estudo é
pré-avaliado uma vez para todos os participantes. Com reaplicação e os lotes próprios dos
docentes, o custo total do TCC fica na casa das dezenas de dólares.

**Teto**: cada rodada tem `teto_usd`. Antes de cada chamada, o worker soma de forma atômica o
custo previsto ao acumulado. Se o teto for ultrapassado, a rodada vai para `PAUSADA_TETO` e as
execuções restantes ficam `PENDENTE`, retomáveis depois de o teto ser elevado.

**Cache**: a unidade de cache é a rodada. Uma execução `CONCLUIDA` nunca é refeita. Retomar ou
reprocessar a mesma rodada não gera custo novo (FR-011). Reaplicação cria rodada nova (FR-022).

### Medido no quickstart V7 (2026-09-18)

Lote sintético com 10 respostas normais × 4 critérios × N=5 = 200 chamadas ao
`gemini-3.6-flash`, rubrica pública de `docs/modelos/` e concorrência de 8.

| | Rodada 1 (prompt v1, sem teto de saída) | Rodada 2 (prompt v2, teto 8.192, timeout 60 s) |
|---|---|---|
| Execuções válidas | 94,5% (9 `SEM_TRECHO`, 2 `JSON_INVALIDO`) | **100%** |
| Tempo total | 360 s | **126 s** (1,6 chamada/s; 800 chamadas ≈ 8 min) |
| Tokens médios (entrada / saída / raciocínio) | 478 / 734 / 593 | 520 / 89 / 560 |
| Latência mediana / p95 | 4,7 s / 7,7 s | 4,5 s / 6,8 s |
| Custo real ÷ estimado | 1,25 (US$ 1,07 ÷ 0,85) | **0,66** (US$ 0,56 ÷ 0,86) |
| Estados (40 pares) | 36 conv., 2 div., 2 indet. | 34 conv., 4 div., 2 sem evid. |

Diagnóstico da rodada 1, que levou às correções:
- **Geração degenerada**: 2 chamadas repetiram `\u0000` até 65 mil tokens de saída, com 245 s e
  US$ 0,24 cada. Elas explicam a cauda de tempo e todo o excesso de custo. Correção:
  `max_output_tokens=8192` e timeout de 60 s (falha passageira, com nova tentativa).
- **Nível por ausência**: as 9 `SEM_TRECHO` foram N1 justificado pela falta de algo ("não apresenta
  exemplos"), sem trecho a citar. Correção: prompt v2, que manda usar `SEM_EVIDENCIA` nesses casos
  (Princípio II: ausência de conteúdo vai para a docente). A rodada guarda a versão do prompt.

`TOKENS_SAIDA_ESTIMADOS=1050` ficou mantido: sem as gerações degeneradas, a saída real (visível +
raciocínio) é de ~650 tokens, e a estimativa troca para a média observada depois de 10 execuções
do lote.

## R8. Execução assíncrona e resiliência

**Decisão**: uma tarefa Celery por execução (`executar_execucao`). As linhas `Execucao` são
criadas em `PENDENTE` quando a rodada é confirmada e enfileiradas depois do commit. A tarefa é
idempotente: sai se a execução não estiver `PENDENTE`. Configuração:

- Falha passageira (408, 429, 5xx, rede e timeout) devolve a execução a `PENDENTE` e a tarefa
  pede `retry` com espera exponencial e variação aleatória (2 s a 120 s), até
  `LLM_MAX_TENTATIVAS` (6). Depois disso, `FALHOU` com o erro gravado. Falha de chamada não é a
  mesma coisa que execução inválida. Em modo síncrono (testes) a nova tentativa é feita em laço,
  porque o Celery propaga o `Retry` com `task_eager_propagates`.
- Timeout de 60 s por chamada (`LLM_TIMEOUT_S`) e teto de 8.192 tokens de saída
  (`LLM_MAX_TOKENS_SAIDA`). Ver o diagnóstico do V7 em R7.
- `rate_limit` por tarefa (`LLM_RATE_LIMIT`, padrão 120/min) e concorrência do worker
  (`LLM_CONCORRENCIA`, padrão 8).
- Quando a última execução de um par sai da fila (concluída ou falha), o consolidado do par é
  recalculado.
- **Worker que cai**: com `acks_late`, a mensagem reservada volta à fila depois do
  `visibility_timeout` do Redis (10 min, e não o padrão de 1 h). A execução que ficou
  `EM_ANDAMENTO` há mais de 10 min é considerada abandonada: retomar a devolve a `PENDENTE`, e a
  própria tarefa a reprocessa se receber a mensagem de novo.
- Retomar reenfileira `PENDENTE` e `FALHOU` (zerando as tentativas). Mensagem duplicada não gera
  chamada duplicada.

Armadilha herdada do Extenda: o cliente `genai.Client` precisa ficar numa variável local até a
resposta chegar. Encadeado, ele é coletado e fecha a conexão.

Meta de desempenho: 800 chamadas em até 30 min exige ≥ 0,45 chamada/s. **Medido no V7**:
1,6 chamada/s com concorrência 8 (800 chamadas ≈ 8 min). Limites de requisição da conta: não
atingidos nas 200 chamadas do V7.

## R9. Privacidade e LGPD

- **Chave com faturamento é obrigatória para dado real.** Termos da Gemini API (consultados em
  2026-09-18): no nível gratuito, "Google uses the content you submit ... to provide, improve,
  and develop Google products", revisores humanos podem ler, e o texto diz "Do not submit
  sensitive, confidential, or personal information to the Unpaid Services". No pago, "Google
  doesn't use your prompts ... or responses to improve our products". **Decidido pelo
  orientador (2026-09-18): o projeto não usa o nível gratuito.** Como proteção contra uma chave
  errada no `.env` de alguém, o sistema recusa rodada de lote não sintético quando
  `GEMINI_PAID_TIER=true` não está em configuração.
- **Idade**: os termos vedam clientes de API destinados a menores de 18 anos ou com
  probabilidade de acesso por eles. Os usuários do sistema são docentes, então o MVP (ensino
  superior) está coberto. A extensão para a educação básica envolve textos de menores (LGPD
  art. 14) e exige reavaliação antes de uso real.
- **Anonimização na carga**:
  - O upload é lido em memória (`MemoryFileUploadHandler`, limite de 10 MB). O arquivo nunca
    toca o disco.
  - As colunas de identificação mapeadas são descartadas.
  - No texto, os tokens dos nomes do próprio arquivo (sem acento e sem caixa, com limite de
    palavra) são substituídos por `[ESTUDANTE]`. E-mails viram `[EMAIL]`, CPF (com ou sem
    máscara) vira `[CPF]` e sequências de 8 a 14 dígitos viram `[MATRICULA]`.
  - Grava-se só a contagem de substituições, nunca o conteúdo substituído.
- **Chave de reidentificação**: CSV `codigo,identificador`, montado em memória e devolvido na
  resposta da importação, uma única vez. Não é persistido.
- **Logs**: nada de texto de resposta nos logs de aplicação. A resposta bruta do modelo fica só
  na tabela `Execucao` (sem identificador, por construção).

## R10. Métricas

| Métrica | Definição | Implementação |
|---|---|---|
| Concordância exata | % de pares com nível modal = nível decidido | própria |
| Adjacente | % com diferença ≤ 1 posição ordinal | própria |
| Ponderada | κ de Cohen com peso quadrático (QWK) | `sklearn.metrics.cohen_kappa_score(weights="quadratic")` |
| Seletiva | concordância exata nos convergentes vs. divergentes; cobertura = % convergentes | própria |
| Taxa de divergência | % de pares divergentes, por critério e por tipo (objetivo/interpretativo) | própria |
| Estabilidade intra-rodada | acordo médio do modal; κ de Fleiss entre as N execuções | própria / `statsmodels` |
| Estabilidade entre rodadas | concordância exata e QWK entre os modais da rodada 1 e da reaplicação | própria + sklearn |
| Referência humana | α de Krippendorff (ordinal) entre docentes cegos no estudo | `krippendorff` |
| Ancoragem | concordância com assistidos − concordância com cegos | própria |
| Tempo | mediana do tempo ativo por resposta, por condição e por participante | própria |

A referência humana dá o teto interpretável: a IA concorda com os docentes tanto quanto eles
concordam entre si?

Convenções implementadas (`metricas/calculos.py`):
- níveis entram pela posição ordinal (1..k);
- pares cujo modal é `SEM_EVIDENCIA`, ou sem modal, ficam fora das medidas ordinais;
- a concordância do lote usa as decisões vigentes da dona do lote fora de estudo;
- a estabilidade compara o modal da rodada 1 com o da rodada 2;
- o κ de Fleiss usa só pares com exatamente N execuções válidas;
- o tempo por resposta soma o tempo ativo das sessões que tiveram decisão;
- valor indefinido (amostra pequena, variância zero, nenhum item com dois avaliadores) sai como
  `null`, nunca NaN. Toda métrica sai de funções puras sobre as tabelas exportadas. O script
independente `analysis/reproduzir_metricas.py` recalcula as métricas a partir do ZIP de
exportação (SC-006).

## R11. Medição de tempo

**Decisão**: o frontend acumula o tempo ativo desde a abertura da resposta. O cronômetro pausa
com `visibilitychange` (aba oculta) e após 60 s sem teclado ou mouse. Cada decisão envia o
acumulado, e o servidor grava o tempo da sessão como o acumulado na última decisão. Sessão sem
decisão não entra na métrica.

## R12. Protocolo A (estudo)

**Decisão**:

- **Respostas do estudo**: só as elegíveis (sem vazias nem longas), porque as demais não têm
  pré-avaliação a comparar.
- **Metades**: embaralhadas com `semente_alocacao` e divididas em A/B, estratificando por "tem ao
  menos um critério não convergente na rodada do estudo". Cada estrato começa pela metade menor,
  o que dá equilíbrio de ±1 no total e por estrato.
- **Participantes**: alocados em rodízio, na **ordem do convite**, pelas 4 células na sequência
  (1, sem primeiro), (2, com primeiro), (2, sem primeiro), (1, com primeiro). Assim os dois
  primeiros já cobrem os dois braços e as duas ordens, e com 8 participantes cada célula recebe 2.
- **Ordem das respostas**: dentro de cada bloco, embaralhada por participante com semente
  derivada de (`semente_alocacao`, participação). É reproduzível e separa efeito de ordem de
  efeito de condição.
- **Rodada**: a sessão do estudo usa a rodada fixada no estudo, e não a mais recente do lote.
- **Condição sem apoio**: a ocultação é feita **no servidor**. A API não devolve nenhum campo de
  pré-avaliação para uma resposta da metade sem apoio daquele participante (FR-025).

## R13. Hospedagem

**Pendente** (não bloqueia a implementação): o compose é o artefato de implantação. As opções
para o estudo são o beelink com túnel (Cloudflare) ou uma VPS. A decisão fica para antes da
fase de estudo.

## R14. Provedor local

**Decisão (2026-09-18, orientador)**: não usar modelo local. O MVP usa só o Gemini na nuvem, em
nível pago. A interface `LLMProvider` continua permitindo outro provedor no futuro. O MVP entrega
os adaptadores `dumb` e `gemini`. Um adaptador Ollama chegou a ser escrito e foi removido.

**Dublê determinístico** (`dumb`), com dois modos:
- **Roteirizado**, para os testes: cenários por código de resposta (unânime, 4-1, 3-2, 2-2-1,
  trecho inventado, sem evidência, JSON inválido).
- **Pseudoaleatório por semente**, para desenvolvimento.

Em ambos, os trechos são substrings reais da resposta, exceto no cenário "trecho inventado".
