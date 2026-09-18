# Feature Specification: MVP — Correção Assistida por Rubrica com Aferição de Consistência

**Feature Branch**: `001-mvp-correcao-assistida`

**Created**: 2026-09-18

**Status**: Implementado (MVP, 2026-09-18). Validação em [quickstart.md](quickstart.md)

**Input**: User description: "MVP funcional para teste do produto descrito no Canvas de Projeto
'Correção Assistida por Rubrica com Aferição de Consistência Avaliativa' (Glauco Silva Sousa,
orientação Júlio Furtado): o docente define a rubrica, o sistema pré-avalia cada resposta
critério por critério, apresenta justificativa ancorada no trecho que a sustenta, declara a
divergência quando execuções repetidas não convergem e encaminha o caso à decisão docente;
avaliação por concordância com o docente, estabilidade em reaplicação e tempo com/sem apoio."

## Clarifications

### Session 2026-09-18

- Q: Protocolo de medição da concordância e do tempo no estudo com docentes? → A: metades
  contrabalançadas (opção A). Cada docente corrige metade do lote sem apoio e metade com apoio,
  com braços e ordem balanceados entre participantes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pré-avaliação ancorada de um lote (Priority: P1)

A docente cadastra uma rubrica para uma questão discursiva (critérios, níveis de desempenho e
descritores), informa o enunciado, importa a planilha de respostas da turma e dispara a
pré-avaliação. Antes de executar, vê a estimativa de custo. Ao final, abre cada resposta e vê,
para cada critério, o nível sugerido, a justificativa e o trecho do texto do estudante que a
sustenta, destacado no próprio texto. Nenhum nome, e-mail ou matrícula de estudante aparece em
parte alguma: as respostas são identificadas por código.

**Why this priority**: é a fatia mínima que entrega valor e sobre a qual todo o resto se apoia.
Já inclui a anonimização, porque sem ela não se pode carregar lote real.

**Independent Test**: com um lote de teste de 10 respostas contendo identificadores plantados
(nomes, e-mails, matrículas, inclusive dentro do texto), criar rubrica, importar, pré-avaliar e
verificar que (a) toda sugestão exibida tem trecho destacado que existe no texto e (b) nenhum
identificador plantado é encontrado no armazenamento ou nos registros de chamada ao modelo.

**Acceptance Scenarios**:

1. **Given** uma rubrica com 4 critérios de 4 níveis, **When** a docente importa uma planilha e
   indica qual coluna contém a resposta e quais contêm identificadores, **Then** o lote é criado
   com códigos pseudônimos, e as colunas de identificação não são armazenadas.
2. **Given** um lote importado, **When** a docente solicita a pré-avaliação, **Then** o sistema
   exibe número de avaliações previstas e custo estimado, e só executa após confirmação.
3. **Given** uma pré-avaliação concluída, **When** a docente abre uma resposta, **Then** cada
   critério mostra nível sugerido, justificativa e trecho(s) destacados no texto.
4. **Given** uma execução em que o trecho citado não existe no texto do estudante, **When** o
   sistema a processa, **Then** a execução é descartada como inválida e não contribui para o
   nível sugerido.

---

### User Story 2 - Declaração de incerteza (Priority: P1)

Cada critério de cada resposta é avaliado várias vezes de forma independente. Quando as
execuções concordam, a docente vê um único nível sugerido com o grau de acordo (ex.: 5 de 5).
Quando não concordam, a docente vê "Divergente": a distribuição dos níveis (ex.: 3× Nível 2,
2× Nível 3) e a justificativa com o trecho de cada alternativa, sem valor único sugerido.
A fila de correção apresenta primeiro os casos divergentes e os "sem evidência".

**Why this priority**: é a contribuição central do trabalho. Sem ela, o produto é só mais um
atribuidor de nota.

**Independent Test**: com provedor de avaliação simulado que devolve níveis controlados
(unânime, 4-1, 3-2, 2-2-1, todas inválidas), verificar a classificação de cada caso e a ordem
da fila.

**Acceptance Scenarios**:

1. **Given** 5 execuções válidas com 5 votos no Nível 3, **When** o resultado é consolidado,
   **Then** aparece "Convergente — Nível 3 (5/5)".
