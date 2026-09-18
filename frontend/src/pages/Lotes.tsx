import { Link } from "react-router-dom";
import type { Lote } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

export default function Lotes() {
  const { dados, erro, carregando } = useCarregar<Lote[]>("/lotes/");
  return (
    <>
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1>Lotes</h1>
        <Link to="/lotes/novo">
          <button className="primario">Novo lote</button>
        </Link>
      </div>
      {erro && <p className="erro">{erro}</p>}
      {carregando && <p className="suave">Carregando…</p>}
      {dados && dados.length === 0 && (
        <p className="suave">
          Nenhum lote ainda. Um lote é uma questão discursiva com sua rubrica e as respostas da turma.
        </p>
      )}
      {dados && dados.length > 0 && (
        <table className="cartao">
          <thead>
            <tr>
              <th>Lote</th>
              <th>Rubrica</th>
              <th className="num">Respostas</th>
              <th>Modelo</th>
            </tr>
          </thead>
          <tbody>
            {dados.map((l) => (
              <tr key={l.id}>
                <td>
                  <Link to={`/lotes/${l.id}`}>{l.titulo}</Link>
                  {l.sintetico && <span className="selo" style={{ marginLeft: 8 }}>sintético</span>}
                </td>
                <td>{l.rubrica_titulo}</td>
                <td className="num">{l.n_respostas}</td>
                <td className="suave">{l.modelo_llm}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
