import json
from datetime import datetime, timedelta, timezone

import jwt

from tests.conftest import gerar_token


def evento(tipo, destinatario_id, mensagem="Aviso"):
    return json.dumps({"tipo": tipo, "destinatario_id": destinatario_id, "mensagem": mensagem,
                       "criado_em": datetime.now().isoformat()}).encode()


def test_evento_vira_notificacao(cliente, contas, banco):
    from app import consumidor
    consumidor.tratar(evento("ChamadoAberto", 2, "Seu chamado #1 foi aberto."))
    avisos = cliente.get("/notificacoes", headers=contas["ana"]).json()
    assert len(avisos) == 1 and avisos[0]["tipo"] == "ChamadoAberto"


def test_notificacoes_sao_so_do_proprio_usuario(cliente, contas, banco):
    from app import consumidor
    consumidor.tratar(evento("ChamadoAberto", 2))
    assert cliente.get("/notificacoes", headers=contas["carla"]).json() == []


def test_evento_invalido_e_descartado(cliente, contas, banco):
    from app import consumidor
    consumidor.tratar(b"isto nao e json")
    consumidor.tratar(json.dumps({"tipo": "X"}).encode())
    assert cliente.get("/notificacoes", headers=contas["ana"]).json() == []


def test_rotas_exigem_login(cliente):
    assert cliente.get("/notificacoes").status_code == 401


def test_token_falso(cliente):
    falso = gerar_token(2, "solicitante", segredo="segredo-de-outra-pessoa-com-mais-de-32-caracteres")
    assert cliente.get("/notificacoes", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_sem_assinatura_alg_none(cliente):
    agora = datetime.now(timezone.utc)
    falso = jwt.encode({"sub": "2", "perfil": "solicitante", "iss": "helpdesk-ti", "iat": agora,
                        "exp": agora + timedelta(hours=1)}, None, algorithm="none")
    assert cliente.get("/notificacoes", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"servico": "notificacoes", "status": "ok"}
