import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { chamar, ErroApi } from "../services/api";
import { ROTULO_STATUS, usd, type Estimativa, type Lote, type Rodada as RodadaT } from "../services/tipos";

export default function Rodada() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const reaplicacao = params.get("reaplicacao") === "1";
  const [lote, setLote] = useState<Lote | null>(null);
  const [estimativa, setEstimativa] = useState<Estimativa | null>(null);
  const [teto, setTeto] = useState("");
  const [rodada, setRodada] = useState<RodadaT | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    chamar<Lote>(`/lotes/${id}/`).then(async (l) => {
      setLote(l);
      const atual = l.rodadas && l.rodadas.length > 0 ? l.rodadas[l.rodadas.length - 1] : null;
      if (atual && !reaplicacao) {
        setRodada(await chamar<RodadaT>(`/rodadas/${atual.id}/`));
        return;
      }
      const e = await chamar<Estimativa>(`/lotes/${id}/rodadas/estimativa/`, { corpo: { reaplicacao } });
      setEstimativa(e);
      setTeto(String(Math.max(e.teto_usd, Math.ceil(e.custo_estimado_usd * 1.5 * 100) / 100)));
    });
  }, [id, reaplicacao]);

  useEffect(() => {
    if (!rodada || !["EM_EXECUCAO"].includes(rodada.status)) return;
    const t = setInterval(async () => setRodada(await chamar<RodadaT>(`/rodadas/${rodada.id}/`)), 3000);
    return () => clearInterval(t);
  }, [rodada]);

  async function confirmar() {
    setErro(null);
    try {
      setRodada(await chamar<RodadaT>(`/lotes/${id}/rodadas/`, { corpo: { confirmar: true, reaplicacao, teto_usd: teto } }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível iniciar.");
    }
  }

  async function retomar() {
    if (!rodada) return;
    setErro(null);
    try {
      setRodada(await chamar<RodadaT>(`/rodadas/${rodada.id}/retomar/`, { corpo: { teto_usd: teto || undefined } }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível retomar.");
    }
  }

  if (!lote) return <p className="suave">Carregando…</p>;

  if (rodada) {
    const feitas = rodada.total - rodada.pendentes;
    const pct = rodada.total ? Math.round((100 * feitas) / rodada.total) : 100;
    return (
      <div className="grade">
        <h1>
          {lote.titulo} — rodada {rodada.numero}
          {rodada.numero > 1 && " (reaplicação)"}
        </h1>
        <div className="cartao grade">
          <div className="linha">
            <span className={`selo ${rodada.status === "CONCLUIDA" ? "CONVERGENTE" : ""}`}>{ROTULO_STATUS[rodada.status]}</span>
            <span className="suave">
              {feitas} de {rodada.total} execuções · {rodada.invalidas} inválidas · {rodada.falhas} falhas
            </span>
          </div>
          <div className="barra" aria-label={`${pct}%`}>
            <span style={{ width: `${pct}%` }} />
          </div>
          <p className="suave">
            Custo até agora: {usd(rodada.custo_acumulado_usd)} (estimado {usd(rodada.custo_estimado_usd)}; teto {usd(rodada.teto_usd)}) ·
            modelo {rodada.modelo}
          </p>
          {rodada.status === "EM_EXECUCAO" && (
            <p className="suave">
              Parou de avançar?{" "}
              <button className="link" onClick={retomar}>
                Reenfileirar pendentes
              </button>{" "}
              (seguro: nada que já terminou é refeito).
            </p>
          )}
          {(rodada.status === "PAUSADA_TETO" || rodada.status === "COM_FALHAS") && (
            <div className="linha">
              <label>
                Novo teto (US$)
                <input type="number" min={0} step="any" value={teto} onChange={(e) => setTeto(e.target.value)} />
              </label>
              <button className="primario" onClick={retomar}>
                Retomar
              </button>
              <span className="suave">Execuções já concluídas não são refeitas.</span>
            </div>
          )}
        </div>
        {(rodada.status === "CONCLUIDA" || rodada.status === "COM_FALHAS") && (
          <div className="linha">
            <Link to={`/lotes/${id}/fila`}>
              <button className="primario">Ir para a correção</button>
            </Link>
            <Link to={`/lotes/${id}`}>Voltar ao lote</Link>
          </div>
        )}
        {erro && <p className="erro">{erro}</p>}
      </div>
    );
  }

  return (
    <div className="grade">
      <h1>{reaplicacao ? "Reaplicar pré-avaliação" : "Pré-avaliar"} — {lote.titulo}</h1>
      {!estimativa && <p className="suave">Calculando estimativa…</p>}
      {estimativa && (
        <div className="cartao grade">
          <p>
            <strong>{estimativa.n_chamadas.toLocaleString("pt-BR")} chamadas</strong> ao modelo ({estimativa.respostas_elegiveis}{" "}
            respostas × {estimativa.criterios} critérios × {estimativa.n_execucoes} execuções).
          </p>
          <p>
            Custo estimado: <strong>{usd(estimativa.custo_estimado_usd)}</strong>{" "}
            <span className="suave">
              ({estimativa.preco_vigente.modelo}: {usd(estimativa.preco_vigente.entrada_por_milhao)} por milhão de tokens de entrada e{" "}
              {usd(estimativa.preco_vigente.saida_por_milhao)} de saída; saída estimada pela{" "}
              {estimativa.base_saida === "observada" ? "média observada neste lote" : "configuração, a partir do piloto"})
            </span>
          </p>
          {reaplicacao && (
            <p className="suave">
              A reaplicação é uma rodada nova e independente, com sementes novas, para medir a estabilidade do julgamento.
            </p>
          )}
          <label style={{ maxWidth: 240 }}>
            Teto de custo desta rodada (US$)
            <input type="number" min={0} step="any" value={teto} onChange={(e) => setTeto(e.target.value)} />
          </label>
          <div>
            <button className="primario" onClick={confirmar} disabled={estimativa.n_chamadas === 0 && !lote.avisos}>
              Confirmar e executar
            </button>
          </div>
        </div>
      )}
      {erro && <p className="erro">{erro}</p>}
    </div>
  );
}
