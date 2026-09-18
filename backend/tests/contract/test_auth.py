def test_login_por_email_devolve_par_de_tokens(cliente, docente):
    r = cliente().post(
        "/api/auth/token/",
        {"email": "docente@exemplo.org", "password": "senha-forte-123"},
        format="json",
    )
    assert r.status_code == 200
    assert {"access", "refresh"} <= set(r.json())


def test_me_com_token(cliente, docente):
    r = cliente(docente).get("/api/auth/me/")
    assert r.status_code == 200
    assert r.json() == {
        "id": docente.id,
        "email": docente.email,
        "nome": "Docente",
        "papel": "DOCENTE",
    }


def test_sem_token_recebe_401_no_formato_de_erro(cliente, db):
    r = cliente().get("/api/auth/me/")
    assert r.status_code == 401
    assert set(r.json()) == {"detail", "codigo"}


def test_senha_errada(cliente, docente):
    r = cliente().post(
        "/api/auth/token/", {"email": "docente@exemplo.org", "password": "errada"}, format="json"
    )
    assert r.status_code == 401
