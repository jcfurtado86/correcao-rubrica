import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import TextoComDestaques from "../components/TextoComDestaques";
import type { Destaque } from "../components/destaques";
import { ROTULO_MOTIVO, type ExecucoesDaResposta } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

export default function RespostaInspecao() {
  const { id } = useParams();
  const { dados, erro } = useCarregar<ExecucoesDaResposta>(`/respostas/${id}/execucoes/`);
  const [focado, setFocado] = useState<number | null>(null);

  const destaques = useMemo<Destaque[]>(() => {
    if (!dados) return [];
    return dados.criterios.flatMap((c, i) =>
      c.execucoes
        .filter((e) => e.valida)
        .flatMap((e) =>
          e.trechos
            .filter((t) => t.localizado && t.inicio !== null && t.fim !== null)
            .map((t) => ({
              inicio: t.inicio!,
              fim: t.fim!,
              cor: i,
              rotulo: `${c.nome}: ${e.nivel_codigo} (execução ${e.indice})`,
              ativo: focado === c.criterio,
            })),
        ),
    );
  }, [dados, focado]);

  if (erro) return <p className="erro">{erro}</p>;
  if (!dados) return <p className="suave">Carregando…</p>;

  return (
    <div className="grade">
      <h1>
        Resposta {dados.codigo} <span className="suave">· execuções da rodada {dados.rodada ?? "—"}</span>
      </h1>
      <div className="duas-colunas">
        <TextoComDestaques texto={dados.texto} destaques={destaques} />
        <div className="grade">
          {dados.criterios.map((c, i) => (
            <div
              key={c.criterio}
              className="cartao"
              onMouseEnter={() => setFocado(c.criterio)}
              onMouseLeave={() => setFocado(null)}
            >
              <h3>
                <mark className={`cor-${i % 10}`}>&nbsp;</mark> {c.nome}
              </h3>
              <table>
                <tbody>
                  {c.execucoes.map((e) => (
                    <tr key={e.indice}>
                      <td>#{e.indice}</td>
                      <td>
                        <strong>{e.status === "CONCLUIDA" ? e.nivel_codigo || "—" : e.status}</strong>
                      </td>
                      <td>
                        {e.valida === false && (
                          <span className="erro">inválida: {ROTULO_MOTIVO[e.motivo_invalidez ?? ""] ?? e.motivo_invalidez}. </span>
                        )}
                        {e.erro && <span className="erro">{e.erro} </span>}
                        <span className="suave">{e.justificativa}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
