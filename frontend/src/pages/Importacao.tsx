import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { chamar, ErroApi, salvarBlob } from "../services/api";

type Previa = { colunas: string[]; amostra: string[][]; total_linhas: number };
type Resultado = {
  n_respostas: number;
  avisos: { codigo: string; tipo: string }[];
  chave_reidentificacao: { nome_arquivo: string; conteudo_base64: string } | null;
};

const ROTULO_AVISO: Record<string, string> = {
  VAZIA: "vazia (fica como “sem evidência”)",
  LONGA: "acima do limite (fica para correção manual, sem pré-avaliação)",
  DUPLICADA: "texto idêntico ao de outra resposta",
};

function baixarChave(chave: NonNullable<Resultado["chave_reidentificacao"]>) {
  const bytes = Uint8Array.from(atob(chave.conteudo_base64), (c) => c.charCodeAt(0));
  salvarBlob(new Blob([bytes], { type: "text/csv" }), chave.nome_arquivo);
}

export default function Importacao() {
  const { id } = useParams();
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [previa, setPrevia] = useState<Previa | null>(null);
  const [colunaResposta, setColunaResposta] = useState("");
  const [colunasId, setColunasId] = useState<string[]>([]);
  const [gerarChave, setGerarChave] = useState(true);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function carregarPrevia(f: File) {
    setArquivo(f);
    setErro(null);
    const dados = new FormData();
    dados.append("arquivo", f);
    try {
      const p = await chamar<Previa>(`/lotes/${id}/importacao/previa/`, { formulario: dados });
      setPrevia(p);
      const provavel = p.colunas.find((c) => /resposta/i.test(c)) ?? "";
      setColunaResposta(provavel);
      setColunasId(p.colunas.filter((c) => /nome|e-?mail|matr|identifica|usu[aá]rio|cpf/i.test(c) && c !== provavel));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível ler o arquivo.");
    }
  }

  async function importar(e: FormEvent) {
    e.preventDefault();
    if (!arquivo) return;
    setEnviando(true);
    setErro(null);
    const dados = new FormData();
    dados.append("arquivo", arquivo);
    dados.append("coluna_resposta", colunaResposta);
    colunasId.forEach((c) => dados.append("colunas_identificacao", c));
    dados.append("gerar_chave", String(gerarChave));
    try {
      const r = await chamar<Resultado>(`/lotes/${id}/importacao/`, { formulario: dados });
      setResultado(r);
      if (r.chave_reidentificacao) baixarChave(r.chave_reidentificacao);
    } catch (err) {
      setErro(err instanceof ErroApi ? err.message : "Falha na importação.");
    } finally {
      setEnviando(false);
    }
  }

  if (resultado) {
    return (
      <div className="grade">
        <h1>Respostas importadas</h1>
        <div className="cartao">
          <p className="ok">
            {resultado.n_respostas} respostas carregadas e anonimizadas. Nenhum nome, e-mail ou matrícula foi guardado.
          </p>
          {resultado.chave_reidentificacao && (
            <p className="alerta">
              A chave de reidentificação (código ↔ estudante) foi baixada agora.{" "}
              <strong>Guarde este arquivo. Ele não poderá ser gerado de novo.</strong>{" "}
              <button className="link" onClick={() => baixarChave(resultado.chave_reidentificacao!)}>
                Baixar de novo
              </button>
            </p>
          )}
          {resultado.avisos.length > 0 && (
            <>
              <h3>Avisos</h3>
              <ul>
                {resultado.avisos.map((a) => (
                  <li key={a.codigo + a.tipo}>
                    {a.codigo}: {ROTULO_AVISO[a.tipo] ?? a.tipo}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
        <div className="linha">
          <Link to={`/lotes/${id}/rodada`}>
            <button className="primario">Pré-avaliar</button>
          </Link>
          <Link to={`/lotes/${id}`}>Ver o lote</Link>
        </div>
      </div>
    );
  }

  return (
    <form className="grade" onSubmit={importar}>
      <h1>Importar respostas</h1>
      <div className="cartao grade">
        <p className="suave">
          Planilha CSV ou XLSX, uma linha por estudante (ex.: relatório de respostas do questionário do Moodle). O arquivo é
          lido em memória e não é guardado.
        </p>
        <input type="file" accept=".csv,.xlsx" onChange={(e) => e.target.files?.[0] && carregarPrevia(e.target.files[0])} />
      </div>
      {previa && (
        <>
          <div className="cartao" style={{ overflowX: "auto" }}>
            <h3>Prévia ({previa.total_linhas} linhas)</h3>
            <table>
              <thead>
                <tr>
                  {previa.colunas.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previa.amostra.map((linha, i) => (
                  <tr key={i}>
                    {linha.map((v, j) => (
                      <td key={j}>{v.length > 80 ? v.slice(0, 80) + "…" : v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="cartao grade">
            <label>
              Coluna com a resposta do estudante
              <select value={colunaResposta} onChange={(e) => setColunaResposta(e.target.value)} required>
                <option value="">Escolha…</option>
                {previa.colunas.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <fieldset>
              <legend>Colunas de identificação (serão descartadas e removidas dos textos)</legend>
              {previa.colunas
                .filter((c) => c !== colunaResposta)
                .map((c) => (
                  <label key={c} className="linha">
                    <input
                      type="checkbox"
                      checked={colunasId.includes(c)}
                      onChange={(e) => setColunasId((cs) => (e.target.checked ? [...cs, c] : cs.filter((x) => x !== c)))}
                    />
                    {c}
                  </label>
                ))}
            </fieldset>
            <label className="linha">
              <input type="checkbox" checked={gerarChave} onChange={(e) => setGerarChave(e.target.checked)} />
              Gerar chave de reidentificação (baixada uma única vez; o sistema não guarda cópia)
            </label>
          </div>
          <div>
            <button className="primario" disabled={enviando || !colunaResposta || colunasId.length === 0}>
              {enviando ? "Importando…" : "Importar e anonimizar"}
            </button>
          </div>
        </>
      )}
      {erro && <p className="erro">{erro}</p>}
    </form>
  );
}
