import { useState, type ReactNode } from "react";

export type EstadoDica = { x: number; y: number; conteudo: ReactNode } | null;

// Dica compartilhada por um gráfico. Os valores também estão nos rótulos e na
// tabela de métricas: a dica enriquece, nunca é o único caminho (skill dataviz).
export function useDica() {
  const [dica, setDica] = useState<EstadoDica>(null);
  function props(conteudo: ReactNode, rotulo: string) {
    const mostrar = (el: HTMLElement) => {
      const caixa = el.getBoundingClientRect();
      const pai = el.closest(".grafico")?.getBoundingClientRect();
      if (!pai) return;
      setDica({ x: caixa.left - pai.left + caixa.width / 2, y: caixa.top - pai.top, conteudo });
    };
    return {
      tabIndex: 0,
      "aria-label": rotulo,
      onMouseEnter: (e: React.MouseEvent<HTMLElement>) => mostrar(e.currentTarget),
      onFocus: (e: React.FocusEvent<HTMLElement>) => mostrar(e.currentTarget),
      onMouseLeave: () => setDica(null),
      onBlur: () => setDica(null),
    };
  }
  const elemento = dica ? (
    <div className="dica" style={{ left: dica.x, top: dica.y - 8, transform: "translate(-50%, -100%)" }} role="status">
      {dica.conteudo}
    </div>
  ) : null;
  return { props, elemento };
}
