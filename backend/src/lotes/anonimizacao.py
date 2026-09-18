"""Anonimização do texto das respostas na carga (contracts/importacao.md, research R9).

Funções puras, sem ORM. Ordem das substituições: e-mail, CPF, matrícula
(sequência de 8 a 14 dígitos) e, por fim, os termos de identificação tirados das
colunas mapeadas pela docente — de **todas** as linhas, porque um estudante pode
citar um colega.

A comparação de nomes ignora acento e caixa e respeita limite de palavra: o nome
"Ana" não altera "análise". O texto é dobrado caractere a caractere (mesmo
comprimento), para que a posição achada no texto dobrado valha no original.
"""

import re
import unicodedata
from itertools import permutations

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
RE_CPF = re.compile(r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)")
RE_MATRICULA = re.compile(r"(?<!\d)\d{8,14}(?!\d)")
RE_PALAVRA = re.compile(r"[^\W\d_]+")

# Partículas de nome com 3 letras ou menos que nunca identificam ninguém e
# apareceriam em qualquer frase ("a maioria dos testes").
PARTICULAS = {"de", "da", "do", "das", "dos", "di", "du", "del", "van", "von", "der", "den", "e"}

ESTUDANTE = "[ESTUDANTE]"
EMAIL = "[EMAIL]"
CPF = "[CPF]"
MATRICULA = "[MATRICULA]"


def _dobrar_caractere(c: str) -> str:
    base = unicodedata.normalize("NFD", c)[0].lower()
    return base[0] if base else c


def dobrar(texto: str) -> str:
    """Sem acento e em minúsculas, com exatamente o mesmo comprimento do original."""
    return "".join(_dobrar_caractere(c) for c in texto)


def _eh_nome(valor: str) -> bool:
    return "@" not in valor and bool(RE_PALAVRA.search(valor))


def termos_de_identificacao(linhas: list[dict], colunas: list[str]) -> list[str]:
    """Termos a remover dos textos, do mais longo para o mais curto."""
    termos: set[str] = set()
    for linha in linhas:
        nomes = []
        for coluna in colunas:
            valor = str(linha.get(coluna) or "").strip()
            if not valor:
                continue
            termos.add(valor)
            if not _eh_nome(valor):
                continue
            nomes.append(valor)
            for palavra in RE_PALAVRA.findall(valor):
                if len(palavra) >= 3 and dobrar(palavra) not in PARTICULAS:
                    termos.add(palavra)
        # Nome completo nas ordens possíveis ("Nome Sobrenome" e "Sobrenome Nome"),
        # para ser trocado por um único marcador.
        for combinacao in permutations(nomes[:4]):
            if len(combinacao) > 1:
                termos.add(" ".join(combinacao))
    return sorted(termos, key=lambda t: (-len(t), t))


def _padrao_de_termos(termos: list[str]) -> re.Pattern | None:
    alvos = sorted({dobrar(t).strip() for t in termos if t.strip()}, key=lambda t: (-len(t), t))
    if not alvos:
        return None
    # Alternância do mais longo para o mais curto: numa mesma posição, o nome
    # completo ganha dos pedaços.
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(a) for a in alvos) + r")(?!\w)")


def anonimizar(texto: str, termos: list[str], padrao: re.Pattern | None = None) -> tuple[str, int]:
    """Devolve o texto anonimizado e o número de substituições feitas.

    `padrao` permite reaproveitar a expressão compilada dos termos entre as
    respostas de uma mesma carga.
    """
    total = 0
    for regex, marcador in ((RE_EMAIL, EMAIL), (RE_CPF, CPF), (RE_MATRICULA, MATRICULA)):
        texto, n = regex.subn(marcador, texto)
        total += n
    padrao = padrao if padrao is not None else _padrao_de_termos(termos)
    if padrao is None:
        return texto, total
    achados = list(padrao.finditer(dobrar(texto)))
    for achado in reversed(achados):
        marcador = MATRICULA if achado.group(0).isdigit() else ESTUDANTE
        texto = texto[: achado.start()] + marcador + texto[achado.end() :]
    return texto, total + len(achados)


def compilar_termos(termos: list[str]) -> re.Pattern | None:
    return _padrao_de_termos(termos)
