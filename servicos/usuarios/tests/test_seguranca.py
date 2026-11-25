"""Testes de segurança do serviço de Usuários: login, tokens, senhas e permissões."""
from datetime import datetime, timedelta, timezone

import jwt

from app import config
from tests.conftest import SENHA


def test_rotas_exigem_login(cliente, contas):
    for metodo, rota in [("get", "/usuarios"), ("get", "/usuarios/1"), ("post", "/usuarios"), ("get", "/auth/eu")]:
        assert getattr(cliente, metodo)(rota).status_code == 401, rota


def test_login_com_senha_errada(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


def test_login_com_email_inexistente_tem_a_mesma_mensagem(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "ninguem@x.com", "senha": "errada123"})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


def test_bloqueio_apos_varias_senhas_erradas(cliente, contas):
    for _ in range(config.LOGIN_MAX_FALHAS):
        cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    # mesmo com a senha certa, fica bloqueado por um tempo
    assert cliente.post("/auth/login", json={"email": "ana@x.com", "senha": SENHA}).status_code == 429


def test_token_traz_o_perfil(cliente, contas):
    """Os outros serviços leem o id e o perfil direto do token."""
    token = contas["carla"]["headers"]["Authorization"].split()[1]
    dados = jwt.decode(token, config.JWT_SEGREDO, algorithms=["HS256"], issuer=config.JWT_EMISSOR)
    assert dados["perfil"] == "tecnico" and dados["sub"] == str(contas["carla"]["id"])


def test_token_adulterado(cliente, contas):
    token = contas["ana"]["headers"]["Authorization"] + "x"
    assert cliente.get("/auth/eu", headers={"Authorization": token}).status_code == 401


def test_token_assinado_com_outro_segredo(cliente, contas):
    falso = jwt.encode({"sub": str(contas["admin"]["id"]), "perfil": "admin", "iss": config.JWT_EMISSOR,
                        "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                       "segredo-de-outra-pessoa-com-mais-de-32-caracteres", algorithm="HS256")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_sem_assinatura_alg_none(cliente, contas):
    falso = jwt.encode({"sub": str(contas["admin"]["id"]), "perfil": "admin", "iss": config.JWT_EMISSOR,
                        "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                       None, algorithm="none")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_expirado(cliente, contas):
    antigo = datetime.now(timezone.utc) - timedelta(hours=2)
    vencido = jwt.encode({"sub": str(contas["ana"]["id"]), "perfil": "solicitante", "iss": config.JWT_EMISSOR,
                          "iat": antigo, "exp": antigo + timedelta(minutes=5)}, config.JWT_SEGREDO, algorithm="HS256")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_senha_guardada_com_hash(sessao, contas):
    from app.usuarios.modelos import Usuario
    with sessao() as db:
        u = db.query(Usuario).filter_by(email="ana@x.com").one()
        assert SENHA not in u.senha_hash and u.senha_hash.startswith("scrypt$")


def test_senha_fraca_e_recusada(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "solicitante", "senha": "abcdefgh"})
    assert r.status_code == 422


def test_solicitante_nao_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["ana"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "admin", "senha": "Forte1234"})
    assert r.status_code == 403


def test_campos_extras_sao_recusados(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "ana@x.com", "senha": SENHA, "perfil": "admin"})
    assert r.status_code == 422


def test_requisicao_grande_demais(cliente, contas):
    corpo = '{"nome": "' + "x" * 70000 + '"}'
    r = cliente.post("/usuarios", headers={**contas["admin"]["headers"], "Content-Type": "application/json"}, content=corpo)
    assert r.status_code == 413


def test_sem_segredo_o_servico_nao_sobe(monkeypatch, tmp_path):
    import pytest
    monkeypatch.setenv("JWT_SEGREDO", "")
    monkeypatch.setenv("JWT_SEGREDO_ARQUIVO", str(tmp_path / "nao-existe"))
    with pytest.raises(RuntimeError):
        config.ler_segredo()


def test_segredo_lido_do_arquivo(monkeypatch, tmp_path):
    arquivo = tmp_path / "jwt"
    arquivo.write_text("s" * 48)
    monkeypatch.setenv("JWT_SEGREDO", "")
    monkeypatch.setenv("JWT_SEGREDO_ARQUIVO", str(arquivo))
    assert config.ler_segredo() == "s" * 48
