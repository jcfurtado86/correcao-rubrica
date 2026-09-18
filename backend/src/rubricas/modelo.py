"""Modelo de rubrica reutilizável (US6, FR-003).

Arquivo JSON sem dono, ids, lotes ou qualquer dado de estudante: só o que
define a rubrica. `versao_formato` protege a importação contra formatos futuros.
"""

from core.exceptions import ErroDeNegocio
from rubricas.serializers import RubricaEntrada
from rubricas.services import conteudo_canonico, criar_rubrica

VERSAO_FORMATO = 1


def exportar(versao) -> dict:
    canonico = conteudo_canonico(versao)
    return {
        "versao_formato": VERSAO_FORMATO,
        "titulo": versao.rubrica.titulo,
        "descricao": versao.rubrica.descricao,
        "criterios": [
            {
                "nome": c["nome"],
                "descricao": c["descricao"],
                "peso": c["peso"],
                "tipo": c["tipo"],
                "niveis": [
                    {
                        "rotulo": n["rotulo"],
                        "pontuacao": n["pontuacao"],
                        "descritor": n["descritor"],
                    }
                    for n in c["niveis"]
                ],
            }
            for c in canonico["criterios"]
        ],
    }


def importar(dono, dados: dict):
    if not isinstance(dados, dict) or dados.get("versao_formato") != VERSAO_FORMATO:
        raise ErroDeNegocio(
            "Arquivo de modelo desconhecido ou de versão não suportada.", codigo="modelo_invalido"
        )
    entrada = RubricaEntrada(data={k: v for k, v in dados.items() if k != "versao_formato"})
    if not entrada.is_valid():
        raise ErroDeNegocio(f"Modelo inválido: {entrada.errors}", codigo="modelo_invalido")
    return criar_rubrica(dono, entrada.validated_data)
