import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useSessao } from "./services/auth";
import Fila from "./pages/Fila";
import Importacao from "./pages/Importacao";
import Login from "./pages/Login";
import Lote from "./pages/Lote";
import LoteNovo from "./pages/LoteNovo";
import Painel from "./pages/Painel";
import Lotes from "./pages/Lotes";
import Resposta from "./pages/Resposta";
import RespostaInspecao from "./pages/RespostaInspecao";
import RubricaEditor from "./pages/RubricaEditor";
import Rubricas from "./pages/Rubricas";
import Rodada from "./pages/Rodada";

function Protegido() {
  const { usuario, carregando, logout } = useSessao();
  if (carregando) return <p className="centro suave">Carregando…</p>;
  if (!usuario) return <Navigate to="/entrar" replace />;
  return (
    <div className="app">
      <header className="topo">
        <strong>Correção Assistida por Rubrica</strong>
        <nav>
          <NavLink to="/rubricas">Rubricas</NavLink>
          <NavLink to="/lotes">Lotes</NavLink>
          {usuario.papel === "PESQUISADOR" && <NavLink to="/estudos">Estudos</NavLink>}
        </nav>
        <span className="suave">
          {usuario.nome || usuario.email} · <button className="link" onClick={logout}>sair</button>
        </span>
      </header>
      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/entrar" element={<Login />} />
      <Route element={<Protegido />}>
        <Route path="/" element={<Navigate to="/lotes" replace />} />
        <Route path="/rubricas" element={<Rubricas />} />
        <Route path="/rubricas/nova" element={<RubricaEditor />} />
        <Route path="/rubricas/:id" element={<RubricaEditor />} />
        <Route path="/lotes" element={<Lotes />} />
        <Route path="/lotes/novo" element={<LoteNovo />} />
        <Route path="/lotes/:id" element={<Lote />} />
        <Route path="/lotes/:id/importar" element={<Importacao />} />
        <Route path="/lotes/:id/rodada" element={<Rodada />} />
        <Route path="/lotes/:id/fila" element={<Fila />} />
        <Route path="/lotes/:id/painel" element={<Painel />} />
        <Route path="/lotes/:id/respostas/:rid" element={<Resposta />} />
        <Route path="/respostas/:id/execucoes" element={<RespostaInspecao />} />
        <Route path="*" element={<p>Página não encontrada.</p>} />
      </Route>
    </Routes>
  );
}
