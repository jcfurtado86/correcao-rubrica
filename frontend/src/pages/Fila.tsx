import { Link, useParams } from "react-router-dom";
import { ROTULO_ESTADO, type EstadoSugestao, type Fila as FilaT, type Lote } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

const ORDEM: EstadoSugestao[] = ["DIVERGENTE", "INDETERMINADO", "SEM_EVIDENCIA", "INDISPONIVEL", "CONVERGENTE"];

export default function Fila() {
  const { id } = useParams();
  const { dados: lote } = useCarregar<Lote>(`/lotes/${id}/`);
  const { dados: fila, erro } = useCarregar<FilaT>(`/lotes/${id}/fila/`);
  if (erro) return <p className="erro">{erro}</p>;
  if (!fila) return <p className="suave">Carregando…</p>;
  const total = Object.values(fila.contagem).reduce((a, b) => a + (b ?? 0), 0);
  const finalizadas = fila.respostas.filter((r) => r.finalizada).length;

  return (
    <div className="grade">
      <h1>Correção — {lote?.titulo}</h1>
      <div className="cartao linha" style={{ gap: "1.25rem" }}>
        {ORDEM.filter((e) => fila.contagem[e]).map((e) => (
          <span key={e}>
            <span className={`selo ${e}`}>{ROTULO_ESTADO[e]}</span> {fila.contagem[e]}
          </span>
        ))}
        <span className="suave">
          {total} critérios avaliados (rodada {fila.rodada ?? "—"}) · {finalizadas}/{fila.respostas.length} respostas finalizadas
        </span>
      </div>
      <p className="suave">
        Respostas com algum critério não convergente vêm primeiro: nelas a pré-avaliação não oferece um nível único.
      </p>
      <table className="cartao">
        <thead>
          <tr>
            <th>Resposta</th>
            <th>Situação</th>
            <th>Critérios</th>
            <th className="num">Decididos</th>
          </tr>
        </thead>
        <tbody>
          {fila.respostas.map((r) => (
            <tr key={r.resposta}>
              <td>
                <Link to={`/lotes/${id}/respostas/${r.resposta}`}>{r.codigo}</Link>
              </td>
              <td>
                <span className={`selo ${r.estado_pior}`}>{ROTULO_ESTADO[r.estado_pior]}</span>
              </td>
              <td className="suave">
                {ORDEM.filter((e) => r.estados[e])
                  .map((e) => `${r.estados[e]} ${ROTULO_ESTADO[e].toLowerCase()}`)
                  .join(" · ")}
              </td>
              <td className="num">
                {r.finalizada ? <span className="ok">✓ finalizada</span> : `${r.n_decididos}/${r.n_criterios}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
