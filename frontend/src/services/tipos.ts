// Tipos das respostas da API (contracts/api.md).

export type TipoCriterio = "OBJETIVO" | "INTERPRETATIVO";

export type Nivel = { id: number; ordem: number; codigo: string; rotulo: string; descritor: string; pontuacao: number };
export type Criterio = {
  id: number;
  ordem: number;
  nome: string;
  descricao: string;
  peso: number;
  tipo: TipoCriterio;
  niveis: Nivel[];
};
export type Versao = { id: number; numero: number; congelada: boolean; hash: string; em_uso: boolean; criterios: Criterio[] };
export type Rubrica = { id: number; titulo: string; descricao: string; versao: Versao };
export type RubricaResumo = {
  id: number;
  titulo: string;
  descricao: string;
  versao_vigente: { id: number; numero: number; congelada: boolean };
  n_criterios: number;
};

export type RodadaResumo = { id: number; numero: number; status: StatusRodada; modelo: string };
export type Lote = {
  id: number;
  titulo: string;
  enunciado: string;
  versao_rubrica: number;
  rubrica_titulo: string;
  n_execucoes: number;
  limiar_acordo: number;
  min_validas: number;
  provedor_llm: string;
  modelo_llm: string;
  teto_usd: number;
  sintetico: boolean;
  criado_em: string;
  n_respostas: number;
  avisos?: Record<string, number>;
  versao?: { id: number; numero: number; rubrica: number };
  criterios?: Criterio[];
  rodadas?: RodadaResumo[];
};

export type RespostaResumo = { id: number; codigo: string; n_caracteres: number; n_substituicoes: number; aviso: string | null };

export type StatusRodada = "ESTIMADA" | "EM_EXECUCAO" | "PAUSADA_TETO" | "CONCLUIDA" | "COM_FALHAS";
export type Rodada = {
  id: number;
  lote: number;
  numero: number;
  status: StatusRodada;
  provedor: string;
  modelo: string;
  custo_estimado_usd: number;
  custo_acumulado_usd: number;
  teto_usd: number;
  total: number;
  pendentes: number;
  concluidas: number;
  invalidas: number;
  falhas: number;
};

export type Estimativa = {
  n_chamadas: number;
  respostas_elegiveis: number;
  criterios: number;
  n_execucoes: number;
  tokens_entrada_est: number;
  tokens_saida_est: number;
  custo_estimado_usd: number;
  teto_usd: number;
  base_saida: "observada" | "configuracao";
  preco_vigente: { modelo: string; entrada_por_milhao: number; saida_por_milhao: number };
};

export type TrechoBruto = { texto_citado: string; localizado: boolean; inicio: number | null; fim: number | null };
export type ExecucaoBruta = {
  indice: number;
  status: string;
  valida: boolean | null;
  motivo_invalidez: string | null;
  nivel_codigo: string;
  justificativa: string;
  erro: string | null;
  trechos: TrechoBruto[];
};
export type ExecucoesDaResposta = {
  id: number;
  codigo: string;
  texto: string;
  aviso: string | null;
  rodada: number | null;
  criterios: { criterio: number; nome: string; ordem: number; execucoes: ExecucaoBruta[] }[];
};

export const ROTULO_STATUS: Record<StatusRodada, string> = {
  ESTIMADA: "Estimada",
  EM_EXECUCAO: "Em execução",
  PAUSADA_TETO: "Pausada pelo teto de custo",
  CONCLUIDA: "Concluída",
  COM_FALHAS: "Concluída com falhas",
};

export const ROTULO_MOTIVO: Record<string, string> = {
  JSON_INVALIDO: "saída fora do formato",
  NIVEL_FORA: "nível inexistente",
  SEM_TRECHO: "sem trecho de apoio",
  TRECHO_NAO_LOCALIZADO: "trecho não encontrado no texto",
  TRECHO_CURTO: "trecho curto demais",
  INCOERENTE_SEM_EVIDENCIA: "“sem evidência” com trecho",
};

