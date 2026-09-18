import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import CartaoCriterio from "../components/CartaoCriterio";
import TextoComDestaques from "../components/TextoComDestaques";
import type { Destaque } from "../components/destaques";
import type { Fila, Lote, Sugestao, SugestoesDaResposta } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

function trechosDa(s: Sugestao) {
  if (s.trechos) return s.trechos;
  return (s.alternativas ?? []).flatMap((a) => a.trechos);
}

export default function Resposta() {
  const { id, rid } = useParams();
  const { dados: lote } = useCarregar<Lote>(`/lotes/${id}/`);
  const { dados, erro } = useCarregar<SugestoesDaResposta>(`/respostas/${rid}/sugestoes/`);
  const { dados: fila } = useCarregar<Fila>(`/lotes/${id}/fila/`);
  const [focado, setFocado] = useState<number | null>(null);

  const criterios = lote?.criterios ?? [];
  const destaques = useMemo<Destaque[]>(() => {
    if (!dados) return [];
    return dados.criterios.flatMap((s) => {
      const i = criterios.findIndex((c) => c.id === s.criterio);
      const nome = criterios[i]?.nome ?? "";
      return trechosDa(s).map((t) => ({ inicio: t.inicio, fim: t.fim, cor: i, rotulo: nome, ativo: focado === s.criterio }));
    });
  }, [dados, criterios, focado]);

  if (erro) return <p className="erro">{erro}</p>;
  if (!dados || !lote) return <p className="suave">Carregando…</p>;
  const posicao = fila?.respostas.findIndex((r) => String(r.resposta) === rid) ?? -1;
  const proxima = fila && posicao >= 0 ? fila.respostas[posicao + 1] : undefined;

  return (
    <div className="grade">
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>
          Resposta {dados.codigo}{" "}
          <span className="suave" style={{ fontSize: "1rem" }}>
            · {lote.titulo}
          </span>
        </h1>
        <div className="linha">
          <Link to={`/lotes/${id}/fila`}>Fila</Link>
          <Link to={`/respostas/${rid}/execucoes`}>Execuções</Link>
          {proxima && (
            <Link to={`/lotes/${id}/respostas/${proxima.resposta}`}>
              <button>Próxima da fila ({proxima.codigo})</button>
            </Link>
          )}
        </div>
      </div>
      <div className="duas-colunas">
        <div style={{ position: "sticky", top: "1rem" }}>
          <TextoComDestaques texto={dados.texto} destaques={destaques} />
        </div>
        <div className="grade">
          {criterios.map((c, i) => {
            const s = dados.criterios.find((x) => x.criterio === c.id);
            if (!s) return null;
            return <CartaoCriterio key={c.id} criterio={c} cor={i} sugestao={s} onFoco={(a) => setFocado(a ? c.id : null)} />;
          })}
        </div>
      </div>
    </div>
  );
}
