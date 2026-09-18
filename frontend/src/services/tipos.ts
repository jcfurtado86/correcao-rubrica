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
