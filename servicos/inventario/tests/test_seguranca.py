"""Testes de segurança do serviço de Inventário: o token é conferido aqui também."""
from datetime import datetime, timedelta, timezone

from tests.conftest import ATIVO_EXEMPLO, gerar_token


def test_rotas_exigem_login(cliente):
    for metodo, rota in [("get", "/ativos"), ("get", "/ativos/1"), ("post", "/ativos")]:
        assert getattr(cliente, metodo)(rota).status_code == 401, rota


def test_token_assinado_com_outro_segredo(cliente):
    falso = gerar_token(1, "admin", segredo="segredo-de-outra-pessoa-com-mais-de-32-caracteres")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_sem_assinatura_alg_none(cliente):
    import jwt
    agora = datetime.now(timezone.utc)
    falso = jwt.encode({"sub": "1", "perfil": "admin", "iss": "helpdesk-ti", "iat": agora,
                        "exp": agora + timedelta(hours=1)}, None, algorithm="none")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_expirado(cliente):
    antigo = datetime.now(timezone.utc) - timedelta(hours=2)
    vencido = gerar_token(2, "solicitante", iat=antigo, exp=antigo + timedelta(minutes=5))
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_token_com_perfil_inventado(cliente):
    token = gerar_token(2, "superusuario")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_solicitante_nao_cadastra_ativo(cliente, contas):
    assert cliente.post("/ativos", headers=contas["ana"], json=ATIVO_EXEMPLO).status_code == 403


def test_campos_extras_sao_recusados(cliente, contas):
    assert cliente.post("/ativos", headers=contas["carla"], json={**ATIVO_EXEMPLO, "id": 50}).status_code == 422


def test_patrimonio_com_caracteres_invalidos(cliente, contas):
    r = cliente.post("/ativos", headers=contas["carla"], json={**ATIVO_EXEMPLO, "patrimonio": "<script>"})
    assert r.status_code == 422


def test_requisicao_grande_demais(cliente, contas):
    corpo = '{"descricao": "' + "x" * 70000 + '"}'
    r = cliente.post("/ativos", headers={**contas["carla"], "Content-Type": "application/json"}, content=corpo)
    assert r.status_code == 413


def test_cabecalhos_de_seguranca(cliente, contas):
    r = cliente.get("/ativos", headers=contas["ana"])
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
