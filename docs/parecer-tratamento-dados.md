# Parecer sobre o tratamento de produção de estudante — RASCUNHO

> Rascunho técnico para revisão do orientador, entrega prevista no canvas ("parecer quanto ao
> tratamento de produção de estudante"). **Não é parecer jurídico.** Os enquadramentos legais
> abaixo são indicações a confirmar com a instância institucional competente (CEP ou assessoria
> de proteção de dados).

## 1. O que é tratado

| Dado | Origem | Tratamento no sistema |
|---|---|---|
| Nome, sobrenome, e-mail, matrícula e usuário do estudante | colunas da planilha exportada do AVA | lidos **só em memória** durante a importação e descartados. Nunca são gravados no banco, nos logs ou nos arquivos de exportação |
| Texto da resposta discursiva | coluna da planilha | anonimizado na carga e guardado com código pseudônimo (R001…) |
| Identificadores escritos dentro do texto | o próprio estudante | substituídos na carga por `[ESTUDANTE]`, `[EMAIL]`, `[CPF]` e `[MATRICULA]`. Guarda-se só a contagem de substituições |
| Chave código ↔ estudante (opcional) | gerada na importação | entregue à docente uma única vez, em arquivo. **O sistema não guarda cópia** |
| Decisões, tempos e motivos da docente | uso do sistema | vinculados à conta da docente. Na exportação de pesquisa, docentes viram `D01…` e participantes de estudo `P01…`. Os motivos (texto livre) só saem quando pedidos |

## 2. Medidas técnicas implementadas (verificáveis)

- **Upload em memória**: a planilha não é gravada em disco (`MemoryFileUploadHandler`, limite de
  10 MB).
- **Anonimização na carga**: e-mail, CPF (com e sem máscara) e sequências de 8 a 14 dígitos por
  expressão regular. Nomes da própria linha **e de todas as outras linhas** do arquivo (um
  estudante pode citar colega), sem acento, sem caixa e com limite de palavra.
- **Auditoria automatizada**: teste e comando `auditar_identificadores` que procuram cada
  identificador de uma turma fictícia em todas as colunas de texto do banco, nos logs e nos
  prompts enviados ao modelo. Resultado atual: **0 ocorrências de 184 identificadores plantados**.
- **Logs**: filtro que remove campos de texto de resposta e trunca mensagens longas.
- **Pseudônimos aleatórios**: a ordem dos códigos é sorteada, para não reproduzir a ordem
  (em geral alfabética) da planilha.
- **Acesso**: cada docente só vê os próprios lotes. O participante de estudo só acessa as
  respostas do estudo, pela rota do estudo, e na condição "sem apoio" o servidor não envia
  nenhuma informação da pré-avaliação.

## 3. Envio de texto ao provedor de IA (Google Gemini)

O texto **já anonimizado** de cada resposta é enviado à API Gemini, junto com o enunciado e a
rubrica, uma vez por critério e por execução.

Trechos dos termos da Gemini API, consultados em 2026-09-18:

- **Nível gratuito**: "Google uses the content you submit to the Services and any generated
  responses to provide, improve, and develop Google products and services"; "human reviewers may
  read, annotate, and process your API input and output"; "Do not submit sensitive, confidential,
  or personal information to the Unpaid Services".
- **Nível pago**: "Google doesn't use your prompts (including associated system instructions,
  cached content, and files such as images, videos, or documents) or responses to improve our
  products"; o registro é feito "solely for detecting and preventing violations of the
  Prohibited Use Policy".
- **Idade**: "You must be 18 years of age or older to use the APIs", e o serviço não pode ser
  usado em cliente "directed towards or is likely to be accessed by individuals under the age of
  18".

Decisão do projeto: **só o nível pago é usado**. O sistema recusa pré-avaliar lote real (não
sintético) quando `GEMINI_PAID_TIER` não está ativo. Os usuários do sistema são docentes
(maiores de idade).

**A confirmar**: o prazo de retenção dos registros de abuso no nível pago e a localização do
processamento. O envio a servidor fora do país é transferência internacional de dados.

## 4. Enquadramento a confirmar

- **Natureza do dado**: o texto anonimizado reduz o risco, mas o **arquivo-chave** torna o
  conjunto **pseudonimizado**, e não anonimizado, enquanto a docente o mantiver. Tratar como dado
  pessoal para fins de salvaguarda.
- **Finalidade**: apoio à correção (docente) e pesquisa (TCC e artigo). Avaliar a base legal de
  estudo por órgão de pesquisa, com anonimização sempre que possível, e a necessidade de
  consentimento ou termo de cessão das respostas pelos docentes que as fornecerem.
- **Transferência internacional**: envio ao provedor de IA (seção 3).
- **Estudo com docentes (protocolo A)**: pesquisa com seres humanos. Verificar a submissão ao CEP
  e o termo de consentimento dos participantes, já que tempo e decisões de cada docente são
  registrados.
- **Educação básica** (extensão prevista no canvas): textos de crianças e adolescentes exigem
  tratamento no melhor interesse deles e **reavaliação completa** antes de qualquer uso real.

## 5. Riscos residuais

1. **Identificador fora das colunas**: nome de professor, de terceiros ou apelido escrito no
   texto não é removido se não constar de nenhuma coluna mapeada. Mitigação: revisão visual por
   amostragem antes da pré-avaliação de lote real.
2. **Conteúdo sensível no próprio texto** (saúde, religião, relato pessoal): não é detectado.
   Mitigação: orientar a escolha das questões usadas no estudo.
3. **Arquivo-chave**: sua guarda é responsabilidade da docente. Recomenda-se guardá-lo fora de
   pastas sincronizadas e apagá-lo quando as notas forem lançadas.
4. **Exportação com texto** (`incluir_texto=1`): o texto anonimizado sai do sistema. Usar só
   quando a análise exigir.

## 6. Recomendações antes de carregar dados reais

- [ ] Parecer ou dispensa do CEP para o estudo com docentes.
- [ ] Termo de cessão das respostas pelos docentes que as fornecerem.
- [ ] Confirmar que a chave de API usada é de projeto com faturamento ativo.
- [ ] Rodar `manage.py auditar_identificadores` com os identificadores do lote real, gerados a
      partir da própria planilha e apagados depois, antes da pré-avaliação.
- [ ] Definir o prazo de guarda do banco e da exportação de pesquisa e a forma de descarte.
