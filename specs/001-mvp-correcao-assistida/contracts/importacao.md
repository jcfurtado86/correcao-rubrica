# Contrato de importação de respostas

## Arquivo aceito

- CSV (UTF-8 ou UTF-8 com BOM, separador `,` ou `;` detectado) ou XLSX (primeira planilha).
- Primeira linha = cabeçalho. Máximo de 10 MB e 1.000 linhas no MVP.
- Uma linha = uma resposta de um estudante a **uma** questão. Exportações do Moodle (relatório
  de respostas do questionário) funcionam com mapeamento manual das colunas.

## Mapeamento (feito pela docente na prévia)

| Campo | Obrigatório | Uso |
|---|---|---|
| `coluna_resposta` | sim | vira `Resposta.texto` (após anonimização) |
| `colunas_identificacao` | sim, ≥ 1 | nome, sobrenome, e-mail, matrícula, usuário… Usadas **só em memória**: montam a lista de termos a remover do texto e a chave de reidentificação. Nunca são gravadas |
| demais colunas | — | ignoradas e descartadas |

## Anonimização (em memória, antes de qualquer gravação)

1. Termos de identificação: cada valor das colunas mapeadas, e cada palavra com ≥ 3 letras dos
   valores de nome, comparados sem acento e sem caixa, com limite de palavra.
2. Substituições no texto da resposta, nesta ordem:
   - e-mail → `[EMAIL]`
   - CPF (`000.000.000-00` ou 11 dígitos) → `[CPF]`
   - sequências de 8 a 14 dígitos → `[MATRICULA]`
   - termos de identificação da **própria linha e de qualquer outra linha do arquivo** →
     `[ESTUDANTE]` (um estudante pode citar colega)
3. Grava-se apenas `n_substituicoes`.
4. Códigos `R001…` atribuídos após embaralhar as linhas, para que o código não revele a ordem
   original do arquivo (geralmente alfabética).

## Avisos

| Tipo | Condição | Efeito |
|---|---|---|
| `VAZIA` | texto vazio ou só espaços | fica no lote. A pré-avaliação produz `SEM_EVIDENCIA` para todos os critérios sem chamar o modelo |
| `LONGA` | > 15.000 caracteres | fica no lote **sem** pré-avaliação, marcada para correção manual. Nunca truncada |
| `DUPLICADA` | texto idêntico ao de outra linha | informativo. Continuam respostas distintas |

## Chave de reidentificação (opcional)

CSV `codigo,identificador` (identificador = valores das colunas de identificação unidos por
` | `), devolvido em base64 na resposta da importação, com nome
`chave-<lote>-<data>.csv`. O sistema não guarda cópia, e a interface avisa: "Guarde este arquivo.
Ele não poderá ser gerado de novo."
