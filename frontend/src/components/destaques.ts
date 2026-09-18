// Divide o texto em segmentos para destacar trechos que podem se sobrepor.

export type Destaque = { inicio: number; fim: number; cor: number; rotulo: string; ativo?: boolean };
export type Segmento = { texto: string; inicio: number; destaques: Destaque[] };

export function segmentar(texto: string, destaques: Destaque[]): Segmento[] {
  const validos = destaques.filter((d) => d.inicio >= 0 && d.fim > d.inicio && d.fim <= texto.length);
  const cortes = new Set<number>([0, texto.length]);
  for (const d of validos) {
    cortes.add(d.inicio);
    cortes.add(d.fim);
  }
  const pontos = [...cortes].sort((a, b) => a - b);
  const segmentos: Segmento[] = [];
  for (let i = 0; i < pontos.length - 1; i++) {
    const inicio = pontos[i];
    const fim = pontos[i + 1];
    if (fim <= inicio) continue;
    segmentos.push({
      texto: texto.slice(inicio, fim),
      inicio,
      destaques: validos.filter((d) => d.inicio <= inicio && d.fim >= fim),
    });
  }
  return segmentos;
}
