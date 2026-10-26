import { useState } from "react";
import { chamar, ErroApi } from "../services/api";

// Instrumento 2 – Termo de consentimento livre e esclarecido, aceito antes do primeiro bloco.
export default function Termo({ estudoId, nRespostas, aoAceitar }: { estudoId: string; nRespostas: number; aoAceitar: () => void }) {
  const [aceito, setAceito] = useState(false);
  const [imagem, setImagem] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function confirmar() {
    setEnviando(true);
    setErro(null);
    try {
      await chamar(`/estudos/${estudoId}/consentimento/`, { corpo: { aceito: true, autoriza_imagem: imagem } });
      aoAceitar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar o aceite.");
      setEnviando(false);
    }
  }

  return (
    <div className="cartao grade" style={{ maxWidth: "52rem" }}>
      <h1 style={{ margin: 0 }}>Termo de consentimento</h1>
      <p style={{ margin: 0 }}>
        Você está sendo convidado(a) a participar da validação de uma ferramenta de correção assistida por rubrica, Trabalho de Conclusão de
        Curso da Especialização em Projetos em Inteligência Artificial da Universidade Federal do Amapá (UNIFAP). Você vai corrigir no
        sistema {nRespostas} respostas curtas e responder a dois questionários, em cerca de 70 minutos.
      </p>
      <p style={{ margin: 0 }}>
        As respostas corrigidas são fictícias. O sistema registra os níveis que você escolher e o tempo que levar em cada resposta, mas o que
        está sendo avaliado é a ferramenta, e não você. A participação é voluntária, você pode desistir a qualquer momento e o risco é mínimo,
        limitado a cansaço ou desconforto.
      </p>
      <p style={{ margin: 0 }}>
        Os dados serão analisados sem identificação, com cada participante representado por um código. Contato: Glauco Silva Sousa; Prof. Dr.
        Julio Cezar Costa Furtado, furtado@unifap.br.
      </p>
      <label className="linha" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
        <input type="checkbox" checked={aceito} onChange={(e) => setAceito(e.target.checked)} style={{ marginTop: "0.2rem" }} />
        <span>
          <strong>Li as informações acima e aceito participar.</strong>
        </span>
      </label>
      <label className="linha" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
        <input type="checkbox" checked={imagem} onChange={(e) => setImagem(e.target.checked)} style={{ marginTop: "0.2rem" }} />
        <span>Autorizo o uso de fotografias em que eu apareça, apenas no relatório acadêmico e em publicações do trabalho. (opcional)</span>
      </label>
      {erro && <p className="erro">{erro}</p>}
      <div>
        <button className="primario" disabled={!aceito || enviando} onClick={confirmar}>
          Confirmar e começar
        </button>
      </div>
    </div>
  );
}
