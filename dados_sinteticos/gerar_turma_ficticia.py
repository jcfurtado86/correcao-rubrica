"""Gera a turma fictícia usada nos testes e no quickstart (tasks T018).

Saídas (nesta pasta):
- turma_ficticia.xlsx e turma_ficticia.csv (separador ";"), 40 linhas no formato
  do relatório de respostas do Moodle: Sobrenome, Nome, Endereço de email,
  Número de identificação, Resposta 1.
- identificadores_plantados.txt: todo identificador usado (nomes completos,
  prenomes, sobrenomes, e-mails, CPFs nos dois formatos, matrículas), um por
  linha. É a lista que a auditoria procura depois da carga (SC-003).

Tudo é inventado. Os nomes foram escolhidos para não coincidirem com palavras
comuns do português, para que a auditoria não dê falso positivo.

Uso: python gerar_turma_ficticia.py
"""

import csv
import random
from pathlib import Path

from openpyxl import Workbook

AQUI = Path(__file__).resolve().parent
ENUNCIADO = (
    "Explique a diferença entre verificação e validação de software e dê um exemplo de cada uma."
)

PRENOMES = [
    "Anderson", "Beatriz", "Cauã", "Débora", "Emanuel", "Fabrícia", "Gustavo", "Heloísa",
    "Igor", "Jéssica", "Kléber", "Larissa", "Marcelo", "Natália", "Otávio", "Priscila",
    "Rafael", "Sabrina", "Thiago", "Úrsula", "Valdir", "Wesley", "Yasmin", "Zacarias",
    "Adriano", "Bruna", "Cristiano", "Daniela", "Everton", "Fernanda", "Gilberto", "Hortência",
    "Ivanildo", "Janaína", "Kátia", "Leandro", "Mirela", "Nivaldo", "Odete", "Péricles",
]
SOBRENOMES = [
    "Albuquerque", "Barbosa", "Cavalcante", "Damasceno", "Esteves", "Figueiredo", "Gonçalves",
    "Iglesias", "Junqueira", "Kawamura", "Lacerda", "Magalhães", "Nogueira", "Pimentel",
    "Quaresma", "Rezende", "Siqueira", "Tavares", "Uchôa", "Vasconcelos",
]

# Respostas-base: variam de fracas a fortes, para o dublê e o Gemini terem o que julgar.
BASES = [
    "Verificação é conferir se o software foi construído corretamente, de acordo com a "
    "especificação. Validação é conferir se construímos o software certo, aquele que o usuário "
    "precisa. Exemplo de verificação: revisão de código comparando com o documento de "
    "requisitos. Exemplo de validação: teste de aceitação com o cliente usando o sistema.",
    "Verificação pergunta se estamos construindo o produto corretamente e validação pergunta se "
    "estamos construindo o produto correto. Na verificação podemos fazer inspeções e testes "
    "unitários. Na validação fazemos testes com usuários reais.",
    "A verificação acontece durante o desenvolvimento e olha os artefatos. A validação olha o "
    "produto final junto ao cliente. Um exemplo seria rodar testes automatizados.",
    "Verificação e validação são a mesma coisa, servem para garantir a qualidade do software e "
    "achar erros antes de entregar para o cliente.",
    "Verificação é checar se o código segue os padrões da equipe. Validação é quando o gerente "
    "aprova o projeto. Por exemplo, o gerente olha o sistema e diz se está bom.",
    "Na verificação conferimos se cada fase do processo atende ao que a fase anterior definiu, "
    "como revisar se o projeto atende à especificação. Na validação conferimos se o sistema "
    "atende à necessidade real, por exemplo com um protótipo avaliado pelos usuários antes da "
    "implementação completa.",
    "Verificar é testar o software. Validar é o cliente usar.",
    "Verificação: análise estática do código e revisão por pares para garantir conformidade com "
    "os requisitos especificados. Validação: teste beta com usuários finais para confirmar que o "
    "sistema resolve o problema deles.",
]

