# Manual da docente

Este sistema ajuda a corrigir questões discursivas com uma rubrica. Ele **não dá nota**: sugere um
nível para cada critério, mostra o trecho da resposta que sustenta a sugestão e avisa quando
não tem segurança. A nota final é sempre sua.

## 1. Crie a rubrica

**Rubricas → Nova rubrica.** Para cada critério, informe:

- **Nome e descrição**: o que o critério avalia.
- **Tipo**: *objetivo* (há resposta certa, como uma definição) ou *interpretativo* (depende de
  julgamento, como a qualidade de um exemplo). Isso não muda a correção, mas o painel compara a
  instabilidade entre os dois tipos.
- **Peso** do critério na nota.
- **Níveis** (pelo menos 2), cada um com rótulo, pontuação e um **descritor**: a frase que diz o
  que caracteriza aquele nível. Descritores claros são o que mais melhora a pré-avaliação.

Para começar de um modelo pronto, use **Importar modelo (JSON)**. Há um exemplo em
`docs/modelos/verificacao-validacao.json`. Para compartilhar a sua rubrica, abra-a e clique em
**Exportar modelo**.

Depois que um lote for pré-avaliado com uma rubrica, ela fica **congelada**. Se você editá-la,
o sistema cria a versão seguinte, e o lote antigo continua ligado à versão com que foi avaliado.

## 2. Crie o lote e importe as respostas

**Lotes → Novo lote**: título, enunciado da questão, rubrica e modelo de linguagem. Um lote é uma
questão com as respostas de uma turma.

Em seguida, envie a planilha (CSV ou XLSX, até 10 MB e 1.000 linhas). A exportação do relatório
de respostas do questionário do Moodle funciona. Na prévia:

1. indique a **coluna da resposta**;
2. marque as **colunas de identificação** (nome, sobrenome, e-mail, matrícula…). Elas são
   descartadas, e nomes, e-mails, CPFs e matrículas que aparecerem **dentro** das respostas viram
   `[ESTUDANTE]`, `[EMAIL]`, `[CPF]` ou `[MATRICULA]`;
3. deixe marcada a **chave de reidentificação** se precisar lançar as notas depois.

A chave é um arquivo `codigo,identificador` baixado **uma única vez**. O sistema não guarda
cópia. **Guarde este arquivo. Ele não poderá ser gerado de novo.** Sem ele, as respostas só
são conhecidas pelo código (R001, R002…), sorteado para não seguir a ordem da planilha.

Respostas vazias ficam como "sem evidência". Respostas muito longas (mais de 15.000 caracteres)
não são pré-avaliadas: você as corrige normalmente. Nenhum texto é cortado.

## 3. Pré-avalie

Antes de executar, o sistema mostra quantas chamadas ao modelo serão feitas (respostas ×
critérios × execuções) e o **custo estimado**. Você define um **teto de custo**. Se ele for
atingido, a rodada pausa e pode ser retomada com um teto maior, sem refazer o que já terminou.

Cada critério de cada resposta é avaliado **várias vezes (padrão: 5)**, de forma independente.
O resultado de cada critério fica num de quatro estados:

| Estado | O que significa | O que você faz |
|---|---|---|
| **Convergente** (ex.: 5/5) | As execuções concordaram no mesmo nível | Confira o trecho destacado e confirme (Enter) ou escolha outro nível |
| **Divergente** | As execuções não concordaram. Não há nível sugerido | Veja a distribuição (ex.: 3× N2, 2× N3) e as justificativas, e escolha você |
| **Sem evidência** | A resposta não trata do critério, ou o nível baixo se deve à falta de algo | Escolha o nível, normalmente o mais baixo |
| **Indeterminado** | Poucas execuções válidas para sugerir algo | Corrija normalmente |

Toda sugestão vem com o **trecho literal** da resposta que a sustenta, destacado no texto. O
sistema confere que o trecho existe de fato. Execução que cita trecho inexistente é descartada.

## 4. Corrija

**Corrigir** abre a fila: as respostas com algum critério não convergente vêm primeiro, porque
é nelas que a sua atenção faz mais diferença.

Na tela da resposta:

- **↑ / ↓** mudam o critério em foco, **1–9** escolhem o nível e **Enter** confirma uma sugestão
  convergente;
- o **motivo** é opcional e vale só para a decisão em que foi escrito;
- decidir de novo o mesmo critério substitui a decisão anterior, e o **histórico** guarda tudo;
- não existe "aceitar tudo": cada critério de cada resposta é uma decisão sua.

O tempo de correção é medido automaticamente. Ele só conta com a aba visível e pausa depois de
60 s sem uso do teclado ou do mouse.

## 5. Baixe as notas

Na página do lote, **Baixar notas (CSV)** gera `codigo, <critério…>, nota_total` **somente com
as respostas em que todos os critérios foram decididos**. Use a chave de reidentificação para
ligar os códigos aos estudantes.

## 6. Painel de consistência

**Painel de consistência** mostra, por critério:

- quanto a pré-avaliação concordou com você (exata, com diferença de até um nível, e κ ponderado);
- a concordância separada para itens convergentes e não convergentes;
- a taxa de divergência;
- a **estabilidade** entre a rodada original e uma **reaplicação** (botão *Reaplicar lote*: uma
  rodada nova e independente, com custo próprio);
- o tempo mediano por resposta.

O seletor de **limiar** (0,6 / 0,8 / 1,0) recalcula os estados só para visualização, sem alterar
nada. **Exportar dados (ZIP)** entrega os dados de pesquisa sem identificação, com o script
`analysis/reproduzir_metricas.py`, que recalcula os números do painel.

## 7. Estudo com docentes (pesquisador)

Em **Estudos**, o pesquisador cria um estudo sobre um lote já pré-avaliado, convida docentes por
e-mail (cada um recebe um link para definir a senha) e inicia. O sistema divide as respostas em
duas metades e sorteia, para cada docente, qual metade será corrigida **sem apoio** e qual **com
apoio**, e em que ordem. Na condição sem apoio o servidor não envia nada da pré-avaliação.

## Limites que você precisa conhecer

- A pré-avaliação é feita por um modelo de linguagem, que erra e varia. Por isso o sistema mostra
  a divergência e nunca decide sozinho.
- Só use dados reais de estudantes com a chave de API do **nível pago** do Google configurada
  (`GEMINI_PAID_TIER=true`). O sistema recusa pré-avaliar um lote real sem isso.
- A rubrica é o que mais pesa na qualidade. Critérios vagos produzem mais divergência.
