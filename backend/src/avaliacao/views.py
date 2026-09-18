from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from avaliacao.estimativa import estimar
from avaliacao.models import Execucao, Rodada
from avaliacao.services import criar_rodada, progresso, retomar, rodada_de_referencia
from avaliacao.sugestao import sugestoes_da_resposta
from core.exceptions import ErroDeNegocio
from core.permissions import pode_ver_lote
from lotes.models import Resposta
from lotes.views import lote_do_dono


def _decimal(valor):
    if valor in (None, ""):
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation as exc:
        raise ErroDeNegocio("Valor numérico inválido.", codigo="invalido") from exc


def _verdadeiro(valor) -> bool:
    return valor is True or str(valor).lower() in {"1", "true", "sim"}


def rodada_json(rodada: Rodada) -> dict:
    return {
        "id": rodada.id,
        "lote": rodada.lote_id,
        "numero": rodada.numero,
        "status": rodada.status,
        "provedor": rodada.provedor,
        "modelo": rodada.modelo,
        "versao_prompt": rodada.versao_prompt,
        "custo_estimado_usd": float(rodada.custo_estimado_usd),
        "custo_acumulado_usd": float(rodada.custo_acumulado_usd),
        "teto_usd": float(rodada.teto_usd),
        "criado_em": rodada.criado_em,
        "concluida_em": rodada.concluida_em,
        **progresso(rodada),
    }


def _estimativa_publica(lote) -> dict:
    dados = estimar(lote)
    dados.pop("custo_previsto_chamada_usd")
    return dados


class EstimativaView(APIView):
    def post(self, request, pk):
        return Response(_estimativa_publica(lote_do_dono(request, pk)))


class RodadasView(APIView):
    def get(self, request, pk):
        lote = lote_do_dono(request, pk)
        return Response([rodada_json(r) for r in lote.rodadas.order_by("numero")])

    def post(self, request, pk):
        lote = lote_do_dono(request, pk)
        rodada = criar_rodada(
            lote,
            request.user,
            reaplicacao=_verdadeiro(request.data.get("reaplicacao")),
            confirmar=_verdadeiro(request.data.get("confirmar")),
            teto_usd=_decimal(request.data.get("teto_usd")),
        )
        return Response(rodada_json(rodada), status=status.HTTP_201_CREATED)


class RodadaView(APIView):
    def get(self, request, pk):
        rodada = get_object_or_404(Rodada.objects.select_related("lote"), pk=pk)
        if not pode_ver_lote(request.user, rodada.lote):
            raise ErroDeNegocio("Não encontrado.", codigo="nao_encontrado", status_code=404)
        return Response(rodada_json(rodada))


class RetomarView(APIView):
    def post(self, request, pk):
        rodada = get_object_or_404(Rodada, pk=pk, lote__dono=request.user)
        rodada = retomar(rodada, teto_usd=_decimal(request.data.get("teto_usd")))
        rodada.refresh_from_db()
        return Response(rodada_json(rodada))


class ExecucoesDaRespostaView(APIView):
    """Inspeção das execuções brutas (dono do lote ou pesquisador do estudo)."""

    def get(self, request, pk):
        resposta = get_object_or_404(Resposta.objects.select_related("lote"), pk=pk)
        if not pode_ver_lote(request.user, resposta.lote):
            raise ErroDeNegocio("Não encontrado.", codigo="nao_encontrado", status_code=404)
        rodadas = resposta.lote.rodadas.order_by("-numero")
        numero = request.query_params.get("rodada")
        rodada = rodadas.filter(numero=numero).first() if numero else rodadas.first()
        criterios = []
        for criterio in resposta.lote.versao_rubrica.criterios.all():
            execucoes = (
                Execucao.objects.filter(rodada=rodada, resposta=resposta, criterio=criterio)
                .prefetch_related("trechos")
                .order_by("indice")
                if rodada
                else []
            )
            criterios.append(
                {
                    "criterio": criterio.id,
                    "nome": criterio.nome,
                    "ordem": criterio.ordem,
                    "execucoes": [
                        {
                            "indice": e.indice,
                            "status": e.status,
                            "valida": e.valida,
                            "motivo_invalidez": e.motivo_invalidez,
                            "nivel_codigo": e.nivel_codigo,
                            "justificativa": e.justificativa,
                            "erro": e.erro,
                            "trechos": [
                                {
                                    "texto_citado": t.texto_citado,
                                    "localizado": t.localizado,
                                    "inicio": t.inicio,
                                    "fim": t.fim,
                                }
                                for t in e.trechos.all()
                            ],
                        }
                        for e in execucoes
                    ],
                }
            )
        return Response(
            {
                "id": resposta.id,
                "codigo": resposta.codigo,
                "texto": resposta.texto,
                "aviso": resposta.aviso,
                "rodada": rodada.numero if rodada else None,
                "criterios": criterios,
            }
        )


class SugestoesDaRespostaView(APIView):
    """Sugestões consolidadas de uma resposta (dono do lote ou pesquisador).

    O participante de estudo nunca passa por aqui: ele recebe as sugestões pela
    sessão do estudo, que aplica a condição com ou sem apoio no servidor.
    """

    def get(self, request, pk):
        resposta = get_object_or_404(Resposta.objects.select_related("lote"), pk=pk)
        if not pode_ver_lote(request.user, resposta.lote):
            raise ErroDeNegocio("Não encontrado.", codigo="nao_encontrado", status_code=404)
        rodada = rodada_de_referencia(resposta.lote)
        return Response(
            {
                "id": resposta.id,
                "codigo": resposta.codigo,
                "texto": resposta.texto,
                "aviso": resposta.aviso,
                "rodada": rodada.numero if rodada else None,
                "criterios": sugestoes_da_resposta(resposta, rodada),
            }
        )


class ModelosView(APIView):
    """Modelos disponíveis para um lote neste servidor, com o preço vigente."""

    def get(self, request):
        from conectores.catalogo import modelos_disponiveis

        return Response(modelos_disponiveis())
