import { useState } from "react";
import { chamar, ErroApi } from "../services/api";
import { ESCALA_CONCORDANCIA, ITENS_APOIO, ITENS_SUS, PERFIL } from "./instrumentos";

type Respostas = Record<string, string | number>;

function Likert({ prefixo, itens, respostas, marcar }: { prefixo: string; itens: string[]; respostas: Respostas; marcar: (c: string, v: number) => void }) {
  return (
    <table className="likert">
      <thead>
        <tr>
          <th>Afirmação</th>
          {[1, 2, 3, 4, 5].map((v) => (
            <th key={v} title={ESCALA_CONCORDANCIA[v - 1]}>
              {v}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {itens.map((texto, i) => {
          const campo = `${prefixo}_${i + 1}`;
          return (
            <tr key={campo}>
              <td>
                {i + 1}. {texto}
              </td>
              {[1, 2, 3, 4, 5].map((v) => (
                <td key={v}>
                  <input
                    type="radio"
                    name={campo}
                    checked={respostas[campo] === v}
                    onChange={() => marcar(campo, v)}
                    aria-label={`${i + 1}. ${texto} — ${v}: ${ESCALA_CONCORDANCIA[v - 1]}`}
                  />
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

const LEGENDA = "Escala: 1 – Discordo totalmente; 2 – Discordo; 3 – Nem concordo nem discordo; 4 – Concordo; 5 – Concordo totalmente.";

// Instrumentos 4 (formulário do participante) e 5 (SUS), respondidos depois dos dois blocos.
export default function Questionario({ estudoId, participante, aoEnviar }: { estudoId: string; participante?: string; aoEnviar: () => void }) {
  const [r, setR] = useState<Respostas>({ o_que_ajudou: "", o_que_mudaria: "" });
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const marcar = (campo: string, valor: string | number) => setR((atual) => ({ ...atual, [campo]: valor }));

  const obrigatorios = [
    ...PERFIL.map((p) => p.campo),
    ...ITENS_APOIO.map((_, i) => `apoio_${i + 1}`),
    ...ITENS_SUS.map((_, i) => `sus_${i + 1}`),
  ];
  const faltam = obrigatorios.filter((c) => r[c] === undefined).length;

  async function enviar() {
    setEnviando(true);
    setErro(null);
    try {
      await chamar(`/estudos/${estudoId}/questionario/`, { corpo: r });
      aoEnviar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível enviar o questionário.");
      setEnviando(false);
    }
  }

  return (
    <div className="grade" style={{ maxWidth: "56rem" }}>
      <div className="cartao">
        <h1 style={{ marginTop: 0 }}>Questionário final</h1>
        <p style={{ marginBottom: 0 }}>
          Você concluiu os dois blocos. Para terminar, responda às perguntas abaixo{participante ? ` (participante ${participante})` : ""}. As
          respostas são enviadas uma única vez.
        </p>
      </div>

      <fieldset className="cartao grade">
        <legend>
          <strong>Parte A – Perfil</strong>
        </legend>
        {PERFIL.map((p, i) => (
          <div key={p.campo} role="radiogroup" aria-label={p.pergunta}>
            <div style={{ marginBottom: "0.35rem" }}>
              A{i + 1}. {p.pergunta}
            </div>
            <div className="linha">
              {p.opcoes.map(([valor, rotulo]) => (
                <label key={valor} className="linha" style={{ gap: "0.35rem" }}>
                  <input type="radio" name={p.campo} checked={r[p.campo] === valor} onChange={() => marcar(p.campo, valor)} />
                  {rotulo}
                </label>
              ))}
            </div>
          </div>
        ))}
      </fieldset>

      <fieldset className="cartao grade">
        <legend>
          <strong>Parte B – O apoio da ferramenta</strong>
        </legend>
        <Likert prefixo="apoio" itens={ITENS_APOIO} respostas={r} marcar={marcar} />
        <p className="suave" style={{ margin: 0, fontSize: "0.85rem" }}>
          {LEGENDA}
        </p>
        <label>
          B6. O que mais ajudou na correção com apoio?
          <textarea value={r.o_que_ajudou} onChange={(e) => marcar("o_que_ajudou", e.target.value)} />
        </label>
        <label>
          B7. O que você mudaria na ferramenta?
          <textarea value={r.o_que_mudaria} onChange={(e) => marcar("o_que_mudaria", e.target.value)} />
        </label>
      </fieldset>

      <fieldset className="cartao grade">
        <legend>
          <strong>Questionário de usabilidade (SUS)</strong>
        </legend>
        <p style={{ margin: 0 }}>
          Pense no uso que você acabou de fazer da ferramenta e marque, para cada afirmação, o quanto concorda. Responda a todas as afirmações,
          sem voltar às anteriores. Se não tiver certeza, marque 3.
        </p>
        <Likert prefixo="sus" itens={ITENS_SUS} respostas={r} marcar={marcar} />
        <p className="suave" style={{ margin: 0, fontSize: "0.85rem" }}>
          {LEGENDA}
        </p>
      </fieldset>

      {erro && <p className="erro">{erro}</p>}
      <div className="linha">
        <button className="primario" disabled={faltam > 0 || enviando} onClick={enviar}>
          Enviar respostas
        </button>
        {faltam > 0 && <span className="suave">Faltam {faltam} {faltam === 1 ? "pergunta" : "perguntas"} de múltipla escolha.</span>}
      </div>
    </div>
  );
}
