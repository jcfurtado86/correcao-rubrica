import { Link, useParams, useSearchParams } from "react-router-dom";
import BarrasAgrupadas from "../components/graficos/BarrasAgrupadas";
import BarrasEmpilhadas from "../components/graficos/BarrasEmpilhadas";
import { baixar } from "../services/api";
import { ROTULO_ESTADO, usd, type BlocoPainel, type Lote, type Painel as PainelT } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);
const dec = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toFixed(2).replace(".", ","));
const tempo = (ms: number | null | undefined) => (ms === null || ms === undefined ? "—" : `${(ms / 1000).toFixed(0)} s`);

const SERIES_SELETIVA = [
  { chave: "conv", nome: "Itens convergentes", cor: "var(--serie-1)" },
  { chave: "nconv", nome: "Itens não convergentes (divergente, sem evidência, indeterminado)", cor: "var(--serie-2)" },
];
const SERIES_ESTADOS = [
  { chave: "CONVERGENTE", nome: ROTULO_ESTADO.CONVERGENTE, cor: "var(--serie-1)" },
  { chave: "DIVERGENTE", nome: ROTULO_ESTADO.DIVERGENTE, cor: "var(--serie-2)" },
  { chave: "SEM_EVIDENCIA", nome: ROTULO_ESTADO.SEM_EVIDENCIA, cor: "var(--serie-3)" },
  { chave: "INDETERMINADO", nome: ROTULO_ESTADO.INDETERMINADO, cor: "var(--serie-4)" },
];

function Kpi({ valor, rotulo, detalhe }: { valor: string; rotulo: string; detalhe?: string }) {
  return (
    <div className="kpi">
      <div className="valor">{valor}</div>
      <div className="rotulo">{rotulo}</div>
      {detalhe && <div className="detalhe">{detalhe}</div>}
    </div>
  );
}

function LinhaTabela({ nome, tipo, b }: { nome: string; tipo?: string; b: BlocoPainel }) {
  return (
    <tr>
      <td>
        {nome} {tipo && <span className="suave">({tipo === "OBJETIVO" ? "obj." : "interp."})</span>}
      </td>
      <td className="num">{b.n_pares}</td>
      <td className="suave" style={{ whiteSpace: "nowrap" }}>
        {(["CONVERGENTE", "DIVERGENTE", "SEM_EVIDENCIA", "INDETERMINADO"] as const)
          .map((e) => `${ROTULO_ESTADO[e].slice(0, 4).toLowerCase()}. ${b.estados[e] ?? 0}`)
          .join(" · ")}
      </td>
      <td className="num">{pct(b.taxa_divergencia)}</td>
      <td className="num">{pct(b.taxa_nao_convergente)}</td>
      <td className="num">{dec(b.acordo_medio)}</td>
      <td className="num">{dec(b.fleiss)}</td>
      <td className="num">
        {pct(b.concordancia.exata)} <span className="suave">n={b.concordancia.n}</span>
      </td>
      <td className="num">{pct(b.concordancia.adjacente)}</td>
      <td className="num">{dec(b.concordancia.qwk)}</td>
      <td className="num">{pct(b.seletiva.exata_convergentes)}</td>
      <td className="num">{pct(b.seletiva.exata_nao_convergentes)}</td>
      <td className="num">{b.estabilidade ? pct(b.estabilidade.exata) : "—"}</td>
      <td className="num">{b.estabilidade ? dec(b.estabilidade.qwk) : "—"}</td>
      <td className="suave">
        {Object.entries(b.distribuicao_decidida)
          .map(([k, v]) => `${k}:${v}`)
          .join(" ")}
      </td>
    </tr>
  );
}

