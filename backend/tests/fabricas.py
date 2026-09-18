"""Fábricas de dados para os testes (sem dado real de estudante)."""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile

DADOS = Path(__file__).resolve().parents[2] / "dados_sinteticos"

RUBRICA_PADRAO = {
    "titulo": "Verificação e validação",
    "descricao": "Rubrica de teste",
    "criterios": [
        {
            "nome": nome,
            "descricao": f"Critério {nome}",
            "peso": "1",
            "tipo": tipo,
            "niveis": [
                {"rotulo": "Insuficiente", "pontuacao": "0", "descritor": "Não atende."},
                {"rotulo": "Parcial", "pontuacao": "1", "descritor": "Atende em parte."},
                {"rotulo": "Adequado", "pontuacao": "2", "descritor": "Atende."},
                {"rotulo": "Excelente", "pontuacao": "3", "descritor": "Atende com precisão."},
            ],
        }
        for nome, tipo in [
            ("Conceituação", "OBJETIVO"),
            ("Distinção", "OBJETIVO"),
            ("Exemplificação", "INTERPRETATIVO"),
            ("Clareza", "INTERPRETATIVO"),
        ]
    ],
}


def rubrica(dono, dados=None):
    from rubricas.services import criar_rubrica

    return criar_rubrica(dono, dados or RUBRICA_PADRAO)


def lote(dono, versao=None, **extras):
    from lotes.models import Lote

    versao = versao or rubrica(dono).versao_vigente
    campos = {
        "titulo": "Lote de teste",
        "enunciado": (DADOS / "enunciado.txt").read_text(encoding="utf-8").strip(),
        "versao_rubrica": versao,
        "sintetico": True,
        "provedor_llm": "dumb",
        "modelo_llm": "dublê",
    }
    campos.update(extras)
    return Lote.objects.create(dono=dono, **campos)


def arquivo_turma(formato="csv"):
    nome = f"turma_ficticia.{formato}"
    return SimpleUploadedFile(nome, (DADOS / nome).read_bytes())


COLUNAS_ID = ["Sobrenome", "Nome", "Endereço de email", "Número de identificação"]


def lote_importado(dono, formato="csv", **extras):
    from lotes.importacao import importar

    novo = lote(dono, **extras)
    importar(novo, arquivo_turma(formato), "Resposta 1", COLUNAS_ID, gerar_chave=False, semente=1)
    return novo


def identificadores_plantados():
    return [
        linha.strip()
        for linha in (DADOS / "identificadores_plantados.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if linha.strip()
    ]
