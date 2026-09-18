"""Criação, edição com versionamento e congelamento de rubricas (FR-001, FR-002)."""

import hashlib
import json

from django.db import transaction

from core.exceptions import ErroDeNegocio
from rubricas.models import Criterio, Nivel, Rubrica, VersaoRubrica


def validar_estrutura(dados: dict) -> None:
    criterios = dados.get("criterios") or []
    if not criterios:
        raise ErroDeNegocio("A rubrica precisa de ao menos um critério.", codigo="rubrica_invalida")
    for c in criterios:
        if len(c.get("niveis") or []) < 2:
            raise ErroDeNegocio(
                f"O critério “{c.get('nome', '')}” precisa de ao menos 2 níveis.",
                codigo="rubrica_invalida",
            )


def _criar_conteudo(versao: VersaoRubrica, criterios: list[dict]) -> None:
    for ordem_c, c in enumerate(criterios, start=1):
        criterio = Criterio.objects.create(
            versao=versao,
            ordem=ordem_c,
            nome=c["nome"],
            descricao=c.get("descricao", ""),
            peso=c.get("peso", 1),
            tipo=c.get("tipo", Criterio.Tipo.INTERPRETATIVO),
        )
        for ordem_n, n in enumerate(c["niveis"], start=1):
            Nivel.objects.create(
                criterio=criterio,
                ordem=ordem_n,
                codigo=f"N{ordem_n}",
                rotulo=n["rotulo"],
                descritor=n.get("descritor", ""),
                pontuacao=n["pontuacao"],
            )


@transaction.atomic
def criar_rubrica(dono, dados: dict) -> Rubrica:
    validar_estrutura(dados)
    rubrica = Rubrica.objects.create(
        dono=dono, titulo=dados["titulo"], descricao=dados.get("descricao", "")
    )
    versao = VersaoRubrica.objects.create(rubrica=rubrica, numero=1)
    _criar_conteudo(versao, dados["criterios"])
    return rubrica


@transaction.atomic
def atualizar_rubrica(rubrica: Rubrica, dados: dict) -> tuple[VersaoRubrica, bool]:
    """Edita a versão vigente; se ela estiver congelada, cria a versão seguinte.

    Devolve (versão resultante, se foi criada uma versão nova).
    """
    validar_estrutura(dados)
    rubrica.titulo = dados["titulo"]
    rubrica.descricao = dados.get("descricao", "")
    rubrica.save(update_fields=["titulo", "descricao"])
    vigente = VersaoRubrica.objects.select_for_update().get(pk=rubrica.versao_vigente.pk)
    if vigente.congelada:
        nova = VersaoRubrica.objects.create(rubrica=rubrica, numero=vigente.numero + 1)
        _criar_conteudo(nova, dados["criterios"])
        return nova, True
    Nivel.objects.filter(criterio__versao=vigente).delete()
    vigente.criterios.all().delete()
    _criar_conteudo(vigente, dados["criterios"])
    return vigente, False


def conteudo_canonico(versao: VersaoRubrica) -> dict:
    return {
        "criterios": [
            {
                "ordem": c.ordem,
                "nome": c.nome,
                "descricao": c.descricao,
                "peso": str(c.peso),
                "tipo": c.tipo,
                "niveis": [
                    {
                        "ordem": n.ordem,
                        "codigo": n.codigo,
                        "rotulo": n.rotulo,
                        "descritor": n.descritor,
                        "pontuacao": str(n.pontuacao),
                    }
                    for n in c.niveis.order_by("ordem")
                ],
            }
            for c in versao.criterios.order_by("ordem")
        ]
    }


def congelar(versao: VersaoRubrica) -> VersaoRubrica:
    """Congela a versão e grava o sha256 do seu conteúdo canônico (Princípio V)."""
    if versao.congelada:
        return versao
    if not versao.criterios.exists():
        raise ErroDeNegocio("Versão sem critério não pode ser usada.", codigo="rubrica_invalida")
    canonico = json.dumps(conteudo_canonico(versao), sort_keys=True, ensure_ascii=False)
    versao.hash = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
    versao.congelada = True
    versao.save(update_fields=["hash", "congelada"])
    return versao