export default function Painel() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const rodada = params.get("rodada") ?? "";
  const limiar = params.get("limiar") ?? "";
  const consulta = new URLSearchParams();
  if (rodada) consulta.set("rodada", rodada);
  if (limiar) consulta.set("limiar", limiar);
  const { dados: lote } = useCarregar<Lote>(`/lotes/${id}/`);
  const { dados: painel, erro, carregando } = useCarregar<PainelT>(`/lotes/${id}/painel/?${consulta}`);

  const mudar = (chave: string, valor: string) => {
    const novos = new URLSearchParams(params);
    if (valor) novos.set(chave, valor);
    else novos.delete(chave);
    setParams(novos);
  };

  if (erro) return <p className="erro">{erro}</p>;
  if (!painel || !lote) return <p className="suave">Carregando…</p>;
  if (painel.rodada === null) return <p className="suave">Este lote ainda não foi pré-avaliado.</p>;
  const t = painel.total;

  return (
    <div className="grade" style={{ opacity: carregando ? 0.6 : 1 }}>
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>Painel de consistência — {lote.titulo}</h1>
        <div className="linha">
          {painel.rodadas.length === 1 && (
            <Link to={`/lotes/${id}/rodada?reaplicacao=1`}>
              <button>Reaplicar lote</button>
            </Link>
          )}
          <button onClick={() => baixar(`/lotes/${id}/exportacao.zip`, `exportacao-lote${id}.zip`)}>Exportar dados (ZIP)</button>
        </div>
      </div>

      <div className="cartao linha">
        <label>
          Rodada
          <select value={rodada || String(painel.rodada)} onChange={(e) => mudar("rodada", e.target.value)}>
            {painel.rodadas.map((r) => (
              <option key={r} value={r}>
                {r === 1 ? "1 (original)" : `${r} (reaplicação)`}
              </option>
            ))}
          </select>
        </label>
        <label>
          Limiar de acordo
          <select value={limiar} onChange={(e) => mudar("limiar", e.target.value)}>
            <option value="">{String(lote.limiar_acordo).replace(".", ",")} (do lote)</option>
            {["0.6", "0.8", "1"]
              .filter((v) => Number(v) !== lote.limiar_acordo)
              .map((v) => (
                <option key={v} value={v}>
                  {v.replace(".", ",")} (sensibilidade)
                </option>
              ))}
          </select>
        </label>
        <span className="suave">
          {painel.recalculado
            ? "Estados recalculados só para esta visão, a partir das execuções gravadas. Nada é alterado."
            : `Modelo ${painel.modelo} · custo da rodada ${usd(painel.custo.acumulado_usd)}`}
        </span>
      </div>

      <div className="kpis">
        <Kpi valor={String(t.n_pares)} rotulo="pares resposta × critério" />
        <Kpi valor={pct(t.taxa_divergencia)} rotulo="divergência sinalizada" detalhe={`${pct(t.taxa_nao_convergente)} não convergentes`} />
        <Kpi valor={pct(t.concordancia.exata)} rotulo="concordância exata com a docente" detalhe={`n = ${t.concordancia.n} · adjacente ${pct(t.concordancia.adjacente)}`} />
        <Kpi valor={dec(t.concordancia.qwk)} rotulo="κ ponderado (QWK)" />
        <Kpi
          valor={t.estabilidade ? pct(t.estabilidade.exata) : "—"}
          rotulo="estabilidade entre rodadas"
          detalhe={t.estabilidade ? `n = ${t.estabilidade.n} · QWK ${dec(t.estabilidade.qwk)}` : "reaplique o lote para medir"}
        />
        <Kpi valor={tempo(painel.tempo.mediana_ms)} rotulo="tempo mediano por resposta" detalhe={`${painel.tempo.n_respostas} respostas corrigidas`} />
      </div>

      <section className="cartao grade">
        <div>
          <h2 style={{ marginTop: 0 }}>Concordância com a docente: convergentes × não convergentes</h2>
          <p className="suave" style={{ margin: 0 }}>
            Hipótese do trabalho (SC-008a): quando as execuções convergem, a pré-avaliação concorda mais com a decisão docente. Nos não
            convergentes, compara-se o nível modal, que não é exibido à docente.
          </p>
        </div>
        <BarrasAgrupadas
          titulo="Concordância exata por critério, convergentes e não convergentes"
          series={SERIES_SELETIVA}
          categorias={[...painel.criterios.map((c) => ({ nome: c.nome, b: c as BlocoPainel })), { nome: "Total", b: t }].map(({ nome, b }) => ({
            nome,
            valores: {
              conv: { valor: b.seletiva.exata_convergentes, n: b.seletiva.n_convergentes },
              nconv: { valor: b.seletiva.exata_nao_convergentes, n: b.seletiva.n_nao_convergentes },
            },
          }))}
        />
      </section>

      <section className="cartao grade">
        <h2 style={{ margin: 0 }}>Estados da pré-avaliação por critério</h2>
        <BarrasEmpilhadas
          titulo="Distribuição dos estados por critério"
          series={SERIES_ESTADOS}
          pilhas={[
            ...painel.criterios.map((c) => ({ nome: `${c.nome} (${c.tipo === "OBJETIVO" ? "obj." : "interp."})`, contagens: c.estados as Record<string, number> })),
            { nome: "Total", contagens: t.estados as Record<string, number> },
          ]}
        />
        <p className="suave" style={{ margin: 0 }}>
          Por tipo de critério — objetivo: {pct(painel.por_tipo.OBJETIVO?.taxa_divergencia)} de divergência; interpretativo:{" "}
          {pct(painel.por_tipo.INTERPRETATIVO?.taxa_divergencia)}.
        </p>
      </section>

      <section className="cartao" style={{ overflowX: "auto" }}>
        <h2 style={{ marginTop: 0 }}>Todas as métricas</h2>
        <table>
          <thead>
            <tr>
              <th>Critério</th>
              <th className="num">Pares</th>
              <th>Estados</th>
              <th className="num">Diverg.</th>
              <th className="num">Não conv.</th>
              <th className="num">Acordo médio</th>
              <th className="num">κ Fleiss</th>
              <th className="num">Exata</th>
              <th className="num">Adjacente</th>
              <th className="num">QWK</th>
              <th className="num">Exata conv.</th>
              <th className="num">Exata não conv.</th>
              <th className="num">Estab. exata</th>
              <th className="num">Estab. QWK</th>
              <th>Níveis decididos</th>
            </tr>
          </thead>
          <tbody>
            {painel.criterios.map((c) => (
              <LinhaTabela key={c.criterio} nome={c.nome} tipo={c.tipo} b={c} />
            ))}
            <LinhaTabela nome="Total" b={t} />
          </tbody>
        </table>
        <p className="suave" style={{ fontSize: "0.85rem" }}>
          Concordância: nível modal da rodada × decisão vigente da docente (fora de estudo). Pares com modal “sem evidência” ficam fora das
          medidas ordinais. Estabilidade: modal da rodada original × modal da reaplicação. Exportação: dados brutos e script{" "}
          <code>analysis/reproduzir_metricas.py</code>, que recalcula estes números.
        </p>
      </section>
    </div>
  );
}
