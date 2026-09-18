import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { baixar, chamar, ErroApi } from "../services/api";
import type { Rubrica, TipoCriterio } from "../services/tipos";

type NivelForm = { rotulo: string; pontuacao: string; descritor: string };
type CriterioForm = { nome: string; descricao: string; peso: string; tipo: TipoCriterio; niveis: NivelForm[] };

const NIVEIS_PADRAO: NivelForm[] = [
  { rotulo: "Insuficiente", pontuacao: "0", descritor: "" },
  { rotulo: "Parcial", pontuacao: "1", descritor: "" },
  { rotulo: "Adequado", pontuacao: "2", descritor: "" },
  { rotulo: "Excelente", pontuacao: "3", descritor: "" },
];

function novoCriterio(): CriterioForm {
  return { nome: "", descricao: "", peso: "1", tipo: "INTERPRETATIVO", niveis: NIVEIS_PADRAO.map((n) => ({ ...n })) };
}

export default function RubricaEditor() {
  const { id } = useParams();
  const navegar = useNavigate();
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [criterios, setCriterios] = useState<CriterioForm[]>([novoCriterio()]);
  const [versao, setVersao] = useState<{ numero: number; congelada: boolean } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!id) return;
    chamar<Rubrica>(`/rubricas/${id}/`).then((r) => {
      setTitulo(r.titulo);
      setDescricao(r.descricao);
      setVersao({ numero: r.versao.numero, congelada: r.versao.congelada });
      setCriterios(
        r.versao.criterios.map((c) => ({
          nome: c.nome,
          descricao: c.descricao,
          peso: String(c.peso),
          tipo: c.tipo,
          niveis: c.niveis.map((n) => ({ rotulo: n.rotulo, pontuacao: String(n.pontuacao), descritor: n.descritor })),
        })),
      );
    });
  }, [id]);

  const alterarCriterio = (i: number, parcial: Partial<CriterioForm>) =>
    setCriterios((cs) => cs.map((c, j) => (j === i ? { ...c, ...parcial } : c)));
  const alterarNivel = (i: number, k: number, parcial: Partial<NivelForm>) =>
    setCriterios((cs) =>
      cs.map((c, j) => (j === i ? { ...c, niveis: c.niveis.map((n, m) => (m === k ? { ...n, ...parcial } : n)) } : c)),
    );

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setMensagem(null);
    setSalvando(true);
    const corpo = { titulo, descricao, criterios };
    try {
      const r = await chamar<Rubrica>(id ? `/rubricas/${id}/` : "/rubricas/", { metodo: id ? "PUT" : "POST", corpo });
      navegar(`/rubricas/${r.id}`, { replace: true });
      setVersao({ numero: r.versao.numero, congelada: r.versao.congelada });
      setMensagem(`Rubrica salva (versão ${r.versao.numero}).`);
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Não foi possível salvar.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form onSubmit={salvar} className="grade">
      <div className="linha" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>{id ? "Editar rubrica" : "Nova rubrica"}</h1>
        {id && (
          <button type="button" onClick={() => baixar(`/rubricas/${id}/modelo/`, "modelo-rubrica.json")}>
            Exportar modelo
          </button>
        )}
      </div>
      {versao?.congelada && (
        <p className="alerta cartao">
          A versão {versao.numero} está em uso por um lote já pré-avaliado. Salvar cria a versão {versao.numero + 1};
          o lote continua ligado à versão antiga.
        </p>
      )}
      <div className="cartao grade">
        <label>
          Título
          <input value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
        </label>
        <label>
          Descrição
          <textarea value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </label>
      </div>

      {criterios.map((c, i) => (
        <fieldset key={i} className="cartao grade">
          <legend>
            <strong>Critério {i + 1}</strong>
          </legend>
          <div className="linha">
            <label style={{ flex: 3 }}>
              Nome
              <input value={c.nome} onChange={(e) => alterarCriterio(i, { nome: e.target.value })} required />
            </label>
            <label style={{ flex: 1 }}>
              Tipo
              <select value={c.tipo} onChange={(e) => alterarCriterio(i, { tipo: e.target.value as TipoCriterio })}>
                <option value="OBJETIVO">Objetivo</option>
                <option value="INTERPRETATIVO">Interpretativo</option>
              </select>
            </label>
            <label style={{ width: "6rem" }}>
              Peso
              <input type="number" min="0" step="any" value={c.peso} onChange={(e) => alterarCriterio(i, { peso: e.target.value })} />
            </label>
          </div>
          <label>
            Descrição do critério
            <textarea value={c.descricao} onChange={(e) => alterarCriterio(i, { descricao: e.target.value })} />
          </label>
          <table>
            <thead>
              <tr>
                <th>Nível</th>
                <th>Rótulo</th>
                <th style={{ width: "6rem" }}>Pontos</th>
                <th>Descritor (o que caracteriza este nível)</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {c.niveis.map((n, k) => (
                <tr key={k}>
                  <td>N{k + 1}</td>
                  <td>
                    <input value={n.rotulo} onChange={(e) => alterarNivel(i, k, { rotulo: e.target.value })} required />
                  </td>
                  <td>
                    <input type="number" step="any" value={n.pontuacao} onChange={(e) => alterarNivel(i, k, { pontuacao: e.target.value })} required />
                  </td>
                  <td>
                    <textarea value={n.descritor} onChange={(e) => alterarNivel(i, k, { descritor: e.target.value })} />
                  </td>
                  <td>
                    <button
                      type="button"
                      disabled={c.niveis.length <= 2}
                      title="Um critério precisa de ao menos 2 níveis"
                      onClick={() => alterarCriterio(i, { niveis: c.niveis.filter((_, m) => m !== k) })}
                    >
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="linha">
            <button
              type="button"
              onClick={() => alterarCriterio(i, { niveis: [...c.niveis, { rotulo: "", pontuacao: String(c.niveis.length), descritor: "" }] })}
            >
              Adicionar nível
            </button>
            <button
              type="button"
              className="perigo"
              disabled={criterios.length <= 1}
              onClick={() => setCriterios((cs) => cs.filter((_, j) => j !== i))}
            >
              Remover critério
            </button>
          </div>
        </fieldset>
      ))}
      <div className="linha">
        <button type="button" onClick={() => setCriterios((cs) => [...cs, novoCriterio()])}>
          Adicionar critério
        </button>
        <button className="primario" disabled={salvando}>
          {salvando ? "Salvando…" : "Salvar rubrica"}
        </button>
      </div>
      {erro && <p className="erro">{erro}</p>}
      {mensagem && <p className="ok">{mensagem}</p>}
    </form>
  );
}