2. **Given** 5 execuções válidas com 3 votos no Nível 2 e 2 no Nível 3, e limiar de 0,8,
   **When** o resultado é consolidado, **Then** aparece "Divergente" com a distribuição e as
   justificativas das duas alternativas, sem nível sugerido.
3. **Given** execuções que indicam ausência de conteúdo para o critério, **When** o resultado
   é consolidado, **Then** aparece "Sem evidência", encaminhado à docente, sem nível atribuído.
4. **Given** um lote com casos convergentes e divergentes, **When** a docente abre a fila,
   **Then** divergentes e "sem evidência" vêm antes dos convergentes.

---

### User Story 3 - Decisão docente registrada (Priority: P1)

Para cada critério de cada resposta, a docente confirma o nível sugerido ou escolhe outro,
podendo registrar o motivo. Nos casos divergentes ou sem evidência, escolhe o nível. Só depois
de todos os critérios de uma resposta estarem decididos a nota daquela resposta é considerada
final, e só respostas finalizadas entram na exportação de notas.

**Why this priority**: sem decisão registrada não há produto utilizável (Princípio I) nem
dado para medir concordância.

**Independent Test**: decidir parte de um lote e verificar que a exportação só contém
respostas com todos os critérios decididos, e que o histórico mostra cada decisão com valor
sugerido, valor decidido, autor e instante.

**Acceptance Scenarios**:

1. **Given** um critério convergente, **When** a docente confirma, **Then** a decisão é
   registrada com valor sugerido igual ao decidido e o tempo gasto na resposta.
2. **Given** um critério convergente, **When** a docente escolhe outro nível, **Then** a
   decisão é registrada como alteração, com valor sugerido, valor decidido e motivo opcional.
3. **Given** uma decisão já registrada, **When** a docente a muda, **Then** a nova decisão
   passa a valer e a anterior permanece no histórico.
4. **Given** um lote com respostas parcialmente decididas, **When** a docente exporta notas,
   **Then** somente respostas com todos os critérios decididos são exportadas, identificadas
   pelo código pseudônimo.

---

### User Story 4 - Painel de consistência e relatório (Priority: P2)

A docente (ou o pesquisador) abre o painel do lote e vê, por critério: concordância entre
pré-avaliação e decisão docente (exata, adjacente e ponderada pela distância entre níveis),
taxa de divergência sinalizada, concordância separada para itens convergentes e divergentes,
estabilidade do julgamento quando o mesmo lote é reaplicado, tempo de correção e distribuição
de desempenho da turma. Pode solicitar uma reaplicação do lote e exportar todos os dados
brutos em planilha para análise estatística.

**Why this priority**: produz as evidências para o TCC e para o artigo, mas depende de P1.

**Independent Test**: com lote pré-avaliado, reaplicado e decidido a partir de dados
simulados conhecidos, conferir que as métricas exibidas batem com o cálculo de referência feito
sobre a exportação.

**Acceptance Scenarios**:

1. **Given** um lote com decisões docentes, **When** o painel é aberto, **Then** exibe, por
   critério, concordância exata, adjacente e ponderada, e a taxa de divergência.
2. **Given** um lote já pré-avaliado, **When** a docente solicita reaplicação, **Then** o
   sistema executa uma nova rodada independente (sem reaproveitar resultados anteriores),
   informando o custo antes, e o painel passa a exibir a estabilidade entre as rodadas.
3. **Given** um lote qualquer, **When** o pesquisador exporta dados, **Then** obtém planilhas
   com execuções, consolidados, decisões e tempos, sem identificador de estudante.

---

### User Story 5 - Protocolo de avaliação assistida com docentes (Priority: P2)

O pesquisador prepara um estudo com um lote comum e convida de 8 a 12 docentes. O lote é
dividido em duas metades, A e B. Metade dos participantes corrige A sem apoio (sem ver a
pré-avaliação) e B com apoio; a outra metade faz o inverso. A ordem das condições também é
alternada entre participantes. Assim, cada resposta recebe decisões cegas de um grupo e
decisões assistidas do outro. O sistema mede o tempo por resposta em cada condição e registra
as decisões, o que permite calcular: concordância da pré-avaliação com decisões cegas (sem viés
de ancoragem), concordância com decisões assistidas, a diferença entre as duas (efeito de
ancoragem) e o tempo com e sem apoio.

