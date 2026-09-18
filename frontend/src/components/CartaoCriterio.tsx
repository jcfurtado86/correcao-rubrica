import type { ReactNode } from "react";
import { EXPLICACAO_ESTADO, ROTULO_ESTADO, type Criterio, type Sugestao } from "../services/tipos";
import Distribuicao from "./Distribuicao";

type Props = {
  criterio: Criterio;
  cor: number;
  sugestao: Sugestao;
  onFoco: (ativo: boolean) => void;
  children?: ReactNode; // controles de decisão (US3)
};

export default function CartaoCriterio({ criterio, cor, sugestao, onFoco, children }: Props) {
  const convergente = sugestao.estado === "CONVERGENTE" && sugestao.nivel_sugerido;
  return (
    <section
      className="cartao grade"
      style={{ gap: "0.6rem" }}
      onMouseEnter={() => onFoco(true)}
      onMouseLeave={() => onFoco(false)}
      data-testid={`criterio-${criterio.id}`}
    >
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>
          <mark className={`cor-${cor % 10}`}>&nbsp;</mark> {criterio.nome}{" "}
          <span className="suave" style={{ fontWeight: 400, fontSize: "0.85rem" }}>
            {criterio.tipo === "OBJETIVO" ? "objetivo" : "interpretativo"}
          </span>
        </h3>
        <span className={`selo ${sugestao.estado}`}>
          {ROTULO_ESTADO[sugestao.estado]}
          {sugestao.acordo && sugestao.estado !== "OCULTO" && ` ${sugestao.acordo.votos}/${sugestao.acordo.validas}`}
        </span>
      </div>
      {convergente ? (
        <div>
          <p style={{ margin: "0 0 0.3rem" }} data-testid="nivel-sugerido">
            Nível sugerido:{" "}
            <strong>
              {sugestao.nivel_sugerido!.codigo} — {sugestao.nivel_sugerido!.rotulo}
            </strong>
          </p>
          <p className="suave" style={{ margin: 0 }}>
            {sugestao.justificativa}
          </p>
        </div>
      ) : (
        <p className="suave" style={{ margin: 0 }}>
          {EXPLICACAO_ESTADO[sugestao.estado]}
          {sugestao.estado === "SEM_EVIDENCIA" && sugestao.justificativa ? ` ${sugestao.justificativa}` : ""}
        </p>
      )}
      {sugestao.alternativas && sugestao.alternativas.length > 0 && <Distribuicao alternativas={sugestao.alternativas} />}
      {children}
    </section>
  );
}
