import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useSessao } from "../services/auth";

export default function Login() {
  const { login } = useSessao();
  const navegar = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await login(email, senha);
      navegar("/");
    } catch {
      setErro("E-mail ou senha incorretos.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="login">
      <form className="cartao" onSubmit={enviar}>
        <h1>Correção Assistida por Rubrica</h1>
        <p className="suave">Entre com a conta criada pelo pesquisador ou pelo convite recebido.</p>
        <label>
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Senha
          <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required />
        </label>
        {erro && <p className="erro">{erro}</p>}
        <button className="primario" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