# Fechamentos que tornam cada linha única: (i % 8, i // 8) é distinto para as 40 linhas,
# e só o par proposital (linhas 10 e 11) fica duplicado.
FECHAMENTOS = [
    "",
    " As duas atividades se complementam ao longo do projeto.",
    " Fazer as duas reduz retrabalho no fim do desenvolvimento.",
    " Na prática da equipe, a revisão vem antes da entrega.",
    " Sem isso o cliente só descobre os problemas em produção.",
]

CENARIOS = ["unanime", "4-1", "3-2", "2-2-1", "sem_evidencia", "trecho_inventado", "json_invalido"]


def cpf_ficticio(rng: random.Random) -> tuple[str, str]:
    digitos = "".join(str(rng.randint(0, 9)) for _ in range(11))
    mascarado = f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return digitos, mascarado


def gerar():
    rng = random.Random(20260918)
    linhas = []
    plantados: set[str] = set()
    for i in range(40):
        prenome = PRENOMES[i]
        sobrenome = SOBRENOMES[i % len(SOBRENOMES)]
        email = f"{prenome.lower()}.{sobrenome.lower()}{i}@alunos.exemplo.edu.br"
        email = email.translate(str.maketrans("áéíóúâêôãõçü", "aeiouaeoaocu"))
        matricula = f"20{rng.randint(10, 26)}{rng.randint(100000, 999999)}"
        linhas.append({
            "Sobrenome": sobrenome, "Nome": prenome, "Endereço de email": email,
            "Número de identificação": matricula,
            "Resposta 1": BASES[i % len(BASES)] + FECHAMENTOS[i // len(BASES)],
        })
        plantados.update({prenome, sobrenome, f"{prenome} {sobrenome}", email, matricula})

    # 7 roteiros do dublê (linhas 0–6)
    for i, cenario in enumerate(CENARIOS):
        linhas[i]["Resposta 1"] = f"{BASES[i % len(BASES)]} [[cenario:{cenario}]]"
    # 2 vazias (7, 8)
    linhas[7]["Resposta 1"] = ""
    linhas[8]["Resposta 1"] = "   "
    # 1 longa, acima de 15.000 caracteres (9)
    linhas[9]["Resposta 1"] = " ".join([BASES[0]] * 60)
    # 2 duplicadas (10 e 11 com o mesmo texto)
    linhas[11]["Resposta 1"] = linhas[10]["Resposta 1"]
    # 5 com identificadores dentro do texto (12–16)
    cpf_limpo, cpf_mascara = cpf_ficticio(rng)
    cpf2_limpo, cpf2_mascara = cpf_ficticio(rng)
    plantados.update({cpf_limpo, cpf_mascara, cpf2_limpo, cpf2_mascara})
    l = linhas
    l[12]["Resposta 1"] = f"Sou {l[12]['Nome']} {l[12]['Sobrenome']}. " + BASES[0]
    l[13]["Resposta 1"] = BASES[1] + f" Qualquer dúvida, meu e-mail é {l[13]['Endereço de email']}."
    l[14]["Resposta 1"] = BASES[5] + f" CPF {cpf_mascara}."
    l[15]["Resposta 1"] = BASES[7] + f" Matrícula {l[15]['Número de identificação']}, CPF {cpf2_limpo}."
    l[16]["Resposta 1"] = f"{l[16]['Nome'].upper()} aqui. " + BASES[2]
    # 1 que cita colega (17 cita o prenome da linha 30)
    l[17]["Resposta 1"] = BASES[0] + f" Discuti este exemplo com {l[30]['Nome']} na aula."

    colunas = list(linhas[0].keys())
    with open(AQUI / "turma_ficticia.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)
    livro = Workbook()
    planilha = livro.active
    planilha.title = "Respostas"
    planilha.append(colunas)
    for linha in linhas:
        planilha.append([linha[c] for c in colunas])
    livro.save(AQUI / "turma_ficticia.xlsx")
    (AQUI / "identificadores_plantados.txt").write_text(
        "\n".join(sorted(plantados)) + "\n", encoding="utf-8"
    )
    (AQUI / "enunciado.txt").write_text(ENUNCIADO + "\n", encoding="utf-8")
    return len(linhas), len(plantados)


if __name__ == "__main__":
    n, p = gerar()
    print(f"{n} respostas, {p} identificadores plantados")
