// Tempo ativo de correção (research R11, FR-020).
// Conta enquanto a aba está visível; para 60 s depois da última interação
// (teclado, mouse, rolagem) e volta a contar na interação seguinte. O relógio é
// injetável para os testes.

export const LIMITE_OCIOSO_MS = 60_000;

export class CronometroAtivo {
  private acumulado = 0;
  private inicio: number | null = null;
  private ultimaAtividade = 0;
  private visivel = true;

  constructor(
    private agora: () => number = () => performance.now(),
    private limiteOciosoMs = LIMITE_OCIOSO_MS,
  ) {}

  iniciar() {
    this.acumulado = 0;
    this.visivel = true;
    this.abrir(this.agora());
  }

  atividade() {
    const t = this.agora();
    this.fecharSeOcioso(t);
    if (this.inicio === null && this.visivel) this.abrir(t);
    this.ultimaAtividade = t;
  }

  ocultar() {
    this.fechar(this.agora());
    this.visivel = false;
  }

  mostrar() {
    this.visivel = true;
    this.atividade();
  }

  parar() {
    this.fechar(this.agora());
    this.visivel = false;
  }

  acumuladoMs(): number {
    const t = this.agora();
    this.fecharSeOcioso(t);
    return Math.round(this.acumulado + (this.inicio === null ? 0 : t - this.inicio));
  }

  private abrir(t: number) {
    this.inicio = t;
    this.ultimaAtividade = t;
  }

  private fechar(t: number) {
    if (this.inicio === null) return;
    const fim = Math.min(t, this.ultimaAtividade + this.limiteOciosoMs);
    this.acumulado += Math.max(0, fim - this.inicio);
    this.inicio = null;
  }

  private fecharSeOcioso(t: number) {
    if (this.inicio !== null && t - this.ultimaAtividade > this.limiteOciosoMs) this.fechar(t);
  }
}

// Liga o cronômetro aos eventos do navegador. Devolve a função que desliga.
export function ligarAoNavegador(c: CronometroAtivo): () => void {
  const atividade = () => c.atividade();
  const visibilidade = () => (document.hidden ? c.ocultar() : c.mostrar());
  const eventos = ["keydown", "mousemove", "mousedown", "wheel", "touchstart", "scroll"];
  eventos.forEach((e) => window.addEventListener(e, atividade, { passive: true }));
  document.addEventListener("visibilitychange", visibilidade);
  return () => {
    eventos.forEach((e) => window.removeEventListener(e, atividade));
    document.removeEventListener("visibilitychange", visibilidade);
  };
}
