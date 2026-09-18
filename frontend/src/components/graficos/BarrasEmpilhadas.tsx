import { useDica } from "./Dica";
import type { Serie } from "./BarrasAgrupadas";

export type Pilha = { nome: string; contagens: Record<string, number> };

const pct = (v: number) => `${Math.round(v * 100)}%`;
const LARGURA_MINIMA_ROTULO = 0.12; // só rotula dentro do segmento se couber

// Barra 100% empilhada (parte do todo). 2px de superfície entre segmentos,
// ponta arredondada só no fim da pilha, rótulo interno só quando cabe.
export default function BarrasEmpilhadas({ series, pilhas, titulo }: { series: Serie[]; pilhas: Pilha[]; titulo: string }) {
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
      <div className="grade" style={{ gap: "0.5rem" }}>
        {pilhas.map((p) => {
          const total = series.reduce((a, s) => a + (p.contagens[s.chave] ?? 0), 0);
          return (
            <div className="linha-grafico" key={p.nome}>
              <div className="rotulo-categoria">{p.nome}</div>
              <div className="faixa">
                <div className="pilha">
                  {series.map((s) => {
                    const n = p.contagens[s.chave] ?? 0;
                    if (!n || !total) return null;
                    const fracao = n / total;
                    return (
                      <div
                        key={s.chave}
                        className="segmento"
                        style={{ width: `${fracao * 100}%`, background: s.cor }}
                        {...props(
                          <>
                            <strong>{pct(fracao)}</strong> {s.nome}
                            <br />
                            <span className="suave">
                              {p.nome} · {n} de {total} pares
                            </span>
                          </>,
                          `${p.nome}, ${s.nome}: ${pct(fracao)} (${n} de ${total})`,
                        )}
                      >
                        {fracao >= LARGURA_MINIMA_ROTULO ? pct(fracao) : ""}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {elemento}
    </figure>
  );
}
