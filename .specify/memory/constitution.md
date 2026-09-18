# Correção Assistida por Rubrica — Constituição

Fonte: Canvas de Projeto "Correção Assistida por Rubrica com Aferição de Consistência Avaliativa"
(autor Glauco Silva Sousa, orientador Júlio Furtado, 22/07/2026).

## Princípios Fundamentais

### I. Decisão Docente Soberana (INEGOCIÁVEL)

- O sistema produz **pré-avaliação**, nunca nota. Nenhum resultado por critério ou total
  pode ser exportado, publicado ou considerado final sem confirmação explícita do docente.
- Todo resultado exibido ao docente é editável; confirmar e alterar são ações registradas
  com autor, instante, valor sugerido, valor decidido e, quando houver, motivo.
- Não existe operação de "aceitar tudo" em lote que dispense a visualização de cada
  critério de cada resposta.

Razão: o risco nº 1 do canvas é a delegação da decisão avaliativa ao sistema.

### II. Ancoragem Obrigatória no Texto

- Toda atribuição de nível MUST vir acompanhada de justificativa e de ao menos um trecho
  do texto do estudante que a sustente.
- O trecho MUST ser verificado pelo sistema, e não pelo modelo: localizado no texto
  original com posição inicial e final. Trecho não localizado invalida a execução.
- Execução sem trecho válido não conta como voto de nível; conta como abstenção.
- Ausência de conteúdo (resposta que não trata do critério) é um resultado próprio,
  "sem evidência", sempre encaminhado ao docente, e nunca convertido automaticamente
  em nível.

Razão: explicabilidade e auditabilidade do julgamento; impede justificativa inventada.

### III. Incerteza como Informação

- Cada par (resposta, critério) é avaliado por N execuções independentes (N configurável,
  padrão 5). Todas as execuções são persistidas, e não apenas o consolidado.
- O resultado é "convergente" somente se a proporção do nível modal entre execuções
  válidas atingir o limiar configurado (padrão 0,8) com mínimo de execuções válidas.
  Caso contrário, é "divergente" e MUST ser apresentado como tal, com a distribuição
  dos níveis e as justificativas de cada nível divergente. Nunca como valor único.
- Casos divergentes e "sem evidência" são priorizados na fila do docente.

Razão: é a contribuição central do trabalho. O canvas mostra variação de 80 pontos em
10 execuções idênticas, concentrada nos critérios interpretativos.

### IV. Privacidade desde a Carga

- Identificadores de estudante (nome, e-mail, matrícula, CPF, usuário) são removidos
  no momento da importação e substituídos por código pseudônimo. O identificador original
  MUST NOT ser persistido no banco, em logs ou em chamadas ao modelo de linguagem.
- O corpo da resposta passa por varredura de dados pessoais (os próprios identificadores
  do arquivo, e-mails, números de matrícula/CPF) antes de ser armazenado.
- A eventual chave de reidentificação é entregue ao docente uma única vez, no momento
  da carga, e não fica no servidor.
- Nenhum dado de estudante real é versionado no repositório.

Razão: produção de estudante pode conter dado pessoal (LGPD); o canvas exige parecer.

### V. Rastreabilidade para Pesquisa

- Toda execução registra, diretamente ou pela rodada: modelo e provedor, versão do prompt,
  versão (hash) da rubrica, semente, tokens, custo, latência e resposta bruta.
- Rubrica em uso por um lote é imutável; alteração gera nova versão.
- Toda métrica do relatório (concordância, estabilidade, taxa de divergência, tempo)
  MUST ser recalculável a partir dos registros, e exportável em formato tabular para
  análise estatística externa.
- O tempo de correção é medido pelo sistema (abertura → decisão), não autodeclarado.

Razão: o produto é também instrumento de pesquisa; os resultados vão para artigo.

### VI. Simplicidade de MVP e Custo Controlado

- Um desenvolvedor, doze semanas: um único serviço implantável, um banco relacional,
  sem microsserviços, filas externas ou infraestrutura que o problema não exija (YAGNI).
- O acesso ao modelo de linguagem passa por uma interface única de provedor, permitindo
  trocar de provedor sem alterar o domínio.
- Todo lançamento de pré-avaliação exibe estimativa de custo antes de executar e respeita
  teto configurável por lote; resultados idênticos são reaproveitados por cache.

## Restrições de Dados, Modelo e Custo

- Lotes reais só entram no sistema já anonimizados pelo próprio fluxo de carga;
  lotes de teste sintéticos são rotulados como tal.
- O prompt de avaliação é artefato versionado no repositório; mudança de prompt é
  mudança de versão e invalida comparações diretas entre lotes.
- A unidade de cache da pré-avaliação é a rodada: execução concluída nunca é refeita, e
  retomar ou reprocessar a mesma rodada não gera custo novo. A reaplicação para medir
  estabilidade usa rodada nova, com sementes novas.

## Fluxo de Desenvolvimento e Portões de Qualidade

- Desenvolvimento guiado por especificação (Spec Kit): constitution → specify → clarify
  → plan → tasks → implement. Nenhuma implementação sem spec aprovada.
- Mecanismos centrais têm testes automatizados obrigatórios antes da integração:
  verificação de âncora, consolidação/convergência, anonimização e cálculo de métricas.
- Testes não chamam o modelo real; usam provedor simulado determinístico. Avaliação com
  modelo real é experimento registrado, não teste de unidade.
- Todo PR verifica conformidade com os Princípios I a IV.

## Governança

- Esta constituição prevalece sobre as demais práticas do projeto.
- Emendas exigem registro do motivo, aprovação do orientador e atualização da versão:
  MAJOR para remoção/redefinição de princípio; MINOR para princípio ou seção nova;
  PATCH para esclarecimento de redação.
- Complexidade que contrarie o Princípio VI MUST ser justificada no plano
  (seção de rastreamento de complexidade).

**Version**: 1.0.1 | **Ratified**: 2026-09-18 | **Last Amended**: 2026-09-18

Emenda 1.0.1 (PATCH, esclarecimento): a redação do cache e do registro de execução passou a
descrever o que foi implementado (cache por rodada; hash da rubrica e versão do prompt
guardados pela rodada). A interface de provedor deixou de citar execução local, que o
orientador descartou.
