"""Tratamento de falhas: o que acontece quando outro serviço está fora do ar.

Aqui os clientes HTTP são os de verdade (sem as versões falsas do conftest),
apontando para endereços onde nada responde.
"""
import time

import httpx
import pytest

from app import clientes, eventos

# As funções de verdade, guardadas antes de o conftest trocá-las pelas falsas
OBTER_ATIVO, OBTER_TECNICO, PUBLICAR = clientes.obter_ativo, clientes.obter_tecnico, eventos.publicar


@pytest.fixture
def clientes_reais(monkeypatch, servicos_falsos):
    monkeypatch.setattr(clientes, "obter_ativo", OBTER_ATIVO)
    monkeypatch.setattr(clientes, "obter_tecnico", OBTER_TECNICO)
    monkeypatch.setattr(clientes, "INVENTARIO_URL", "http://127.0.0.1:9")  # porta onde nada responde
    monkeypatch.setattr(clientes, "USUARIOS_URL", "http://127.0.0.1:9")
    return clientes


def abrir(cliente, h, **extra):
    return cliente.post("/chamados", headers=h, json={"titulo": "PC parado", "descricao": "Não liga", "prioridade": "alta", **extra})


def test_inventario_fora_do_ar_responde_503(cliente, contas, clientes_reais):
    inicio = time.monotonic()
    r = abrir(cliente, contas["ana"]["headers"], ativo_id=1)
    assert r.status_code == 503
    assert "Inventário" in r.json()["detail"]
    assert time.monotonic() - inicio < 5  # responde rápido, não trava


def test_chamado_sem_equipamento_funciona_com_inventario_fora(cliente, contas, clientes_reais):
    assert abrir(cliente, contas["ana"]["headers"]).status_code == 201


def test_usuarios_fora_do_ar_responde_503_ao_atribuir(cliente, contas, clientes_reais):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 4})
    assert r.status_code == 503 and "Usuários" in r.json()["detail"]
    # a lista de chamados continua funcionando
    assert cliente.get("/chamados", headers=contas["carla"]["headers"]).status_code == 200


def test_servico_lento_estoura_o_timeout(monkeypatch, clientes_reais):
    def demora(*args, **kwargs):
        raise httpx.ReadTimeout("demorou")
    monkeypatch.setattr(httpx, "get", demora)
    with pytest.raises(Exception) as erro:
        clientes_reais.obter_ativo(1, "token")
    assert "demorou demais" in str(erro.value)


def test_token_e_repassado(monkeypatch, clientes_reais):
    recebido = {}

    def falso_get(url, headers, timeout):
        recebido.update(url=url, headers=headers, timeout=timeout)
        return httpx.Response(200, json={"id": 1}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", falso_get)
    clientes_reais.obter_ativo(1, "meu-token")
    assert recebido["headers"]["Authorization"] == "Bearer meu-token"
    assert recebido["url"].endswith("/ativos/1") and recebido["timeout"] > 0


def test_fila_fora_do_ar_nao_impede_o_chamado(monkeypatch, cliente, contas):
    monkeypatch.setattr(eventos, "publicar", PUBLICAR)
    monkeypatch.setattr(eventos, "REDIS_URL", "redis://127.0.0.1:9/0")  # fila fora do ar
    monkeypatch.setattr(eventos, "_cliente", None)
    assert PUBLICAR("ChamadoAberto", 2, "teste") is False  # não lança erro
    assert abrir(cliente, contas["ana"]["headers"]).status_code == 201