**Why this priority**: é a entrega extensionista de avaliação assistida e a fonte da métrica
de tempo com e sem apoio.

**Independent Test**: criar um estudo com 2 participantes fictícios, executar o roteiro e
conferir a atribuição das condições, a ocultação da pré-avaliação na condição sem apoio e a
exportação dos tempos por condição.

**Acceptance Scenarios**:

1. **Given** um estudo com 8 participantes, **When** o pesquisador o inicia, **Then** 4 recebem
   "A sem apoio / B com apoio" e 4 recebem o inverso, com a ordem das condições alternada.
2. **Given** um estudo com lote comum, **When** um participante inicia a condição sem apoio,
   **Then** nenhuma informação da pré-avaliação (nível, justificativa, destaque, divergência)
   fica visível.
3. **Given** participantes em ordem contrabalançada, **When** o estudo termina, **Then** a
   exportação mostra, por participante e resposta, a condição, o tempo e as decisões.
4. **Given** um estudo, **When** vários docentes corrigem o mesmo lote, **Then** a
   pré-avaliação é calculada uma única vez e compartilhada entre todos.

---

### User Story 6 - Modelo de rubrica reutilizável (Priority: P3)

A docente exporta uma rubrica como modelo e outra docente, de outra instituição ou escola,
importa esse modelo e o adapta.

**Why this priority**: apoia a entrega em repositório público e a oficina, mas não é
necessária ao teste do mecanismo central.

**Independent Test**: exportar uma rubrica, importá-la em outra conta e verificar que
critérios, níveis e descritores foram preservados.

**Acceptance Scenarios**:

1. **Given** uma rubrica, **When** a docente a exporta, **Then** obtém arquivo com critérios,
   níveis e descritores, sem dado de lote ou de estudante.
2. **Given** um arquivo de modelo, **When** outra docente o importa, **Then** uma rubrica nova
   e editável é criada na conta dela.

### Edge Cases

- Resposta vazia ou que não trata do critério: resultado "sem evidência", encaminhado à docente.
- Trecho citado com diferença só de espaços, quebras de linha, aspas ou hífens tipográficos:
  deve ser localizado. Paráfrase que não existe no texto: execução inválida.
- Todas as execuções de um critério inválidas: resultado "indeterminado", encaminhado à docente.
- Empate entre níveis (ex.: 2-2-1): divergente.
- Resposta acima do tamanho máximo suportado: a docente é avisada na carga. O texto nunca é
  truncado em silêncio.
- Nome, e-mail ou matrícula do estudante escritos dentro da própria resposta: substituídos por
  marcador na carga.
- Planilha com colunas em ordem ou nomes inesperados (ex.: exportação do ambiente virtual):
  a docente mapeia as colunas manualmente.
- Linhas duplicadas ou respostas idênticas de estudantes diferentes: tratadas como respostas
  distintas.
- Falha do serviço de avaliação, limite de requisições ou teto de custo atingido no meio do
  lote: o processamento para, o que foi feito é preservado, os itens pendentes ficam visíveis e
  a execução pode ser retomada sem refazer o que já terminou.
- Rubrica editada depois da pré-avaliação: gera nova versão, e a pré-avaliação existente
  continua ligada à versão com que foi feita.
- Docente fecha a tela no meio de uma resposta: o tempo parcial não é contado como decisão.

## Requirements *(mandatory)*

### Functional Requirements

**Rubrica**

- **FR-001**: Docentes MUST poder criar, editar e versionar rubricas com critérios (nome,
  descrição, peso, tipo objetivo ou interpretativo) e níveis de desempenho ordenados (rótulo,
  pontuação e descritor), com no mínimo 2 níveis por critério.
- **FR-002**: Uma rubrica associada a um lote pré-avaliado MUST ficar imutável. Editar gera
  nova versão.
- **FR-003**: Docentes MUST poder exportar e importar rubricas como modelo reutilizável (P3).

**Lote e anonimização**

