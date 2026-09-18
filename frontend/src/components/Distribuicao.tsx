import type { Alternativa } from "../services/tipos";

export default function Distribuicao({ alternativas }: { alternativas: Alternativa[] }) {
  const resumo = alternativas.map((a) => `${a.votos}× ${a.nivel.codigo}`).join(", ");
  return (
    <div className="grade" style={{ gap: "0.4rem" }}>
      <p style={{ margin: 0 }}>
        <strong>Distribuição:</strong> {resumo}
      </p>
      {alternativas.map((a) => (
        <details key={a.nivel.codigo} className="alternativa">
          <summary>
            {a.nivel.codigo} — {a.nivel.rotulo} <span className="suave">({a.votos} {a.votos === 1 ? "execução" : "execuções"})</span>
          </summary>
          <p className="suave" style={{ margin: "0.3rem 0" }}>
            {a.justificativa}
          </p>
          {a.trechos.map((t) => (
            <blockquote key={t.inicio} style={{ margin: "0.2rem 0 0.2rem 0.5rem" }}>
              “{t.texto}”
            </blockquote>
          ))}
        </details>
      ))}
    </div>
  );
}
