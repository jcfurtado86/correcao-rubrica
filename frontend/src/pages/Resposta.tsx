import { useCallback } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import PainelDeCorrecao from "../components/PainelDeCorrecao";
import { chamar } from "../services/api";
import type { Fila, Lote, Sessao } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

export default function Resposta() {
  const { id, rid } = useParams();
  const navegar = useNavigate();
  const { dados: lote } = useCarregar<Lote>(`/lotes/${id}/`);
  const { dados: fila, recarregar } = useCarregar<Fila>(`/lotes/${id}/fila/`);
  const abrirSessao = useCallback(() => chamar<Sessao>(`/respostas/${rid}/sessoes/`, { metodo: "POST" }), [rid]);

  if (!lote?.criterios) return <p className="suave">Carregando…</p>;
  const itens = fila?.respostas ?? [];
  const posicao = itens.findIndex((r) => String(r.resposta) === rid);
  const proxima = [...itens.slice(posicao + 1), ...itens.slice(0, Math.max(posicao, 0))].find((r) => !r.finalizada);

  return (
    <div className="grade">
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>
          Resposta {itens[posicao]?.codigo ?? ""}{" "}
          <span className="suave" style={{ fontSize: "1rem" }}>
            · {lote.titulo}
          </span>
        </h1>
        <div className="linha">
          <Link to={`/lotes/${id}/fila`}>Fila</Link>
          <Link to={`/respostas/${rid}/execucoes`}>Execuções</Link>
        </div>
      </div>
      <PainelDeCorrecao
        key={rid}
        criterios={lote.criterios}
        abrirSessao={abrirSessao}
        caminhoHistorico={`/respostas/${rid}/historico/`}
        aoFinalizar={recarregar}
        proxima={
          proxima ? (
            <button onClick={() => navegar(`/lotes/${id}/respostas/${proxima.resposta}`)}>Próxima da fila ({proxima.codigo})</button>
          ) : (
            <Link to={`/lotes/${id}`}>Todas finalizadas — voltar ao lote</Link>
          )
        }
      />
    </div>
  );
}
