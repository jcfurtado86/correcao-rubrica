import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { chamar, ErroApi } from "../services/api";
import { usd, type Lote, type RubricaResumo } from "../services/tipos";

type Modelo = { provedor: string; modelo: string; rotulo: string; entrada_por_milhao: number; saida_por_milhao: number };
import { useCarregar } from "../services/useCarregar";

export default function LoteNovo() {
  const navegar = useNavigate();
  const { dados: rubricas } = useCarregar<RubricaResumo[]>("/rubricas/");
  const { dados: modelos } = useCarregar<Modelo[]>("/modelos/");
  const [form, setForm] = useState({
    titulo: "",
    enunciado: "",
    versao_rubrica: "",
    n_execucoes: "5",
    limiar_acordo: "0.8",
    min_validas: "3",
    teto_usd: "10",
    sintetico: false,
    modelo: "",
  });
  const [erro, setErro] = useState<string | null>(null);
  const alterar = (parcial: Partial<typeof form>) => setForm((f) => ({ ...f, ...parcial }));

  async function criar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    try {
      const escolhido = modelos?.find((m) => `${m.provedor}|${m.modelo}` === form.modelo);
      const { modelo: _ignorado, ...resto } = form;
      const lote = await chamar<Lote>("/lotes/", {
        corpo: {
          ...resto,
          ...(escolhido ? { provedor_llm: escolhido.provedor, modelo_llm: escolhido.modelo } : {}),
          versao_rubrica: Number(form.versao_rubrica),
          n_execucoes: Number(form.n_execucoes),
          min_validas: Number(form.min_validas),
        },
      });
      navegar(`/lotes/${lote.id}/importar`);
    } catch (err) {
      setErro(err instanceof ErroApi ? `${err.message} ${err.campos ? JSON.stringify(err.campos) : ""}` : "Erro ao criar.");
    }
  }

  return (
    <form className="grade" onSubmit={criar}>
      <h1>Novo lote</h1>
      <div className="cartao grade">
        <label>
          Título
          <input value={form.titulo} onChange={(e) => alterar({ titulo: e.target.value })} placeholder="ESI 2026.2 — Questão 3" required />
        </label>
        <label>
          Enunciado da questão
          <textarea value={form.enunciado} onChange={(e) => alterar({ enunciado: e.target.value })} required />
        </label>
        <label>
          Rubrica
          <select value={form.versao_rubrica} onChange={(e) => alterar({ versao_rubrica: e.target.value })} required>
            <option value="">Escolha…</option>
            {rubricas?.map((r) => (
              <option key={r.id} value={r.versao_vigente.id}>
                {r.titulo} (v{r.versao_vigente.numero})
              </option>
            ))}
          </select>
        </label>
        <label>
          Modelo de linguagem
          <select value={form.modelo} onChange={(e) => alterar({ modelo: e.target.value })}>
            <option value="">Padrão do servidor</option>
            {modelos?.map((m) => (
              <option key={`${m.provedor}|${m.modelo}`} value={`${m.provedor}|${m.modelo}`}>
                {m.rotulo}
                {m.saida_por_milhao > 0 ? ` — ${usd(m.entrada_por_milhao)} / ${usd(m.saida_por_milhao)} por milhão de tokens` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="linha">
          <input type="checkbox" checked={form.sintetico} onChange={(e) => alterar({ sintetico: e.target.checked })} />
          Lote sintético (dados de teste, sem estudante real)
        </label>
      </div>
      <details className="cartao">
        <summary>Parâmetros da pré-avaliação</summary>
        <div className="linha" style={{ marginTop: "0.75rem" }}>
          <label>
            Execuções por critério (N)
            <input type="number" min={1} max={10} value={form.n_execucoes} onChange={(e) => alterar({ n_execucoes: e.target.value })} />
          </label>
          <label>
            Limiar de acordo
            <input type="number" min={0.51} max={1} step="any" value={form.limiar_acordo} onChange={(e) => alterar({ limiar_acordo: e.target.value })} />
          </label>
          <label>
            Mínimo de execuções válidas
            <input type="number" min={1} value={form.min_validas} onChange={(e) => alterar({ min_validas: e.target.value })} />
          </label>
          <label>
            Teto de custo (US$)
            <input type="number" min={0} step="any" value={form.teto_usd} onChange={(e) => alterar({ teto_usd: e.target.value })} />
          </label>
        </div>
        <p className="suave">
          Com N = 5 e limiar 0,8, um critério só é “convergente” se ao menos 4 das 5 execuções válidas escolherem o mesmo nível.
        </p>
      </details>
      <div>
        <button className="primario">Criar e importar respostas</button>
      </div>
      {erro && <p className="erro">{erro}</p>}
    </form>
  );
}