export function usd(valor: number): string {
  return `US$ ${valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
}

export type EstadoSugestao = "CONVERGENTE" | "DIVERGENTE" | "SEM_EVIDENCIA" | "INDETERMINADO" | "INDISPONIVEL" | "OCULTO";
export type NivelSugerido = { id: number | null; codigo: string; rotulo: string; ordem: number | null };
export type TrechoSugestao = { inicio: number; fim: number; texto: string };
export type Alternativa = { nivel: NivelSugerido; votos: number; justificativa: string; trechos: TrechoSugestao[] };
export type Sugestao = {
  criterio: number;
  estado: EstadoSugestao;
  nivel_sugerido?: NivelSugerido | null;
  acordo?: { votos: number; validas: number };
  justificativa?: string;
  trechos?: TrechoSugestao[];
  alternativas?: Alternativa[];
};
export type SugestoesDaResposta = { id: number; codigo: string; texto: string; aviso: string | null; rodada: number | null; criterios: Sugestao[] };

export type ItemFila = {
  resposta: number;
  codigo: string;
  estado_pior: EstadoSugestao;
  estados: Partial<Record<EstadoSugestao, number>>;
  n_decididos: number;
  n_criterios: number;
  finalizada: boolean;
};
export type Fila = { rodada: number | null; contagem: Partial<Record<EstadoSugestao, number>>; respostas: ItemFila[] };

export const ROTULO_ESTADO: Record<EstadoSugestao, string> = {
  CONVERGENTE: "Convergente",
  DIVERGENTE: "Divergente",
  SEM_EVIDENCIA: "Sem evidência",
  INDETERMINADO: "Indeterminado",
  INDISPONIVEL: "Sem pré-avaliação",
  OCULTO: "Sem apoio",
};

export const EXPLICACAO_ESTADO: Record<EstadoSugestao, string> = {
  CONVERGENTE: "As execuções concordaram. Confira o trecho e confirme ou altere.",
  DIVERGENTE: "As execuções não concordaram. Não há nível sugerido: escolha você.",
  SEM_EVIDENCIA: "A resposta não parece tratar deste critério. Escolha o nível.",
  INDETERMINADO: "Execuções válidas insuficientes para uma sugestão. Escolha o nível.",
  INDISPONIVEL: "Sem pré-avaliação para esta resposta. Corrija normalmente.",
  OCULTO: "Condição sem apoio: corrija sem sugestão.",
};

export type Condicao = "COM_APOIO" | "SEM_APOIO";
export type DecisaoT = {
  id: number;
  criterio: number;
  nivel: number;
  nivel_codigo: string;
  tipo: "CONFIRMACAO" | "ALTERACAO" | "ESCOLHA" | "CEGA";
  estado_exibido: string;
  nivel_sugerido: number | null;
  motivo: string;
  tempo_ativo_ms: number;
  vigente: boolean;
  substitui: number | null;
  criado_em: string;
};
export type Sessao = {
  sessao: number;
  resposta: number;
  codigo: string;
  texto: string;
  aviso: string | null;
  condicao: Condicao;
  rodada: number | null;
  criterios: Sugestao[];
  decisoes_vigentes: DecisaoT[];
};

export const ROTULO_TIPO: Record<DecisaoT["tipo"], string> = {
  CONFIRMACAO: "confirmou a sugestão",
  ALTERACAO: "alterou a sugestão",
  ESCOLHA: "escolheu (sem sugestão)",
  CEGA: "decidiu sem apoio",
};

export type Concordancia = { n: number; exata: number | null; adjacente: number | null; qwk: number | null };
export type BlocoPainel = {
  n_pares: number;
  estados: Partial<Record<EstadoSugestao, number>>;
  taxa_divergencia: number | null;
  taxa_nao_convergente: number | null;
  acordo_medio: number | null;
  fleiss: number | null;
  concordancia: Concordancia;
  seletiva: {
    cobertura: number | null;
    n_convergentes: number;
    n_nao_convergentes: number;
    exata_convergentes: number | null;
    exata_nao_convergentes: number | null;
  };
  estabilidade: { n: number; exata: number | null; qwk: number | null } | null;
  distribuicao_decidida: Record<string, number>;
};
export type Painel = {
  rodada: number | null;
  rodadas: number[];
  limiar: number;
  recalculado: boolean;
  modelo: string;
  custo: { estimado_usd: number; acumulado_usd: number };
  criterios: (BlocoPainel & { criterio: number; nome: string; tipo: TipoCriterio })[];
  total: BlocoPainel;
  por_tipo: Record<TipoCriterio, { n_pares: number; taxa_divergencia: number | null; taxa_nao_convergente: number | null; exata: number | null }>;
  tempo: { n_respostas: number; mediana_ms: number | null; media_ms: number | null };
};
