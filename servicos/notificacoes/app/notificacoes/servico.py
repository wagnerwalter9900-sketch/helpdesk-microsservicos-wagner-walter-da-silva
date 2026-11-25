"""Regras das notificações."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notificacoes.modelos import Notificacao


def registrar(db: Session, evento: dict) -> Notificacao:
    """Grava o aviso que veio de um evento. No mundo real, aqui seria enviado um e-mail ou SMS."""
    aviso = Notificacao(
        tipo=str(evento["tipo"])[:40],
        destinatario_id=int(evento["destinatario_id"]),
        mensagem=str(evento["mensagem"])[:300],
        criada_em=datetime.fromisoformat(evento["criado_em"]) if evento.get("criado_em") else datetime.now(),
    )
    db.add(aviso)
    db.commit()
    db.refresh(aviso)
    return aviso


def listar(db: Session, destinatario_id: int) -> list[Notificacao]:
    consulta = select(Notificacao).where(Notificacao.destinatario_id == destinatario_id).order_by(Notificacao.id)
    return list(db.scalars(consulta))
