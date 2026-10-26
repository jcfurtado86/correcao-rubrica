import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useSessao } from "./services/auth";
import type { EstudoResumo } from "./services/tipos";
import { useCarregar } from "./services/useCarregar";
import DefinirSenha from "./pages/DefinirSenha";
import EstudoDetalhe from "./pages/EstudoDetalhe";
import Estudos from "./pages/Estudos";
import Fila from "./pages/Fila";
import Importacao from "./pages/Importacao";
import Login from "./pages/Login";
import Lote from "./pages/Lote";
import LoteNovo from "./pages/LoteNovo";
import Painel from "./pages/Painel";
import Participacao from "./pages/Participacao";
import Lotes from "./pages/Lotes";
import Resposta from "./pages/Resposta";
import RespostaInspecao from "./pages/RespostaInspecao";
import RubricaEditor from "./pages/RubricaEditor";
import Rubricas from "./pages/Rubricas";
import Rodada from "./pages/Rodada";

// Docente convidado para um estudo ainda aberto: a ferramenta mostra só o estudo,
// para que o participante não se perca em Rubricas e Lotes durante a oficina.
function estudosAtivos(estudos: EstudoResumo[] | null) {
  return (estudos ?? []).filter((e) => e.papel === "PARTICIPANTE" && e.status !== "ENCERRADO");
}

function Inicio() {
  const { usuario } = useSessao();
  const pesquisador = usuario?.papel === "PESQUISADOR";
  const { dados: estudos, erro } = useCarregar<EstudoResumo[]>(pesquisador ? null : "/estudos/");
  if (pesquisador || erro) return <Navigate to="/lotes" replace />;
  if (!estudos) return <p className="centro suave">Carregando…</p>;
  const ativos = estudosAtivos(estudos);
  if (ativos.length === 1) return <Navigate to={`/estudos/${ativos[0].id}/participar`} replace />;
  return <Navigate to={ativos.length > 1 ? "/estudos" : "/lotes"} replace />;
}

function Protegido() {
  const { usuario, carregando, logout } = useSessao();
  const pesquisador = usuario?.papel === "PESQUISADOR";
  const { dados: estudos } = useCarregar<EstudoResumo[]>(usuario && !pesquisador ? "/estudos/" : null);
  const soEstudo = !pesquisador && estudosAtivos(estudos).length > 0;
  if (carregando) return <p className="centro suave">Carregando…</p>;
  if (!usuario) return <Navigate to="/entrar" replace />;
  return (
    <div className="app">
      <header className="topo">
        <strong>Correção Assistida por Rubrica</strong>
        <nav>
          {!soEstudo && <NavLink to="/rubricas">Rubricas</NavLink>}
          {!soEstudo && <NavLink to="/lotes">Lotes</NavLink>}
          <NavLink to="/estudos">Estudos</NavLink>
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
      <Route path="/definir-senha/:uid/:token" element={<DefinirSenha />} />
      <Route element={<Protegido />}>
        <Route path="/" element={<Inicio />} />
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
        <Route path="/estudos" element={<Estudos />} />
        <Route path="/estudos/:id" element={<EstudoDetalhe />} />
        <Route path="/estudos/:id/participar" element={<Participacao />} />
        <Route path="*" element={<p>Página não encontrada.</p>} />
      </Route>
    </Routes>
  );
}
