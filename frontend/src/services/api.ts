// Cliente da API: JWT no cabeçalho, renovação automática e erro no formato
// {detail, codigo} de contracts/api.md.

const CHAVE_ACESSO = "cr.acesso";
const CHAVE_RENOVACAO = "cr.renovacao";

export class ErroApi extends Error {
  constructor(
    public status: number,
    public codigo: string,
    mensagem: string,
    public campos?: Record<string, unknown>,
  ) {
    super(mensagem);
  }
}

function ler(chave: string): string | null {
  try {
    return localStorage.getItem(chave);
  } catch {
    return null;
  }
}

export function guardarTokens(acesso: string | null, renovacao: string | null) {
  try {
    if (acesso) localStorage.setItem(CHAVE_ACESSO, acesso);
    else localStorage.removeItem(CHAVE_ACESSO);
    if (renovacao) localStorage.setItem(CHAVE_RENOVACAO, renovacao);
    else localStorage.removeItem(CHAVE_RENOVACAO);
  } catch {
    /* navegador sem armazenamento: a sessão dura só enquanto a aba estiver aberta */
  }
}

export function temSessao(): boolean {
  return Boolean(ler(CHAVE_ACESSO));
}

async function renovar(): Promise<boolean> {
  const renovacao = ler(CHAVE_RENOVACAO);
  if (!renovacao) return false;
  const r = await fetch("/api/auth/token/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: renovacao }),
  });
  if (!r.ok) {
    guardarTokens(null, null);
    return false;
  }
  const dados = await r.json();
  guardarTokens(dados.access, dados.refresh ?? renovacao);
  return true;
}

type Opcoes = { metodo?: string; corpo?: unknown; formulario?: FormData; bruto?: boolean };

export async function chamar<T = unknown>(caminho: string, opcoes: Opcoes = {}, tentouRenovar = false): Promise<T> {
  const cabecalhos: Record<string, string> = {};
  const acesso = ler(CHAVE_ACESSO);
  if (acesso) cabecalhos.Authorization = `Bearer ${acesso}`;
  let corpo: BodyInit | undefined;
  if (opcoes.formulario) corpo = opcoes.formulario;
  else if (opcoes.corpo !== undefined) {
    cabecalhos["Content-Type"] = "application/json";
    corpo = JSON.stringify(opcoes.corpo);
  }
  const resposta = await fetch(`/api${caminho}`, {
    method: opcoes.metodo ?? (corpo ? "POST" : "GET"),
    headers: cabecalhos,
    body: corpo,
  });
  if (resposta.status === 401 && !tentouRenovar && (await renovar())) {
    return chamar<T>(caminho, opcoes, true);
  }
  if (!resposta.ok) {
    let dados: { detail?: string; codigo?: string; campos?: Record<string, unknown> } = {};
    try {
      dados = await resposta.json();
    } catch {
      /* corpo não é JSON */
    }
    throw new ErroApi(resposta.status, dados.codigo ?? "erro", dados.detail ?? `Erro ${resposta.status}`, dados.campos);
  }
  if (opcoes.bruto) return (await resposta.blob()) as T;
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

export async function baixar(caminho: string, nomeArquivo: string) {
  const blob = await chamar<Blob>(caminho, { bruto: true });
  salvarBlob(blob, nomeArquivo);
}

export function salvarBlob(blob: Blob, nomeArquivo: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomeArquivo;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function entrar(email: string, senha: string) {
  const r = await fetch("/api/auth/token/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: senha }),
  });
  if (!r.ok) throw new ErroApi(r.status, "login", "E-mail ou senha incorretos.");
  const dados = await r.json();
  guardarTokens(dados.access, dados.refresh);
}

export function sair() {
  guardarTokens(null, null);
}
