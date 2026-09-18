import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { chamar, ErroApi } from "../services/api";
import { CronometroAtivo, ligarAoNavegador } from "../services/tempoAtivo";
import { ROTULO_TIPO, type Criterio, type DecisaoT, type Sessao, type Sugestao } from "../services/tipos";
import CartaoCriterio from "./CartaoCriterio";
import TextoComDestaques from "./TextoComDestaques";
import type { Destaque } from "./destaques";

type Props = {
  criterios: Criterio[];
  abrirSessao: () => Promise<Sessao>;
  caminhoHistorico?: string; // ausente no estudo (participante não vê histórico)
  aoFinalizar?: () => void;
  proxima?: React.ReactNode;
};

const BATIDA_MS = 30_000;

function trechosDa(s: Sugestao) {
  if (s.trechos) return s.trechos;
  return (s.alternativas ?? []).flatMap((a) => a.trechos);
}

export default function PainelDeCorrecao({ criterios, abrirSessao, caminhoHistorico, aoFinalizar, proxima }: Props) {
  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [vigentes, setVigentes] = useState<Record<number, DecisaoT>>({});
  const [motivos, setMotivos] = useState<Record<number, string>>({});
  const [foco, setFoco] = useState(0);
  const [hover, setHover] = useState<number | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [historico, setHistorico] = useState<DecisaoT[] | null>(null);
  const cronometro = useRef(new CronometroAtivo());
  const finalizadaAntes = useRef(false);

  useEffect(() => {
    let ativo = true;
    let desligar = () => {};
    let batida: ReturnType<typeof setInterval> | undefined;
    abrirSessao()
      .then((s) => {
        if (!ativo) return;
        setSessao(s);
        setVigentes(Object.fromEntries(s.decisoes_vigentes.map((d) => [d.criterio, d])));
        finalizadaAntes.current = s.decisoes_vigentes.length === criterios.length;
        cronometro.current.iniciar();
        desligar = ligarAoNavegador(cronometro.current);
        batida = setInterval(() => {
          chamar(`/sessoes/${s.sessao}/`, { metodo: "PATCH", corpo: { tempo_ativo_ms: cronometro.current.acumuladoMs() } }).catch(() => {});
        }, BATIDA_MS);
      })
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível abrir a resposta."));
    return () => {
      ativo = false;
      desligar();
      if (batida) clearInterval(batida);
      cronometro.current.parar();
    };
  }, [abrirSessao, criterios.length]);

  const sugestaoDe = useCallback((criterioId: number) => sessao?.criterios.find((s) => s.criterio === criterioId), [sessao]);

  const decidir = useCallback(
    async (criterio: Criterio, nivelId: number) => {
      if (!sessao) return;
      setErro(null);
      try {
        const d = await chamar<DecisaoT>(`/sessoes/${sessao.sessao}/decisoes/`, {
          corpo: {
            criterio: criterio.id,
            nivel: nivelId,
            motivo: motivos[criterio.id] ?? "",
            tempo_ativo_ms: cronometro.current.acumuladoMs(),
          },
        });
        setVigentes((v) => ({ ...v, [criterio.id]: d }));
        // O motivo vale só para esta decisão; a próxima começa em branco.
        setMotivos((m) => ({ ...m, [criterio.id]: "" }));
        setHistorico(null);
        const idx = criterios.findIndex((c) => c.id === criterio.id);
        if (idx < criterios.length - 1) setFoco(idx + 1);
      } catch (e) {
        setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar a decisão.");
      }
    },
    [sessao, motivos, criterios],
  );

  const finalizada = criterios.length > 0 && criterios.every((c) => vigentes[c.id]);
  useEffect(() => {
    if (finalizada && !finalizadaAntes.current) {
      finalizadaAntes.current = true;
      aoFinalizar?.();
    }
  }, [finalizada, aoFinalizar]);

  // Atalhos: ↑/↓ muda o critério; 1–9 escolhe o nível; Enter confirma a sugestão convergente.
  useEffect(() => {
    function tecla(e: KeyboardEvent) {
      const alvo = e.target as HTMLElement;
      if (alvo && ["INPUT", "TEXTAREA", "SELECT"].includes(alvo.tagName)) return;
      const criterio = criterios[foco];
      if (!criterio) return;
      if (e.key === "ArrowDown") setFoco((f) => Math.min(f + 1, criterios.length - 1));
      else if (e.key === "ArrowUp") setFoco((f) => Math.max(f - 1, 0));
      else if (/^[1-9]$/.test(e.key)) {
        const nivel = criterio.niveis.find((n) => n.ordem === Number(e.key));
        if (nivel) decidir(criterio, nivel.id);
      } else if (e.key === "Enter") {
        const s = sugestaoDe(criterio.id);
        if (s?.estado === "CONVERGENTE" && s.nivel_sugerido?.id) decidir(criterio, s.nivel_sugerido.id);
      } else return;
      e.preventDefault();
    }
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [criterios, foco, decidir, sugestaoDe]);

  const destaques = useMemo<Destaque[]>(() => {
    if (!sessao) return [];
    return sessao.criterios.flatMap((s) => {
      const i = criterios.findIndex((c) => c.id === s.criterio);
      const ativo = hover === s.criterio || criterios[foco]?.id === s.criterio;
      return trechosDa(s).map((t) => ({ inicio: t.inicio, fim: t.fim, cor: i, rotulo: criterios[i]?.nome ?? "", ativo }));
    });
  }, [sessao, criterios, hover, foco]);

  async function abrirHistorico() {
    if (!caminhoHistorico) return;
    setHistorico(await chamar<DecisaoT[]>(caminhoHistorico));
  }

  if (erro && !sessao) return <p className="erro">{erro}</p>;
  if (!sessao) return <p className="suave">Abrindo resposta…</p>;

  return (
    <div className="grade">
      {sessao.condicao === "SEM_APOIO" && (
        <div className="faixa-bloco SEM_APOIO">Condição sem apoio: corrija sem sugestão da pré-avaliação.</div>
      )}
      <div className="duas-colunas">
        <div style={{ position: "sticky", top: "1rem" }} className="grade">
          <TextoComDestaques texto={sessao.texto} destaques={destaques} />
          <p className="suave" style={{ fontSize: "0.85rem" }}>
            <kbd>↑</kbd> <kbd>↓</kbd> critério · <kbd>1</kbd>–<kbd>9</kbd> nível
            {sessao.condicao === "COM_APOIO" && (
              <>
                {" "}
                · <kbd>Enter</kbd> confirma a sugestão convergente
              </>
            )}
          </p>
          {finalizada && (
            <div className="cartao linha" data-testid="finalizada">
              <span className="ok">✓ Resposta finalizada: todos os critérios decididos.</span>
              {proxima}
            </div>
          )}
          {!finalizada && proxima}
          {erro && <p className="erro">{erro}</p>}
        </div>
        <div className="grade">
          {criterios.map((c, i) => {
            const s = sugestaoDe(c.id);
            if (!s) return null;
            const decidida = vigentes[c.id];
            const sugerido = s.estado === "CONVERGENTE" ? s.nivel_sugerido : null;
            return (
              <div key={c.id} onClick={() => setFoco(i)} style={{ outline: foco === i ? "2px solid var(--primaria)" : "none", borderRadius: 8 }}>
                <CartaoCriterio criterio={c} cor={i} sugestao={s} onFoco={(a) => setHover(a ? c.id : null)}>
                  <div className="linha" role="group" aria-label={`Níveis de ${c.nome}`}>
                    {sugerido?.id && (
                      <button className="primario" onClick={() => decidir(c, sugerido.id!)} title="Enter">
                        Confirmar {sugerido.codigo}
                      </button>
                    )}
                    {c.niveis.map((n) => (
                      <button
                        key={n.id}
                        className={decidida?.nivel === n.id ? "selecionado" : ""}
                        onClick={() => decidir(c, n.id)}
                        title={n.descritor}
                        aria-pressed={decidida?.nivel === n.id}
                      >
                        <kbd>{n.ordem}</kbd> {n.codigo} {n.rotulo}
                      </button>
                    ))}
                  </div>
                  <input
                    placeholder="Motivo (opcional)"
                    value={motivos[c.id] ?? ""}
                    onChange={(e) => setMotivos((m) => ({ ...m, [c.id]: e.target.value }))}
                  />
                  {decidida && (
                    <p className="ok" style={{ margin: 0, fontSize: "0.9rem" }} data-testid={`decidido-${c.id}`}>
                      Decidido: {decidida.nivel_codigo} ({ROTULO_TIPO[decidida.tipo]})
                    </p>
                  )}
                </CartaoCriterio>
              </div>
            );
          })}
          {caminhoHistorico && (
            <details className="cartao" onToggle={(e) => (e.currentTarget as HTMLDetailsElement).open && abrirHistorico()}>
              <summary>Histórico de decisões</summary>
              {historico && historico.length === 0 && <p className="suave">Nenhuma decisão ainda.</p>}
              {historico && historico.length > 0 && (
                <table>
                  <tbody>
                    {historico.map((d) => (
                      <tr key={d.id} style={{ opacity: d.vigente ? 1 : 0.6 }}>
                        <td>{criterios.find((c) => c.id === d.criterio)?.nome}</td>
                        <td>
                          {d.nivel_codigo} {!d.vigente && <span className="suave">(substituída)</span>}
                        </td>
                        <td className="suave">{ROTULO_TIPO[d.tipo]}</td>
                        <td className="suave">{d.motivo}</td>
                        <td className="suave">{new Date(d.criado_em).toLocaleString("pt-BR")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
