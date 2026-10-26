import { API } from "../services/api";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

export default function DefinirSenha() {
  const { uid, token } = useParams();
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    if (senha !== confirmacao) {
      setErro("As senhas não conferem.");
      return;
    }
    const r = await fetch(`${API}/auth/definir-senha/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid, token, senha }),
    });
    const dados = await r.json().catch(() => ({}));
    if (!r.ok) setErro(dados.detail ?? "Não foi possível definir a senha.");
    else setEmail(dados.email);
  }

  return (
    <main className="login">
      {email ? (
        <div className="cartao">
          <h1>Senha definida</h1>
          <p>
            Entre com <strong>{email}</strong> e a senha que você acabou de criar.
          </p>
          <Link to="/entrar">
            <button className="primario">Entrar</button>
          </Link>
        </div>
      ) : (
        <form className="cartao" onSubmit={enviar}>
          <h1>Definir senha</h1>
          <p className="suave">Você foi convidada(o) para um estudo de correção assistida por rubrica.</p>
          <label>
            Nova senha
            <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={8} autoFocus />
          </label>
          <label>
            Confirme a senha
            <input type="password" value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} required />
          </label>
          {erro && <p className="erro">{erro}</p>}
          <button className="primario">Salvar senha</button>
        </form>
      )}
    </main>
  );
}