- **FR-004**: Docentes MUST poder criar um lote com enunciado da questão, rubrica e respostas
  importadas de planilha (CSV ou XLSX), mapeando a coluna de resposta e as de identificação.
- **FR-005**: Na carga, o sistema MUST substituir identificadores por código pseudônimo,
  descartar as colunas de identificação e remover do corpo das respostas os identificadores
  conhecidos do próprio arquivo, e-mails e números com formato de matrícula ou CPF.
- **FR-006**: O sistema MUST oferecer à docente, apenas no momento da carga, o download
  opcional de uma chave código↔identificador, que não é guardada pelo sistema.
- **FR-007**: O sistema MUST avisar sobre respostas vazias e acima do tamanho suportado na
  carga, e nunca truncar texto em silêncio.

**Pré-avaliação e ancoragem**

- **FR-008**: O sistema MUST avaliar cada par (resposta, critério) separadamente, retornando
  nível, justificativa e um ou mais trechos de apoio, ou a indicação "sem evidência".
- **FR-009**: O sistema MUST localizar cada trecho no texto original (tolerando apenas
  diferenças de espaço e pontuação tipográfica) e registrar sua posição. Execução com trecho
  não localizado MUST ser marcada inválida.
- **FR-010**: O sistema MUST exibir estimativa de chamadas e de custo antes de executar e
  exigir confirmação; MUST respeitar um teto de custo por lote.
- **FR-011**: O processamento MUST ser retomável e não repetir chamadas já concluídas;
  reprocessar o mesmo lote sem alteração MUST NOT gerar custo novo, exceto na reaplicação.
- **FR-012**: O sistema MUST permitir escolher, por lote, o modelo de linguagem entre os
  disponíveis no servidor, registrando o modelo e o provedor de cada rodada e execução. No MVP
  são o Gemini em nível pago e um dublê sem custo para testes. A execução local foi descartada
  pelo orientador em 2026-09-18.

**Incerteza**

- **FR-013**: Cada par (resposta, critério) MUST ser avaliado em N execuções independentes
  (padrão 5, configurável por lote), e todas as execuções MUST ser guardadas.
- **FR-014**: O sistema MUST classificar cada par como convergente, divergente, sem evidência
  ou indeterminado, segundo limiar de acordo configurável (padrão 0,8) e mínimo de execuções
  válidas, e MUST NOT exibir nível único para casos não convergentes.
- **FR-015**: Para divergentes, MUST exibir a distribuição de níveis e, para cada nível que
  aparecer, uma justificativa representativa com seu trecho.
- **FR-016**: A fila de correção MUST priorizar divergentes, sem evidência e indeterminados.

**Decisão docente**

- **FR-017**: A docente MUST confirmar ou alterar cada critério de cada resposta. Cada ação
  MUST gerar registro com valor sugerido (ou "divergente"), valor decidido, motivo opcional,
  autor, instante e tempo gasto.
- **FR-018**: MUST NOT existir ação que finalize em lote várias respostas sem exibição
  individual de cada uma.
- **FR-019**: A exportação de notas MUST conter apenas respostas com todos os critérios
  decididos, identificadas por código pseudônimo.
- **FR-020**: O tempo de correção MUST ser medido pelo sistema, da abertura da resposta à
  última decisão, descontando o tempo com a tela inativa.

**Métricas e relatório**

- **FR-021**: O painel MUST exibir, por critério e no total: concordância exata, adjacente
  (±1 nível) e ponderada; taxa de divergência; concordância separada para convergentes e
  divergentes; tempo por resposta; distribuição de níveis decididos.
- **FR-022**: O sistema MUST permitir reaplicação de um lote como rodada nova independente e
  exibir a estabilidade entre rodadas (acordo por critério entre os consolidados).
- **FR-023**: O sistema MUST exportar dados brutos (execuções, consolidados, decisões, tempos,
  metadados de modelo e versão) em planilha, sem identificador de estudante.

**Estudo com docentes**

- **FR-024**: O pesquisador MUST poder criar um estudo com lote comum, dividido em metades A e
  B, convidar participantes e atribuí-los de forma balanceada aos braços "A sem apoio / B com
  apoio" e "A com apoio / B sem apoio", alternando a ordem das condições.
