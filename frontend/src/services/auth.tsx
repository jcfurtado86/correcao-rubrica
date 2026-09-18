import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { chamar, entrar, sair, temSessao } from "./api";

export type Usuario = { id: number; email: string; nome: string; papel: "DOCENTE" | "PESQUISADOR" };

type Sessao = {
  usuario: Usuario | null;
  carregando: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
};

const Contexto = createContext<Sessao | null>(null);

export function ProvedorDeSessao({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    if (!temSessao()) {
      setUsuario(null);
      setCarregando(false);
      return;
    }
    try {
      setUsuario(await chamar<Usuario>("/auth/me/"));
    } catch {
      sair();
      setUsuario(null);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const login = async (email: string, senha: string) => {
    await entrar(email, senha);
    await carregar();
  };
  const logout = () => {
    sair();
    setUsuario(null);
  };

  return <Contexto.Provider value={{ usuario, carregando, login, logout }}>{children}</Contexto.Provider>;
}

export function useSessao(): Sessao {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useSessao fora do ProvedorDeSessao");
  return ctx;
}
