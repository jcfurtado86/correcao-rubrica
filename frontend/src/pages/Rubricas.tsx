import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { chamar, ErroApi } from "../services/api";
import type { Rubrica, RubricaResumo } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

export default function Rubricas() {
  const { dados, erro, carregando } = useCarregar<RubricaResumo[]>("/rubricas/");
  const navegar = useNavigate();
  const [erroImportacao, setErroImportacao] = useState<string | null>(null);

  async function importarModelo(arquivo: File) {
    setErroImportacao(null);
    const formulario = new FormData();
    formulario.append("arquivo", arquivo);
    try {
      const r = await chamar<Rubrica>("/rubricas/importar-modelo/", { formulario });
      navegar(`/rubricas/${r.id}`);
    } catch (e) {
      setErroImportacao(e instanceof ErroApi ? e.message : "Não foi possível importar o modelo.");
    }
  }
  return (
    <>
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1>Rubricas</h1>
        <div className="linha">
          <label className="linha" style={{ cursor: "pointer" }}>
            <span className="suave">Importar modelo (JSON)</span>
            <input
              type="file"
              accept=".json,application/json"
              aria-label="Importar modelo de rubrica"
              onChange={(e) => e.target.files?.[0] && importarModelo(e.target.files[0])}
            />
          </label>
          <Link to="/rubricas/nova">
            <button className="primario">Nova rubrica</button>
          </Link>
        </div>
      </div>
      {erroImportacao && <p className="erro">{erroImportacao}</p>}
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
