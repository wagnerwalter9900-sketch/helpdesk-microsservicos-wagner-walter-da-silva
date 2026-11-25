from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Chamado(Base):
    __tablename__ = "chamados"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text)
    prioridade: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="aberto")
    # Sem chaves estrangeiras para usuários e ativos: essas tabelas ficam nos bancos
    # dos outros serviços. Aqui guardamos só o número (id), e quem confere se ele
    # existe é o próprio serviço dono do dado, por HTTP (veja app/clientes.py).
    solicitante_id: Mapped[int]
    tecnico_id: Mapped[int | None] = mapped_column(nullable=True)
    ativo_id: Mapped[int | None] = mapped_column(nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime)
    prazo_sla: Mapped[datetime] = mapped_column(DateTime)

    comentarios: Mapped[list["Comentario"]] = relationship(
        back_populates="chamado", order_by="Comentario.id", cascade="all, delete-orphan"
    )


class Comentario(Base):
    __tablename__ = "comentarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Esta chave estrangeira continua: chamados e comentários ficam no mesmo banco
    chamado_id: Mapped[int] = mapped_column(ForeignKey("chamados.id"))
    autor_id: Mapped[int]
    texto: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime)

    chamado: Mapped[Chamado] = relationship(back_populates="comentarios")
