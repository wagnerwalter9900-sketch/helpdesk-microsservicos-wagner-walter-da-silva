"""Testes do gateway: encaminhamento, falhas e segurança da tela."""
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app


class Transporte(httpx.AsyncBaseTransport):
    """Simula os serviços: guarda o que recebeu e responde o que o teste mandar."""

    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.pedidos = resposta, erro, []

    async def handle_async_request(self, request):
        self.pedidos.append(request)
        if self.erro:
            raise self.erro
        return self.resposta or httpx.Response(200, json={"ok": True})


@pytest.fixture
def gateway():
    def criar(transporte):
        cliente = TestClient(app)
        cliente.__enter__()
        app.state.http = httpx.AsyncClient(transport=transporte)
        return cliente
    return criar


@pytest.mark.parametrize("caminho,servico", [
    ("/auth/login", "usuarios"), ("/usuarios/4", "usuarios"), ("/ativos", "inventario"),
    ("/chamados/1/status", "chamados"), ("/notificacoes", "notificacoes"),
])
def test_cada_rota_vai_para_o_servico_certo(gateway, caminho, servico):
    t = Transporte()
    gateway(t).get(caminho, headers={"Authorization": "Bearer abc"})
    pedido = t.pedidos[0]
    assert pedido.url.host == servico and pedido.url.path == caminho
    assert pedido.headers["authorization"] == "Bearer abc"  # o token é repassado


def test_corpo_e_parametros_sao_repassados(gateway):
    t = Transporte()
    gateway(t).post("/chamados?x=1", json={"titulo": "Teste"})
    assert t.pedidos[0].url.params["x"] == "1" and b"Teste" in t.pedidos[0].content


def test_status_da_resposta_e_repassado(gateway):
    t = Transporte(resposta=httpx.Response(401, json={"detail": "Faça login para continuar."}))
    r = gateway(t).get("/chamados")
    assert r.status_code == 401 and r.json()["detail"] == "Faça login para continuar."


def test_servico_fora_do_ar_responde_503(gateway):
    t = Transporte(erro=httpx.ConnectError("sem conexão"))
    r = gateway(t).get("/ativos")
    assert r.status_code == 503 and "Inventário" in r.json()["detail"]


def test_servico_lento_responde_504(gateway):
    t = Transporte(erro=httpx.ReadTimeout("demorou"))
    assert gateway(t).get("/chamados").status_code == 504


def test_rota_desconhecida(gateway):
    t = Transporte()
    assert gateway(t).get("/admin/segredos").status_code == 404 and t.pedidos == []


def test_saude_mostra_os_servicos(gateway):
    r = gateway(Transporte(erro=httpx.ConnectError("x"))).get("/saude").json()
    assert r["gateway"] == "no ar" and set(r["servicos"]) == {"usuarios", "inventario", "chamados", "notificacoes"}
    assert all(v == "fora do ar" for v in r["servicos"].values())


def test_requisicao_grande_demais(gateway):
    t = Transporte()
    r = gateway(t).post("/chamados", content="x" * 70000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and t.pedidos == []


def test_cabecalhos_de_seguranca(gateway):
    r = gateway(Transporte()).get("/")
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"


def test_tela_escapa_o_html():
    js = (Path(__file__).parent.parent / "app" / "web" / "app.js").read_text()
    assert "const esc =" in js and "onclick" not in js
