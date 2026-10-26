// Textos dos Instrumentos 2, 4 e 5 da atividade extensionista (instrumentos_validacao_correcao.pdf).

export const ESCALA_CONCORDANCIA = ["Discordo totalmente", "Discordo", "Nem concordo nem discordo", "Concordo", "Concordo totalmente"];

export const PERFIL = [
  {
    campo: "nivel",
    pergunta: "Nível em que leciona",
    opcoes: [
      ["SO_GRADUACAO", "Só graduação"],
      ["GRADUACAO_POS", "Graduação e pós-graduação"],
      ["BASICA_GRADUACAO", "Educação básica e graduação"],
    ],
  },
  {
    campo: "tempo_docencia",
    pergunta: "Tempo de docência",
    opcoes: [
      ["MENOS_5", "Menos de 5 anos"],
      ["DE_5_A_15", "De 5 a 15 anos"],
      ["MAIS_15", "Mais de 15 anos"],
    ],
  },
  {
    campo: "uso_ia",
    pergunta: "Já usou IA para corrigir avaliações?",
    opcoes: [
      ["NUNCA", "Nunca"],
      ["ALGUMAS", "Algumas vezes"],
      ["FREQUENTE", "Com frequência"],
    ],
  },
] as const;

export const ITENS_APOIO = [
  "As sugestões de nível foram coerentes com a rubrica.",
  "Os trechos destacados na resposta ajudaram a conferir a sugestão.",
  "Saber onde a IA divergiu me ajudou a decidir onde prestar mais atenção.",
  "Senti que a decisão final continuou sendo minha.",
  "Eu usaria a ferramenta para corrigir avaliações das minhas turmas.",
];

export const ITENS_SUS = [
  "Eu acho que gostaria de usar este sistema com frequência.",
  "Achei o sistema desnecessariamente complexo.",
  "Achei o sistema fácil de usar.",
  "Acho que precisaria da ajuda de uma pessoa com conhecimentos técnicos para usar este sistema.",
  "Achei que as diversas funções deste sistema estão bem integradas.",
  "Achei que o sistema apresenta muita inconsistência.",
  "Imagino que a maioria das pessoas aprenderia a usar este sistema rapidamente.",
  "Achei o sistema muito complicado de usar.",
  "Eu me senti muito confiante ao usar o sistema.",
  "Precisei aprender muitas coisas antes de conseguir usar este sistema.",
];
