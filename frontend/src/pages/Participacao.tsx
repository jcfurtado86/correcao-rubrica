import { useCallback } from "react";
import { useParams } from "react-router-dom";
import PainelDeCorrecao from "../components/PainelDeCorrecao";
import { chamar } from "../services/api";
import { ROTULO_CONDICAO, type Criterio, type EstudoResumo, type Sessao, type Tarefa } from "../services/tipos";
import { useCarregar } from "../services/useCarregar";

export default function Participacao() {
  const { id } = useParams();
  const { dados: estudo } = useCarregar<EstudoResumo>(`/estudos/${id}/`);
  const { dados: tarefa, recarregar } = useCarregar<Tarefa>(`/estudos/${id}/minha-tarefa/`);
  const rid = tarefa?.proxima_resposta?.id;
  const { dados: criterios } = useCarregar<Criterio[]>(rid ? `/estudos/${id}/criterios/` : null);
  const abrirSessao = useCallback(
    () => chamar<Sessao>(`/estudos/${id}/respostas/${rid}/sessoes/`, { metodo: "POST" }),
    [id, rid],
  );

  if (!estudo || !tarefa) return <p className="suave">Carregando…</p>;
  if (!tarefa.iniciado) return <p className="suave">O estudo “{estudo.titulo}” ainda não começou. Volte quando o pesquisador iniciar.</p>;
  if (tarefa.concluido)
    return (
      <div className="cartao">
        <h1>Obrigado!</h1>
        <p>Você concluiu as duas etapas do estudo “{estudo.titulo}”.</p>
      </div>
    );
  const bloco = tarefa.bloco_atual!;
  const progresso = tarefa.progresso?.find((p) => p.bloco === bloco.numero);

  return (
    <div className="grade">
      <div className={`faixa-bloco ${bloco.condicao}`} data-testid="faixa-bloco">
        Bloco {bloco.numero} de {bloco.de}: {ROTULO_CONDICAO[bloco.condicao]}
        {progresso && (
          <span className="suave" style={{ fontWeight: 400 }}>
            {" "}
            · {progresso.feitas} de {progresso.total} respostas
          </span>
        )}
      </div>
      <h1 style={{ margin: 0 }}>
        Resposta {tarefa.proxima_resposta?.codigo} <span className="suave" style={{ fontSize: "1rem" }}>· {estudo.titulo}</span>
      </h1>
      {criterios && rid && (
        <PainelDeCorrecao
          key={rid}
          criterios={criterios}
          abrirSessao={abrirSessao}
          proximaSoAoFinalizar
          proxima={<button onClick={recarregar}>Próxima resposta</button>}
        />
      )}
    </div>
  );
}
