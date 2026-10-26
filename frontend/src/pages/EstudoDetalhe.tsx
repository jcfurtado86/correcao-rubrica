import { useState } from "react";
import { useParams } from "react-router-dom";
import { baixar, chamar, ErroApi } from "../services/api";
import { ITENS_APOIO } from "../estudo/instrumentos";
import { ROTULO_CONDICAO, type EstudoResumo, type PainelEstudo } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

type Convite = { email: string; link: string | null; posicao: number };
type Alocacao = { metade_A: number; metade_B: number; participantes: { posicao: number; docente: string; braco: number; ordem: string }[] };

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);
const pp = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${Math.round(v * 100)} p.p.`);
const dec = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toFixed(2).replace(".", ","));
const seg = (ms: number | null | undefined) => (ms === null || ms === undefined ? "—" : `${Math.round(ms / 1000)} s`);

export default function EstudoDetalhe() {
  const { id } = useParams();
  const { dados: estudo, recarregar } = useCarregar<EstudoResumo>(`/estudos/${id}/`);
  const { dados: painel, recarregar: recarregarPainel } = useCarregar<PainelEstudo>(`/estudos/${id}/painel/`);
  const [emails, setEmails] = useState("");
  const [alocacao, setAlocacao] = useState<Alocacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [links, setLinks] = useState<Record<number, string>>({});
  const [copiado, setCopiado] = useState<number | null>(null);

  async function gerarLink(posicao: number) {
    setErro(null);
    try {
      const r = await chamar<{ link: string }>(`/estudos/${id}/participantes/${posicao}/link-senha/`, { metodo: "POST" });
      setLinks((atual) => ({ ...atual, [posicao]: r.link }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Falha ao gerar o link.");
    }
  }

  async function copiar(posicao: number) {
    try {
      await navigator.clipboard.writeText(links[posicao]);
      setCopiado(posicao);
    } catch {
      setErro("Não foi possível copiar. Selecione o link e copie manualmente.");
    }
  }

  async function convidar() {
    setErro(null);
    try {
      const lista = emails.split(/[\s,;]+/).filter(Boolean);
      const r = await chamar<{ convites: Convite[] }>(`/estudos/${id}/convites/`, { corpo: { emails: lista } });
      setLinks((atual) => ({ ...atual, ...Object.fromEntries(r.convites.filter((c) => c.link).map((c) => [c.posicao, c.link!])) }));
      setEmails("");
      recarregar();
      recarregarPainel();
    } catch (e) {
      setErro(e instanceof ErroApi ? `${e.message} ${e.campos ? JSON.stringify(e.campos) : ""}` : "Falha ao convidar.");
    }
  }

  async function iniciar() {
    setErro(null);
    try {
      setAlocacao(await chamar<Alocacao>(`/estudos/${id}/iniciar/`, { metodo: "POST" }));
      recarregar();
      recarregarPainel();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Falha ao iniciar.");
    }
  }

  if (!estudo) return <p className="suave">Carregando…</p>;

  return (
    <div className="grade">
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>{estudo.titulo}</h1>
        <button onClick={() => baixar(`/estudos/${id}/exportacao.zip`, `exportacao-estudo${id}.zip`)}>Exportar dados (ZIP)</button>
      </div>
      <p className="suave" style={{ margin: 0 }}>
        Lote comum: {estudo.lote_titulo} · rodada {estudo.rodada} · {estudo.n_participantes} participantes · status {estudo.status}
      </p>

      {estudo.status === "PREPARACAO" && (
        <div className="cartao linha" style={{ justifyContent: "space-between" }}>
          <span className="suave">
            Convide os docentes na tabela de participantes e inicie o estudo. Quem for convidado depois do início entra no próximo grupo do rodízio.
          </span>
          <button className="primario" onClick={iniciar} disabled={estudo.n_participantes === 0}>
            Iniciar estudo (aloca metades e braços)
          </button>
        </div>
      )}

      {alocacao && (
        <div className="cartao">
          <p className="ok" style={{ marginTop: 0 }}>
            Estudo iniciado: metade A com {alocacao.metade_A} respostas, metade B com {alocacao.metade_B}.
          </p>
        </div>
      )}

      {painel && estudo.status !== "PREPARACAO" && (
        <>
          <div className="kpis">
            <div className="kpi">
              <div className="valor">{pct(painel.cegos.exata)}</div>
              <div className="rotulo">concordância IA × docentes sem apoio</div>
              <div className="detalhe">n = {painel.cegos.n} · QWK {dec(painel.cegos.qwk)}</div>
            </div>
            <div className="kpi">
              <div className="valor">{pct(painel.assistidos.exata)}</div>
              <div className="rotulo">concordância IA × docentes com apoio</div>
              <div className="detalhe">n = {painel.assistidos.n} · QWK {dec(painel.assistidos.qwk)}</div>
            </div>
            <div className="kpi">
              <div className="valor">{pp(painel.ancoragem.exata)}</div>
              <div className="rotulo">efeito de ancoragem</div>
              <div className="detalhe">com apoio − sem apoio</div>
            </div>
            <div className="kpi">
              <div className="valor">{dec(painel.referencia_humana.cegos.alfa)}</div>
              <div className="rotulo">α de Krippendorff entre docentes sem apoio</div>
              <div className="detalhe">referência humana · {painel.referencia_humana.cegos.avaliadores} avaliadores</div>
            </div>
            <div className="kpi">
              <div className="valor">
                {seg(painel.tempo.SEM_APOIO.mediana_ms)} → {seg(painel.tempo.COM_APOIO.mediana_ms)}
              </div>
              <div className="rotulo">tempo mediano por resposta (sem → com apoio)</div>
              <div className="detalhe">
                diferença pareada {seg(painel.tempo.diferenca_pareada_mediana_ms)} · {painel.tempo.n_pareados} docentes
              </div>
            </div>
          </div>
        </>
      )}

      {painel && (
        <div className="cartao" style={{ overflowX: "auto" }}>
          <h3 style={{ marginTop: 0 }}>Participantes</h3>
          {painel.participantes.length === 0 && <p className="suave">Nenhum docente convidado ainda.</p>}
          {painel.participantes.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Participante</th>
                  <th>E-mail</th>
                  <th>Acesso</th>
                  <th>Braço</th>
                  <th>Ordem</th>
                  <th>Progresso</th>
                  <th>TCLE</th>
                  <th>Questionário</th>
                  <th className="num">Mediana sem apoio</th>
                  <th className="num">Mediana com apoio</th>
                </tr>
              </thead>
              <tbody>
                {painel.participantes.map((p) => (
                  <tr key={p.participante}>
                    <td>{p.participante}</td>
                    <td className="suave">{p.email}</td>
                    <td style={{ minWidth: "14rem" }}>
                      {p.posicao !== undefined && links[p.posicao] ? (
                        <div className="linha" style={{ flexWrap: "nowrap" }}>
                          <input readOnly value={links[p.posicao]} onFocus={(e) => e.target.select()} aria-label={`Link de senha de ${p.participante}`} />
                          <button onClick={() => copiar(p.posicao!)}>{copiado === p.posicao ? "Copiado" : "Copiar"}</button>
                        </div>
                      ) : (
                        <span className="linha" style={{ gap: "0.5rem" }}>
                          <span className="suave">{p.senha_definida ? "senha definida" : "sem senha"}</span>
                          {p.posicao !== undefined && (
                            <button className="link" onClick={() => gerarLink(p.posicao!)}>
                              {p.senha_definida ? "novo link de senha" : "gerar link"}
                            </button>
                          )}
                        </span>
                      )}
                    </td>
                    <td>{p.braco ?? "—"}</td>
                    <td>{p.ordem === "SEM_PRIMEIRO" ? "sem apoio primeiro" : p.ordem === "COM_PRIMEIRO" ? "com apoio primeiro" : "—"}</td>
                    <td>
                      {p.progresso.map((b) => `${ROTULO_CONDICAO[b.condicao]} ${b.feitas}/${b.total}`).join(" · ") || "—"}
                      {p.concluida && <span className="ok"> ✓</span>}
                    </td>
                    <td>
                      {p.consentimento ? <span className="ok">aceito</span> : <span className="suave">pendente</span>}
                      {p.consentimento && <span className="suave"> · imagem {p.autoriza_imagem ? "sim" : "não"}</span>}
                    </td>
                    <td>{p.questionario ? <span className="ok">respondido</span> : <span className="suave">—</span>}</td>
                    <td className="num">{seg(p.mediana_sem_apoio_ms)}</td>
                    <td className="num">{seg(p.mediana_com_apoio_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {estudo.status !== "ENCERRADO" && (
            <div className="linha" style={{ marginTop: "1rem", alignItems: "flex-end" }}>
              <label style={{ flex: 1 }}>
                Adicionar docentes
                <input
                  placeholder="e-mails separados por vírgula"
                  value={emails}
                  onChange={(e) => setEmails(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && emails.trim() && convidar()}
                  aria-label="E-mails dos participantes"
                />
              </label>
              <button onClick={convidar} disabled={!emails.trim()}>
                Convidar
              </button>
            </div>
          )}
          <p className="suave" style={{ marginBottom: 0, fontSize: "0.85rem" }}>
            Ao convidar, o link de senha do docente aparece na linha dele. Envie por WhatsApp ou mostre na tela; ele vale uma vez e expira em 3 dias.
            Gerar um link novo não muda a senha atual.
          </p>
        </div>
      )}

      {painel && estudo.status !== "PREPARACAO" && (
        <>
          <div className="cartao" style={{ overflowX: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Concordância por condição</h3>
            <table>
              <thead>
                <tr>
                  <th>Condição</th>
                  <th className="num">n</th>
                  <th className="num">Exata</th>
                  <th className="num">Adjacente</th>
                  <th className="num">QWK</th>
                  <th className="num">Exata em convergentes</th>
                  <th className="num">Exata em não convergentes</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["Sem apoio (cegos)", painel.cegos],
                    ["Com apoio (assistidos)", painel.assistidos],
                  ] as const
                ).map(([nome, r]) => (
                  <tr key={nome}>
                    <td>{nome}</td>
                    <td className="num">{r.n}</td>
                    <td className="num">{pct(r.exata)}</td>
                    <td className="num">{pct(r.adjacente)}</td>
                    <td className="num">{dec(r.qwk)}</td>
                    <td className="num">{pct(r.seletiva.exata_convergentes)}</td>
                    <td className="num">{pct(r.seletiva.exata_nao_convergentes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="cartao" style={{ overflowX: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Questionários (Instrumentos 4 e 5)</h3>
            <p style={{ marginTop: 0 }}>
              {painel.questionarios.respondidos} de {painel.participantes.length} respondidos · SUS médio{" "}
              <strong>{painel.questionarios.sus.media === null ? "—" : dec(painel.questionarios.sus.media)}</strong>
              {painel.questionarios.sus.dp !== null && <span className="suave"> (DP {dec(painel.questionarios.sus.dp)})</span>}
            </p>
            <table>
              <thead>
                <tr>
                  <th>Afirmação sobre o apoio (1 a 5)</th>
                  <th className="num">Média</th>
                  <th className="num">DP</th>
                </tr>
              </thead>
              <tbody>
                {painel.questionarios.apoio.map((a) => (
                  <tr key={a.item}>
                    <td>
                      {a.item}. {ITENS_APOIO[a.item - 1]}
                    </td>
                    <td className="num">{dec(a.media)}</td>
                    <td className="num">{dec(a.dp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="suave" style={{ marginBottom: 0, fontSize: "0.85rem" }}>
              As respostas abertas (B6 e B7) e os itens do SUS, por participante, estão em questionarios.csv no ZIP de exportação.
            </p>
          </div>
        </>
      )}
      {erro && <p className="erro">{erro}</p>}
    </div>
  );
}
