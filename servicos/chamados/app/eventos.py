"""Publicação de eventos na fila (Redis).

No monólito, o Chamados chamava a função de notificar diretamente. Agora ele
só avisa "aconteceu isto" colocando um evento na fila. Quem quiser (o serviço
de Notificações) lê a fila no seu ritmo.

Se a fila estiver fora do ar, o chamado continua sendo salvo: o evento é só
registrado no log. Notificação é importante, mas não pode impedir o chamado.
"""
import json
import logging
from datetime import datetime

from app.config import FILA_EVENTOS, REDIS_URL

log = logging.getLogger("chamados.eventos")
_cliente = None


def _redis():
    global _cliente
    if _cliente is None:
        import redis
        _cliente = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    return _cliente


def publicar(tipo: str, destinatario_id: int, mensagem: str) -> bool:
    """Coloca o evento no fim da fila. Devolve False se não conseguiu."""
    if not REDIS_URL:
        return False
    evento = {"tipo": tipo, "destinatario_id": destinatario_id, "mensagem": mensagem,
              "criado_em": datetime.now().isoformat()}
    try:
        _redis().rpush(FILA_EVENTOS, json.dumps(evento))
        return True
    except Exception as erro:  # qualquer falha da fila não pode derrubar o chamado
        log.warning("Não foi possível publicar o evento %s: %s", tipo, erro)
        return False
