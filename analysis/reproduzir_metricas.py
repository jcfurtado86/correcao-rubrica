"""Reproduz, a partir do ZIP exportado, as métricas do painel (SC-006).

Independente do backend de propósito: não importa nada do sistema. Lê os CSVs,
reimplementa as definições do research R10 e compara com `metricas.json`.

Uso:  python reproduzir_metricas.py exportacao-loteN.zip
Saída: "OK: 0 divergências" (código 0) ou a lista de diferenças (código 1).
"""

import csv
import io
import json
import math
import statistics
import sys
import warnings
import zipfile
from collections import Counter

import numpy as np
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.inter_rater import fleiss_kappa

TOLERANCIA = 1e-9
NAO_CONVERGENTES = {"DIVERGENTE", "SEM_EVIDENCIA", "INDETERMINADO"}


# --- definições (research R10) ----------------------------------------------

def razao(a, b):
    return a / b if b else None


def limpo(x):
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else x


def exata(pares):
    return razao(sum(a == b for a, b in pares), len(pares))


def adjacente(pares):
    return razao(sum(abs(a - b) <= 1 for a, b in pares), len(pares))


def qwk(pares, categorias):
    if len(pares) < 2:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return limpo(cohen_kappa_score([a for a, _ in pares], [b for _, b in pares],
                                       weights="quadratic", labels=categorias))


def fleiss(votos):
    categorias = sorted({v for vs in votos for v in vs})
    tabela = [[vs.count(c) for c in categorias] for vs in votos]
    if len(tabela) < 2 or len(categorias) < 2:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return limpo(fleiss_kappa(np.array(tabela)))


def taxa(estados, alvo):
    return razao(sum(e in alvo for e in estados), len(estados))


def media(v):
    return statistics.fmean(v) if v else None


def mediana(v):
    return statistics.median(v) if v else None


def bloco(pares, categorias, n):
    estados = [p["estado"] for p in pares]
    ordinais = [p for p in pares if p["modal"] is not None]
    conc = [(p["modal"], p["decidido"]) for p in ordinais if p["decidido"] is not None]
    sel = [(p["estado"], p["modal"], p["decidido"]) for p in ordinais if p["decidido"] is not None]
    est = [(p["modal"], p["outra"]) for p in ordinais if p["outra"] is not None]
    conv = [(a, b) for e, a, b in sel if e == "CONVERGENTE"]
    outros = [(a, b) for e, a, b in sel if e != "CONVERGENTE"]
    return {
        "n_pares": len(pares),
        "estados": dict(sorted(Counter(estados).items())),
        "taxa_divergencia": taxa(estados, {"DIVERGENTE"}),
        "taxa_nao_convergente": taxa(estados, NAO_CONVERGENTES),
        "acordo_medio": media([p["acordo"] for p in pares if p["n_validas"] > 0]),
        "fleiss": fleiss([p["votos"] for p in pares if len(p["votos"]) == n]),
        "concordancia": {"n": len(conc), "exata": exata(conc), "adjacente": adjacente(conc),
                         "qwk": qwk(conc, categorias)},
        "seletiva": {
            "cobertura": razao(len(conv), len(sel)),
            "n_convergentes": len(conv),
            "n_nao_convergentes": len(outros),
            "exata_convergentes": exata(conv),
            "exata_nao_convergentes": exata(outros),
        },
        "estabilidade": ({"n": len(est), "exata": exata(est), "qwk": qwk(est, categorias)}
                         if est else None),
        "distribuicao_decidida": dict(sorted(Counter(
            p["decidido_codigo"] for p in pares if p["decidido_codigo"]).items())),
    }


# --- leitura do ZIP ------------------------------------------------------------

def ler_csv(z, nome):
    return list(csv.DictReader(io.StringIO(z.read(nome).decode("utf-8"))))


def inteiro(x):
    return int(x) if x not in ("", None) else None


