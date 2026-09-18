import { describe, expect, it } from "vitest";
import { CronometroAtivo } from "./tempoAtivo";

function relogio() {
  let t = 0;
  return { agora: () => t, avancar: (ms: number) => (t += ms) };
}

describe("CronometroAtivo", () => {
  it("conta com a aba visível e em atividade", () => {
    const r = relogio();
    const c = new CronometroAtivo(r.agora);
    c.iniciar();
    r.avancar(10_000);
    c.atividade();
    r.avancar(5_000);
    expect(c.acumuladoMs()).toBe(15_000);
  });

  it("pausa quando a aba fica oculta e retoma ao voltar", () => {
    const r = relogio();
    const c = new CronometroAtivo(r.agora);
    c.iniciar();
    r.avancar(3_000);
    c.ocultar();
    r.avancar(100_000);
    c.mostrar();
    r.avancar(2_000);
    expect(c.acumuladoMs()).toBe(5_000);
  });

  it("para de contar 60 s depois da última interação", () => {
    const r = relogio();
    const c = new CronometroAtivo(r.agora);
    c.iniciar();
    r.avancar(10_000);
    c.atividade();
    r.avancar(300_000);
    expect(c.acumuladoMs()).toBe(70_000);
  });

  it("retoma com nova interação depois de ocioso", () => {
    const r = relogio();
    const c = new CronometroAtivo(r.agora);
    c.iniciar();
    r.avancar(200_000); // 60 s contam, o resto não
    c.atividade();
    r.avancar(4_000);
    expect(c.acumuladoMs()).toBe(64_000);
  });

  it("parar congela o valor", () => {
    const r = relogio();
    const c = new CronometroAtivo(r.agora);
    c.iniciar();
    r.avancar(1_000);
    c.parar();
    r.avancar(9_000);
    expect(c.acumuladoMs()).toBe(1_000);
  });
});
