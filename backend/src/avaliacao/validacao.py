"""Validação de uma saída do modelo (research R5; motivos de data-model.md).

Execução só é **válida** com JSON no formato do contrato, nível existente e,
para níveis da rubrica, todos os trechos localizados no texto. `SEM_EVIDENCIA`
exige lista de trechos vazia. Execução inválida não vota na consolidação.
"""

import json
from dataclasses import dataclass, field

from avaliacao.ancora import verificar_trecho

SEM_EVIDENCIA = "SEM_EVIDENCIA"


@dataclass
class TrechoVerificado:
    texto_citado: str
    localizado: bool
    inicio: int | None
    fim: int | None


@dataclass
class ResultadoValidacao:
    valida: bool
    motivo_invalidez: str | None
    nivel_codigo: str = ""
    justificativa: str = ""
    trechos: list[TrechoVerificado] = field(default_factory=list)


def _formato_ok(dados) -> bool:
    return (
        isinstance(dados, dict)
        and isinstance(dados.get("nivel"), str)
        and isinstance(dados.get("justificativa"), str)
        and isinstance(dados.get("trechos"), list)
        and all(isinstance(t, str) for t in dados["trechos"])
    )


def validar(texto_resposta: str, json_bruto: str, codigos_validos: list[str]) -> ResultadoValidacao:
    try:
        dados = json.loads(json_bruto)
    except (json.JSONDecodeError, TypeError):
        return ResultadoValidacao(False, "JSON_INVALIDO")
    if not _formato_ok(dados):
        return ResultadoValidacao(False, "JSON_INVALIDO")

    nivel = dados["nivel"].strip()
    justificativa = dados["justificativa"].strip()
    citados = [t for t in dados["trechos"]]

    if nivel != SEM_EVIDENCIA and nivel not in codigos_validos:
        return ResultadoValidacao(False, "NIVEL_FORA", nivel, justificativa)

    verificados = []
    motivo = None
    for citado in citados:
        m, inicio, fim = verificar_trecho(texto_resposta, citado)
        verificados.append(TrechoVerificado(citado, inicio is not None, inicio, fim))
        motivo = motivo or m

    if nivel == SEM_EVIDENCIA:
        if citados:
            return ResultadoValidacao(
                False, "INCOERENTE_SEM_EVIDENCIA", nivel, justificativa, verificados
            )
        return ResultadoValidacao(True, None, nivel, justificativa, [])
    if not citados:
        return ResultadoValidacao(False, "SEM_TRECHO", nivel, justificativa, [])
    return ResultadoValidacao(motivo is None, motivo, nivel, justificativa, verificados)