def painel_da_rodada(meta, consolidados, execucoes, decisoes, sessoes, rodada):
    criterios = meta["rubrica"]["criterios"]
    n = meta["lote"]["n_execucoes"]
    outra = "2" if rodada == "1" else "1"
    codigo_do_nivel = {(c["ordem"], nv["ordem"]): nv["codigo"] for c in criterios for nv in c["niveis"]}
    modal_outra = {(r["codigo"], int(r["criterio"])): inteiro(r["nivel_modal_ordem"])
                   for r in consolidados if r["rodada"] == outra}
    votos = {}
    for e in sorted(execucoes, key=lambda e: int(e["indice"])):
        if e["rodada"] == rodada and e["status"] == "CONCLUIDA" and e["valida"] == "1":
            votos.setdefault((e["codigo"], int(e["criterio"])), []).append(e["nivel_codigo"])
    decididos = {(d["codigo"], int(d["criterio"])): int(d["nivel_decidido_ordem"])
                 for d in decisoes
                 if d["vigente"] == "1" and d["dono_do_lote"] == "1" and d["participante"] == ""}
    pares = []
    for r in sorted((r for r in consolidados if r["rodada"] == rodada),
                    key=lambda r: (r["codigo"], int(r["criterio"]))):
        chave = (r["codigo"], int(r["criterio"]))
        decidido = decididos.get(chave)
        pares.append({
            "criterio": chave[1],
            "estado": r["estado"],
            "modal": inteiro(r["nivel_modal_ordem"]),
            "acordo": float(r["acordo"]),
            "n_validas": int(r["n_validas"]),
            "votos": votos.get(chave, []),
            "outra": modal_outra.get(chave),
            "decidido": decidido,
            "decidido_codigo": codigo_do_nivel.get((chave[1], decidido)) if decidido else None,
        })
    tempos = Counter()
    for s in sessoes:
        if s["dono_do_lote"] == "1" and s["participante"] == "" and int(s["n_decisoes"]) > 0:
            tempos[s["codigo"]] += int(s["tempo_ativo_ms"])
    tempos = sorted(tempos.values())
    por_criterio = []
    for c in criterios:
        cats = [nv["ordem"] for nv in c["niveis"]]
        ps = [p for p in pares if p["criterio"] == c["ordem"]]
        por_criterio.append({"criterio": c["ordem"], "nome": c["nome"], "tipo": c["tipo"],
                             **bloco(ps, cats, n)})
    todas = sorted({nv["ordem"] for c in criterios for nv in c["niveis"]})
    por_tipo = {}
    for tipo in ("OBJETIVO", "INTERPRETATIVO"):
        ordens = {c["ordem"] for c in criterios if c["tipo"] == tipo}
        ps = [p for p in pares if p["criterio"] in ordens]
        estados = [p["estado"] for p in ps]
        conc = [(p["modal"], p["decidido"]) for p in ps
                if p["modal"] is not None and p["decidido"] is not None]
        por_tipo[tipo] = {"n_pares": len(ps), "taxa_divergencia": taxa(estados, {"DIVERGENTE"}),
                          "taxa_nao_convergente": taxa(estados, NAO_CONVERGENTES),
                          "exata": exata(conc)}
    return {
        "criterios": por_criterio,
        "total": bloco(pares, todas, n),
        "por_tipo": por_tipo,
        "tempo": {"n_respostas": len(tempos), "mediana_ms": mediana(tempos), "media_ms": media(tempos)},
    }


def comparar(esperado, obtido, caminho, diferencas):
    if isinstance(obtido, dict):
        if not isinstance(esperado, dict):
            diferencas.append(f"{caminho}: esperado {esperado!r}, obtido objeto")
            return
        for chave, valor in obtido.items():
            comparar(esperado.get(chave), valor, f"{caminho}.{chave}", diferencas)
    elif isinstance(obtido, list):
        if not isinstance(esperado, list) or len(esperado) != len(obtido):
            diferencas.append(f"{caminho}: tamanhos diferentes")
            return
        for i, (a, b) in enumerate(zip(esperado, obtido, strict=True)):
            comparar(a, b, f"{caminho}[{i}]", diferencas)
    elif isinstance(obtido, float) or isinstance(esperado, float):
        if esperado is None or obtido is None or abs(float(esperado) - float(obtido)) > TOLERANCIA:
            diferencas.append(f"{caminho}: painel {esperado!r} × reproduzido {obtido!r}")
    elif esperado != obtido:
        diferencas.append(f"{caminho}: painel {esperado!r} × reproduzido {obtido!r}")


def main(caminho_zip):
    with zipfile.ZipFile(caminho_zip) as z:
        meta = json.loads(z.read("metadados.json"))
        metricas = json.loads(z.read("metricas.json"))
        consolidados = ler_csv(z, "consolidados.csv")
        execucoes = ler_csv(z, "execucoes.csv")
        decisoes = ler_csv(z, "decisoes.csv")
        sessoes = ler_csv(z, "sessoes.csv")
    diferencas = []
    for rodada, painel in metricas["por_rodada"].items():
        obtido = painel_da_rodada(meta, consolidados, execucoes, decisoes, sessoes, rodada)
        comparar(painel, obtido, f"rodada {rodada}", diferencas)
        total = obtido["total"]
        print(f"Rodada {rodada}: {total['n_pares']} pares · divergência "
              f"{total['taxa_divergencia']} · concordância exata {total['concordancia']['exata']} "
              f"(n={total['concordancia']['n']}) · QWK {total['concordancia']['qwk']}")
    if diferencas:
        print(f"{len(diferencas)} divergência(s):")
        for d in diferencas:
            print("  " + d)
        return 1
    print("OK: 0 divergências")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
