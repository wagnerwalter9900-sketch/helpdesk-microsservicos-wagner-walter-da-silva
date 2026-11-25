ATIVO = {"patrimonio": "PAT-1", "tipo": "computador", "descricao": "Desktop", "setor": "TI"}


def test_tecnico_cadastra_ativo_e_filtra_por_setor(cliente, contas):
    h = contas["carla"]
    cliente.post("/ativos", headers=h, json={"patrimonio": "PAT-1", "tipo": "impressora", "descricao": "HP", "setor": "RH"})
    cliente.post("/ativos", headers=h, json={"patrimonio": "PAT-2", "tipo": "computador", "descricao": "Dell", "setor": "TI"})
    assert len(cliente.get("/ativos", params={"setor": "RH"}, headers=h).json()) == 1


def test_obter_ativo(cliente, contas):
    """O serviço de Chamados usa esta rota para conferir o equipamento."""
    criado = cliente.post("/ativos", headers=contas["carla"], json=ATIVO).json()
    r = cliente.get(f"/ativos/{criado['id']}", headers=contas["ana"])
    assert r.status_code == 200 and r.json()["patrimonio"] == "PAT-1"


def test_ativo_inexistente(cliente, contas):
    assert cliente.get("/ativos/999", headers=contas["ana"]).status_code == 404


def test_patrimonio_repetido(cliente, contas):
    cliente.post("/ativos", headers=contas["carla"], json=ATIVO)
    assert cliente.post("/ativos", headers=contas["carla"], json=ATIVO).status_code == 422


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"servico": "inventario", "status": "ok"}
