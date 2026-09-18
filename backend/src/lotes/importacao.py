"""Leitura da planilha e carga anonimizada (contracts/importacao.md, FR-004–FR-007).

O arquivo é lido **em memória** (settings: MemoryFileUploadHandler) e nunca é
gravado. As colunas de identificação só existem durante esta função: servem
para montar os termos a remover do texto e, se pedida, a chave de
reidentificação, que volta na resposta uma única vez e não é guardada.
"""

import base64
import csv
import hashlib
import io
import random
import unicodedata
from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from openpyxl import load_workbook

from core.exceptions import ErroDeNegocio
from lotes.anonimizacao import anonimizar, compilar_termos, termos_de_identificacao
from lotes.models import Resposta


def _erro(mensagem, codigo, status_code=400):
    return ErroDeNegocio(mensagem, codigo=codigo, status_code=status_code)


def _celula(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    return str(valor)


def _cabecalho_unico(cabecalho: list[str]) -> list[str]:
    vistos: dict[str, int] = {}
    saida = []
    for i, nome in enumerate(cabecalho):
        nome = nome.strip() or f"Coluna {i + 1}"
        if nome in vistos:
            vistos[nome] += 1
            nome = f"{nome} ({vistos[nome]})"
        else:
            vistos[nome] = 1
        saida.append(nome)
    return saida


def _linhas_csv(dados: bytes) -> list[list[str]]:
    try:
        texto = dados.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _erro("O CSV precisa estar em UTF-8.", "arquivo_invalido") from exc
    primeira = texto.split("\n", 1)[0]
    separador = max((",", ";", "\t"), key=primeira.count)
    return [linha for linha in csv.reader(io.StringIO(texto), delimiter=separador)]


def _linhas_xlsx(dados: bytes) -> list[list[str]]:
    try:
        livro = load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    except Exception as exc:
        raise _erro("Não foi possível ler a planilha XLSX.", "arquivo_invalido") from exc
    try:
        planilha = livro.worksheets[0]
        return [[_celula(v) for v in linha] for linha in planilha.iter_rows(values_only=True)]
    finally:
        livro.close()


def ler_planilha(arquivo) -> tuple[list[str], list[dict]]:
    """(colunas, linhas como dicionários de texto). Levanta ErroDeNegocio."""
    if arquivo.size > settings.LIMITE_UPLOAD_BYTES:
        raise _erro("O arquivo passa de 10 MB.", "arquivo_grande")
    arquivo.seek(0)
    dados = arquivo.read()
    brutas = _linhas_xlsx(dados) if dados[:2] == b"PK" else _linhas_csv(dados)
    brutas = [linha for linha in brutas if any(str(c).strip() for c in linha)]
    if not brutas:
        raise _erro("A planilha está vazia.", "arquivo_invalido")
    colunas = _cabecalho_unico([str(c) for c in brutas[0]])
    corpo = brutas[1:]
    if len(corpo) > settings.LIMITE_LINHAS_PLANILHA:
        raise _erro(
            f"A planilha tem {len(corpo)} linhas; o limite é {settings.LIMITE_LINHAS_PLANILHA}.",
            "linhas_demais",
        )
    linhas = []
    for bruta in corpo:
        valores = [str(v) for v in bruta] + [""] * (len(colunas) - len(bruta))
        linhas.append(dict(zip(colunas, valores[: len(colunas)], strict=True)))
    return colunas, linhas


def previa(arquivo) -> dict:
    colunas, linhas = ler_planilha(arquivo)
    amostra = [[linha[c] for c in colunas] for linha in linhas[:5]]
    return {"colunas": colunas, "amostra": amostra, "total_linhas": len(linhas)}


def _validar_mapeamento(colunas, coluna_resposta, colunas_identificacao):
    if coluna_resposta not in colunas:
        raise _erro("A coluna de resposta não existe na planilha.", "coluna_invalida")
    if not colunas_identificacao:
        raise _erro("Indique ao menos uma coluna de identificação.", "coluna_invalida")
    faltando = [c for c in colunas_identificacao if c not in colunas]
    if faltando:
        raise _erro(f"Colunas inexistentes: {', '.join(faltando)}.", "coluna_invalida")
    if coluna_resposta in colunas_identificacao:
        raise _erro("A coluna de resposta não pode ser de identificação.", "coluna_invalida")


def _chave_csv(pares: list[tuple[str, str]], lote) -> dict:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["codigo", "identificador"])
    escritor.writerows(sorted(pares))
    conteudo = base64.b64encode(buffer.getvalue().encode("utf-8")).decode("ascii")
    return {
        "nome_arquivo": f"chave-lote{lote.id}-{date.today().isoformat()}.csv",
        "conteudo_base64": conteudo,
    }


@transaction.atomic
def importar(
    lote,
    arquivo,
    coluna_resposta: str,
    colunas_identificacao: list[str],
    gerar_chave: bool,
    semente: int | None = None,
) -> dict:
    if lote.respostas.exists():
        raise _erro("Este lote já recebeu respostas.", "ja_importado", status_code=409)
    colunas, linhas = ler_planilha(arquivo)
    _validar_mapeamento(colunas, coluna_resposta, colunas_identificacao)
    termos = termos_de_identificacao(linhas, colunas_identificacao)
    padrao = compilar_termos(termos)

    # Embaralha antes de numerar: a ordem do arquivo costuma ser alfabética, e o
    # código não pode revelar quem é quem.
    sorteio = random.Random(semente) if semente is not None else random.SystemRandom()
    ordem = list(range(len(linhas)))
    sorteio.shuffle(ordem)
    largura = max(3, len(str(len(linhas))))

    respostas, avisos, pares, por_texto = [], [], [], {}
    for posicao, indice in enumerate(ordem, start=1):
        linha = linhas[indice]
        codigo = f"R{posicao:0{largura}d}"
        texto, n = anonimizar(linha[coluna_resposta], termos, padrao)
        # NFC: a verificação de âncora compara caractere a caractere (research R5).
        texto = unicodedata.normalize("NFC", texto).strip()
        aviso = None
        if not texto:
            aviso = Resposta.Aviso.VAZIA
        elif len(texto) > settings.LIMITE_CARACTERES_RESPOSTA:
            aviso = Resposta.Aviso.LONGA
        if aviso:
            avisos.append({"codigo": codigo, "tipo": aviso})
        if texto:
            por_texto.setdefault(texto, []).append(codigo)
        respostas.append(
            Resposta(
                lote=lote,
                codigo=codigo,
                texto=texto,
                hash_texto=hashlib.sha256(texto.encode("utf-8")).hexdigest(),
                n_substituicoes=n,
                aviso=aviso,
            )
        )
        if gerar_chave:
            identificador = " | ".join(linha[c] for c in colunas_identificacao)
            pares.append((codigo, identificador))
    for codigos in por_texto.values():
        if len(codigos) > 1:
            avisos.extend({"codigo": c, "tipo": "DUPLICADA"} for c in codigos)

    Resposta.objects.bulk_create(respostas)
    chave = _chave_csv(pares, lote) if gerar_chave else None
    del linhas, pares, termos, padrao
    return {
        "n_respostas": len(respostas),
        "avisos": sorted(avisos, key=lambda a: (a["codigo"], a["tipo"])),
        "chave_reidentificacao": chave,
    }
