import { segmentar, type Destaque } from "./destaques";

export default function TextoComDestaques({ texto, destaques }: { texto: string; destaques: Destaque[] }) {
  if (!texto)
    return (
      <div className="texto-resposta suave" data-testid="texto-resposta">
        (resposta vazia)
      </div>
    );
  return (
    <div className="texto-resposta" data-testid="texto-resposta">
      {segmentar(texto, destaques).map((s) => {
        if (s.destaques.length === 0) return <span key={s.inicio}>{s.texto}</span>;
        const principal = s.destaques[s.destaques.length - 1];
        const ativo = s.destaques.some((d) => d.ativo);
        return (
          <mark
            key={s.inicio}
            className={`cor-${principal.cor % 10}${ativo ? " ativo" : ""}`}
            title={s.destaques.map((d) => d.rotulo).join(" · ")}
          >
            {s.texto}
          </mark>
        );
      })}
    </div>
  );
}
