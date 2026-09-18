from lotes.anonimizacao import anonimizar, termos_de_identificacao

LINHAS = [
    {
        "Nome": "Heloísa",
        "Sobrenome": "Magalhães",
        "Email": "helo.m@exemplo.edu.br",
        "Mat": "2021123456",
    },
    {"Nome": "Ana", "Sobrenome": "dos Santos", "Email": "ana@exemplo.edu.br", "Mat": "2020654321"},
]
COLUNAS = ["Nome", "Sobrenome", "Email", "Mat"]


def _termos():
    return termos_de_identificacao(LINHAS, COLUNAS)


def test_email_vira_marcador():
    texto, n = anonimizar("Meu contato: fulano.tal+x@dominio.com.br, obrigado.", [])
    assert texto == "Meu contato: [EMAIL], obrigado."
    assert n == 1


def test_cpf_com_e_sem_mascara():
    texto, n = anonimizar("CPF 123.456.789-09 ou 12345678909.", [])
    assert texto == "CPF [CPF] ou [CPF]."
    assert n == 2


def test_sequencia_de_8_a_14_digitos_vira_matricula():
    texto, _ = anonimizar("Matrícula 20231234 e protocolo 12345678901234; ano 2026; 1234567.", [])
    assert texto == "Matrícula [MATRICULA] e protocolo [MATRICULA]; ano 2026; 1234567."


def test_nome_da_propria_linha_e_de_outra_linha_sem_acento_e_sem_caixa():
    texto, n = anonimizar("Eu, HELOISA magalhaes, discuti com a Ana.", _termos())
    assert texto == "Eu, [ESTUDANTE], discuti com a [ESTUDANTE]."
    assert n == 2


def test_limite_de_palavra_nao_altera_palavras_que_contem_o_nome():
    texto, n = anonimizar("A análise da Ana foi boa; bananas e anais.", _termos())
    assert texto == "A análise da [ESTUDANTE] foi boa; bananas e anais."
    assert n == 1


def test_particulas_de_nome_nao_viram_termos():
    termos = {t.lower() for t in _termos()}
    assert "dos" not in termos
    assert "santos" in termos
    texto, _ = anonimizar("A maioria dos testes passou.", _termos())
    assert texto == "A maioria dos testes passou."


def test_dominio_de_email_nao_vira_termo():
    termos = {t.lower() for t in _termos()}
    assert "exemplo" not in termos
    texto, _ = anonimizar("Um exemplo de validação.", _termos())
    assert texto == "Um exemplo de validação."


def test_palavras_com_menos_de_3_letras_ignoradas():
    termos = termos_de_identificacao([{"Nome": "Li Wu"}], ["Nome"])
    assert "Li" not in termos and "Wu" not in termos


def test_nome_completo_substituido_de_uma_vez():
    texto, n = anonimizar("Assinado: Heloísa Magalhães.", _termos())
    assert texto == "Assinado: [ESTUDANTE]."
    assert n == 1


def test_contagem_confere():
    texto, n = anonimizar(
        "Sou Ana (ana@exemplo.edu.br), matrícula 2020654321, CPF 111.222.333-44.", _termos()
    )
    assert texto == "Sou [ESTUDANTE] ([EMAIL]), matrícula [MATRICULA], CPF [CPF]."
    assert n == 4
