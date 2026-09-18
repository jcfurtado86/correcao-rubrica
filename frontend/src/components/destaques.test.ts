import { describe, expect, it } from "vitest";
import { segmentar } from "./destaques";

describe("segmentar", () => {
  it("texto sem destaque vira um segmento só", () => {
    expect(segmentar("abc def", [])).toEqual([{ texto: "abc def", inicio: 0, destaques: [] }]);
  });

  it("destaques adjacentes não se misturam", () => {
    const s = segmentar("aaabbb", [
      { inicio: 0, fim: 3, cor: 0, rotulo: "A" },
      { inicio: 3, fim: 6, cor: 1, rotulo: "B" },
    ]);
    expect(s.map((x) => [x.texto, x.destaques.map((d) => d.rotulo)])).toEqual([
      ["aaa", ["A"]],
      ["bbb", ["B"]],
    ]);
  });

  it("sobreposição gera segmento com os dois destaques", () => {
    const s = segmentar("0123456789", [
      { inicio: 2, fim: 6, cor: 0, rotulo: "A" },
      { inicio: 4, fim: 8, cor: 1, rotulo: "B" },
    ]);
    expect(s.map((x) => [x.texto, x.destaques.map((d) => d.rotulo).join("+")])).toEqual([
      ["01", ""],
      ["23", "A"],
      ["45", "A+B"],
      ["67", "B"],
      ["89", ""],
    ]);
  });

  it("ignora destaque fora do texto", () => {
    expect(segmentar("abc", [{ inicio: 2, fim: 9, cor: 0, rotulo: "X" }])).toHaveLength(1);
  });
});