- **FR-025**: Na condição "sem apoio", nenhuma informação da pré-avaliação MUST ficar visível.

**Acesso**

- **FR-026**: O acesso MUST exigir conta individual. Papéis: docente (seus lotes e rubricas) e
  pesquisador (estudos, painéis agregados, exportações). Contas de participantes são criadas
  por convite.
- **FR-027**: Uma docente MUST NOT ver lotes, rubricas ou decisões de outra docente, exceto
  o lote comum de um estudo do qual participe.

### Key Entities

- **Docente**: pessoa usuária. Papel docente ou pesquisador.
- **Rubrica / Versão de rubrica**: conjunto versionado de critérios. Versão congelada quando
  usada.
- **Critério**: dimensão avaliada. Nome, descrição, peso e tipo (objetivo ou interpretativo).
- **Nível de desempenho**: posição ordinal do critério com rótulo, pontuação e descritor.
- **Lote**: enunciado da questão, versão de rubrica, conjunto de respostas e parâmetros de
  pré-avaliação (N, limiar, modelo).
- **Resposta**: texto anonimizado do estudante, com código pseudônimo.
- **Rodada**: uma aplicação completa da pré-avaliação sobre o lote (original ou reaplicação).
- **Execução**: uma avaliação de um par (resposta, critério) numa rodada. Nível ou "sem
  evidência", justificativa, validade e metadados de modelo, prompt, custo e tempo.
- **Trecho de apoio**: citação de uma execução, com posição no texto e se foi localizada.
- **Resultado consolidado**: estado (convergente, divergente, sem evidência ou indeterminado),
  nível modal, distribuição e grau de acordo por par e rodada.
- **Decisão docente**: nível decidido para um par, com valor sugerido, motivo, autor, instante,
  tempo e condição (com ou sem apoio). Histórico preservado.
- **Estudo**: lote comum, participantes, atribuição de condições e ordem.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma docente sem treinamento cria uma rubrica de 4 critérios × 4 níveis e importa
  um lote de 40 respostas em até 15 minutos.
- **SC-002**: 100% das sugestões de nível exibidas têm ao menos um trecho de apoio que existe
  no texto do estudante (auditoria por amostragem e verificação automática).
- **SC-003**: Em lote de teste com identificadores plantados (nas colunas e dentro do texto),
  0 identificadores são encontrados no armazenamento, nos registros e nas chamadas ao modelo.
- **SC-004**: 100% das notas exportadas têm decisão docente registrada para todos os critérios.
- **SC-005**: Um lote de 40 respostas × 4 critérios × 5 execuções termina em até 30 minutos,
  com custo real no máximo 20% acima da estimativa mostrada antes da execução.
- **SC-006**: Toda métrica do painel é reproduzida exatamente a partir da exportação por um
  script de análise independente.
- **SC-007**: Pelo menos 80% dos docentes do estudo concluem o roteiro de tarefas sem ajuda do
  pesquisador.
- **SC-008** (hipóteses de pesquisa, verificadas e não garantidas pelo sistema): (a) a
  concordância com a decisão docente é maior nos itens convergentes que nos divergentes;
  (b) o tempo mediano de correção por resposta é menor com apoio que sem apoio.

## Assumptions

- Cada lote corresponde a uma questão discursiva com uma rubrica. Provas com várias questões
  viram vários lotes.
- Respostas em português, em texto (digitado ou exportado do ambiente virtual). Manuscritos e
  imagens estão fora do MVP.
- Coordenações de curso recebem o relatório exportado. Visão própria para coordenação fica fora
  do MVP.
- Integração direta com o ambiente virtual (ex.: Moodle) fica fora do MVP. A entrada é
  planilha exportada.
- Interface em português, para uso em computador. Uso em celular não é requisito.
- O estudo com docentes depende de aprovação ética ou declaração institucional aplicável e do
  termo de cessão das respostas pelos docentes. Isso é providenciado fora do sistema.
- O uso de serviço comercial de modelo de linguagem envolve envio de texto anonimizado a
  terceiro. O parecer de tratamento de dados do canvas cobre essa decisão (rascunho em
  `docs/parecer-tratamento-dados.md`).
- Só o nível pago da API é usado (decisão do orientador). Modelo local não é usado.
