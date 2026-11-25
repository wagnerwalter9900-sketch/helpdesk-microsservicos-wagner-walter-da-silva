"""Consumidor da fila de eventos.

Roda em segundo plano: espera um evento chegar na fila do Redis, grava o aviso
no banco e volta a esperar. Se o Redis cair, tenta de novo a cada 2 segundos.
Se este serviço ficar fora do ar, os eventos esperam na fila e são lidos
quando ele voltar: nenhum aviso se perde.
"""
import json
import logging
import threading

from app.config import FILA_EVENTOS, REDIS_URL
from app.database import SessionLocal
from app.notificacoes import servico

log = logging.getLogger("notificacoes.consumidor")


def tratar(mensagem: bytes) -> None:
    try:
        evento = json.loads(mensagem)
        with SessionLocal() as db:
            aviso = servico.registrar(db, evento)
        log.info("Evento %s recebido: aviso #%s para o usuário %s", aviso.tipo, aviso.id, aviso.destinatario_id)
    except (ValueError, KeyError, TypeError) as erro:
        log.warning("Evento inválido descartado: %s (%s)", mensagem[:200], erro)


def consumir(parar: threading.Event) -> None:
    import redis
    cliente = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=10)
    while not parar.is_set():
        try:
            item = cliente.blpop([FILA_EVENTOS], timeout=5)  # espera até 5 s por um evento
            if item:
                tratar(item[1])
        except redis.RedisError as erro:
            log.warning("Fila indisponível (%s). Tentando de novo em 2 s.", erro)
            parar.wait(2)


def iniciar() -> threading.Event | None:
    if not REDIS_URL:
        return None
    parar = threading.Event()
    threading.Thread(target=consumir, args=(parar,), daemon=True, name="consumidor-eventos").start()
    return parar
