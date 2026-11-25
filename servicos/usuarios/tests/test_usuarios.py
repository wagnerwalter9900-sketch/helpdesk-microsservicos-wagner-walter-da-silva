def test_admin_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Davi", "email": "davi@x.com", "perfil": "tecnico", "senha": "Forte1234"})
    assert r.status_code == 201
    assert "senha" not in r.json() and "senha_hash" not in r.json()


def test_email_repetido_e_recusado(cliente, contas):
    dados = {"nome": "Ana 2", "email": "ANA@x.com", "perfil": "solicitante", "senha": "Forte1234"}
    assert cliente.post("/usuarios", headers=contas["admin"]["headers"], json=dados).status_code == 422


def test_usuario_inexistente(cliente, contas):
    assert cliente.get("/usuarios/99", headers=contas["ana"]["headers"]).status_code == 404


def test_obter_usuario_mostra_o_perfil(cliente, contas):
    """O serviço de Chamados usa esta rota para conferir se alguém é técnico."""
    r = cliente.get(f"/usuarios/{contas['carla']['id']}", headers=contas["ana"]["headers"]).json()
    assert r["perfil"] == "tecnico" and "email" not in r


def test_lista_publica_nao_mostra_email(cliente, contas):
    lista = cliente.get("/usuarios", headers=contas["ana"]["headers"]).json()
    assert lista and all("email" not in u for u in lista)


def test_quem_sou_eu(cliente, contas):
    r = cliente.get("/auth/eu", headers=contas["ana"]["headers"]).json()
    assert r["email"] == "ana@x.com" and r["perfil"] == "solicitante"


def test_saude(cliente):
    assert cliente.get("/saude").json()["status"] == "ok"
