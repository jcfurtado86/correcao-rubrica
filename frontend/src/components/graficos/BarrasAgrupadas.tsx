import { useDica } from "./Dica";

export type Serie = { chave: string; nome: string; cor: string };
export type Categoria = { nome: string; valores: Record<string, { valor: number | null; n: number }> };

const pct = (v: number) => `${Math.round(v * 100)}%`;
const GRADE = [0, 0.25, 0.5, 0.75, 1];

// Barras horizontais agrupadas numa escala 0–100%. Barra ≤ 12px, ponta de dados
// arredondada, 2px de superfície entre as barras do grupo, grade recessiva.
export default function BarrasAgrupadas({ series, categorias, titulo }: { series: Serie[]; categorias: Categoria[]; titulo: string }) {
  const { props, elemento } = useDica();
  return (
    <figure className="grafico" style={{ margin: 0 }} aria-label={titulo}>
      <div className="legenda">
        {series.map((s) => (
          <span key={s.chave}>
            <span className="amostra" style={{ background: s.cor }} />
            {s.nome}
          </span>
        ))}
      </div>
      <div className="grade" style={{ gap: "0.6rem" }}>
        {categorias.map((c) => (
          <div className="linha-grafico" key={c.nome}>
            <div className="rotulo-categoria">{c.nome}</div>
            <div className="faixa">
              {GRADE.slice(1).map((g) => (
                <span key={g} className="grade-x" style={{ left: `${g * 100}%` }} />
              ))}
              <div style={{ display: "grid", gap: 2, position: "relative" }}>
                {series.map((s) => {
                  const v = c.valores[s.chave];
                  const valor = v?.valor ?? null;
                  const rotulo = `${c.nome}, ${s.nome}: ${valor === null ? "sem dados" : pct(valor)} (n = ${v?.n ?? 0})`;
                  return (
                    <div
                      key={s.chave}
                      className="alvo"
                      {...props(
                        <>
                          <strong>{valor === null ? "—" : pct(valor)}</strong> {s.nome}
                          <br />
                          <span className="suave">
                            {c.nome} · n = {v?.n ?? 0}
                          </span>
                        </>,
                        rotulo,
                      )}
                    >
                      {valor !== null && valor > 0 && <span className="barra" style={{ width: `${valor * 100}%`, background: s.cor }} />}
                      <span className="valor-barra">{valor === null ? "sem dados" : pct(valor)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="eixo-x">
        <span />
        <div>
          {GRADE.map((g) => (
            <span key={g} style={{ position: "absolute", left: `${g * 100}%`, transform: "translateX(-50%)" }}>
              {pct(g)}
            </span>
          ))}
        </div>
      </div>
      {elemento}
    </figure>
  );
}
