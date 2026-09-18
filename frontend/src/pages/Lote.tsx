import { Link, useParams } from "react-router-dom";
import { baixar } from "../services/api";
import { ROTULO_ESTADO, ROTULO_STATUS, type EstadoSugestao, type Fila, type Lote as LoteT, type RespostaResumo } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

export default function Lote() {
  const { id } = useParams();
  const { dados: lote, erro } = useCarregar<LoteT>(`/lotes/${id}/`);
  const { dados: respostas } = useCarregar<RespostaResumo[]>(`/lotes/${id}/respostas/`);
  const { dados: fila } = useCarregar<Fila>(`/lotes/${id}/fila/`);
  if (erro) return <p className="erro">{erro}</p>;
  if (!lote) return <p className="suave">Carregando…</p>;
  const rodadas = lote.rodadas ?? [];
  const concluida = rodadas.some((r) => r.status === "CONCLUIDA" || r.status === "COM_FALHAS");

  return (
    <div className="grade">
      <div>
        <h1>{lote.titulo}</h1>
        <p className="suave">
          Rubrica: {lote.rubrica_titulo} (v{lote.versao?.numero}) · N = {lote.n_execucoes} · limiar {lote.limiar_acordo} · modelo{" "}
          {lote.modelo_llm}
          {lote.sintetico && " · lote sintético"}
        </p>
      </div>
      <div className="cartao">
        <h3>Enunciado</h3>
        <p style={{ whiteSpace: "pre-wrap" }}>{lote.enunciado}</p>
      </div>
      <div className="cartao linha">
        {lote.n_respostas === 0 && (
          <Link to={`/lotes/${id}/importar`}>
            <button className="primario">Importar respostas</button>
          </Link>
        )}
        {lote.n_respostas > 0 && rodadas.length === 0 && (
          <Link to={`/lotes/${id}/rodada`}>
            <button className="primario">Pré-avaliar</button>
          </Link>
        )}
        {rodadas.map((r) => (
          <Link key={r.id} to={`/lotes/${id}/rodada`}>
            Rodada {r.numero}: {ROTULO_STATUS[r.status]}
          </Link>
        ))}
        {concluida && (
          <Link to={`/lotes/${id}/fila`}>
            <button className="primario">Corrigir</button>
          </Link>
        )}
        {concluida && (
          <Link to={`/lotes/${id}/painel`}>
            <button>Painel de consistência</button>
          </Link>
        )}
      </div>
      {concluida && fila && (
        <div className="cartao grade">
          <h3>Resumo da correção</h3>
          <div className="linha" style={{ gap: "1.25rem" }}>
            {(Object.keys(fila.contagem) as EstadoSugestao[]).map((e) => (
              <span key={e}>
                <span className={`selo ${e}`}>{ROTULO_ESTADO[e]}</span> {fila.contagem[e]}
              </span>
            ))}
          </div>
          <p style={{ margin: 0 }}>
            <strong>{fila.respostas.filter((r) => r.finalizada).length}</strong> de {fila.respostas.length} respostas finalizadas.
          </p>
          <div className="linha">
            <button onClick={() => baixar(`/lotes/${id}/notas.csv`, `notas-lote${id}.csv`)}>Baixar notas (CSV)</button>
            <span className="suave">Só respostas com todos os critérios decididos, identificadas pelo código.</span>
          </div>
        </div>
      )}
      {respostas && respostas.length > 0 && (
        <div className="cartao">
          <h3>Respostas ({respostas.length})</h3>
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th className="num">Caracteres</th>
                <th className="num">Dados removidos</th>
                <th>Aviso</th>
              </tr>
            </thead>
            <tbody>
              {respostas.map((r) => (
                <tr key={r.id}>
                  <td>{rodadas.length ? <Link to={`/respostas/${r.id}/execucoes`}>{r.codigo}</Link> : r.codigo}</td>
                  <td className="num">{r.n_caracteres}</td>
                  <td className="num">{r.n_substituicoes || ""}</td>
                  <td>{r.aviso ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
