import { Link } from "react-router-dom";
import type { RubricaResumo } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

export default function Rubricas() {
  const { dados, erro, carregando } = useCarregar<RubricaResumo[]>("/rubricas/");
  return (
    <>
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1>Rubricas</h1>
        <Link to="/rubricas/nova">
          <button className="primario">Nova rubrica</button>
        </Link>
      </div>
      {erro && <p className="erro">{erro}</p>}
      {carregando && <p className="suave">Carregando…</p>}
      {dados && dados.length === 0 && <p className="suave">Nenhuma rubrica ainda. Crie a primeira.</p>}
      {dados && dados.length > 0 && (
        <table className="cartao">
          <thead>
            <tr>
              <th>Título</th>
              <th className="num">Critérios</th>
              <th>Versão</th>
            </tr>
          </thead>
          <tbody>
            {dados.map((r) => (
              <tr key={r.id}>
                <td>
                  <Link to={`/rubricas/${r.id}`}>{r.titulo}</Link>
                </td>
                <td className="num">{r.n_criterios}</td>
                <td>
                  v{r.versao_vigente.numero}
                  {r.versao_vigente.congelada && <span className="suave"> · em uso (congelada)</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
