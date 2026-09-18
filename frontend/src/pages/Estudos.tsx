import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { chamar, ErroApi } from "../services/api";
import { useSessao } from "../services/auth";
import type { EstudoResumo, Lote } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

const ROTULO_STATUS = { PREPARACAO: "em preparação", EM_ANDAMENTO: "em andamento", ENCERRADO: "encerrado" };

export default function Estudos() {
  const { usuario } = useSessao();
  const navegar = useNavigate();
  const { dados: estudos } = useCarregar<EstudoResumo[]>("/estudos/");
  const pesquisador = usuario?.papel === "PESQUISADOR";
  const { dados: lotes } = useCarregar<Lote[]>(pesquisador ? "/lotes/" : null);
  const [titulo, setTitulo] = useState("");
  const [lote, setLote] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  async function criar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    try {
      const detalhe = await chamar<Lote>(`/lotes/${lote}/`);
      const rodada1 = detalhe.rodadas?.find((r) => r.numero === 1 && r.status === "CONCLUIDA");
      if (!rodada1) throw new ErroApi(400, "rodada", "O lote precisa ter a rodada 1 concluída.");
      const estudo = await chamar<EstudoResumo>("/estudos/", { corpo: { titulo, lote: Number(lote), rodada: rodada1.id } });
      navegar(`/estudos/${estudo.id}`);
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Não foi possível criar o estudo.");
    }
  }

  const criados = estudos?.filter((e) => e.papel === "PESQUISADOR") ?? [];
  const participo = estudos?.filter((e) => e.papel === "PARTICIPANTE") ?? [];

  return (
    <div className="grade">
      <h1>Estudos</h1>
      {participo.length > 0 && (
        <div className="cartao">
          <h3>Estudos de que participo</h3>
          <ul>
            {participo.map((e) => (
              <li key={e.id}>
                <Link to={`/estudos/${e.id}/participar`}>{e.titulo}</Link> <span className="suave">({ROTULO_STATUS[e.status]})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {pesquisador && (
        <>
          <div className="cartao">
            <h3>Estudos que coordeno</h3>
            {criados.length === 0 && <p className="suave">Nenhum ainda.</p>}
            <ul>
              {criados.map((e) => (
                <li key={e.id}>
                  <Link to={`/estudos/${e.id}`}>{e.titulo}</Link>{" "}
                  <span className="suave">
                    ({ROTULO_STATUS[e.status]} · lote {e.lote_titulo} · {e.n_participantes} participantes)
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <form className="cartao grade" onSubmit={criar}>
            <h3 style={{ margin: 0 }}>Novo estudo (protocolo A)</h3>
            <p className="suave" style={{ margin: 0 }}>
              O lote comum precisa ser seu e estar pré-avaliado. Cada participante corrigirá metade das respostas sem apoio e metade com
              apoio, com braços e ordem balanceados.
            </p>
            <label>
              Título
              <input value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
            </label>
            <label>
              Lote comum
              <select value={lote} onChange={(e) => setLote(e.target.value)} required>
                <option value="">Escolha…</option>
                {lotes?.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.titulo} ({l.n_respostas} respostas)
                  </option>
                ))}
              </select>
            </label>
            <div>
              <button className="primario">Criar estudo</button>
            </div>
            {erro && <p className="erro">{erro}</p>}
          </form>
        </>
      )}
      {!pesquisador && participo.length === 0 && <p className="suave">Você não participa de nenhum estudo.</p>}
    </div>
  );
}
