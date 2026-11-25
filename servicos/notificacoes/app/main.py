"""Serviço de Notificações (bônus).

Não recebe chamadas do serviço de Chamados: ele lê os eventos ChamadoAberto,
ChamadoAtribuido e ChamadoResolvido da fila e grava os avisos no próprio banco.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import consumidor
from app.config import DOCS_ATIVA
from app.database import Base, engine
from app.notificacoes.rotas import router as notificacoes_router
from app.seguranca_http import CabecalhosDeSeguranca

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    Base.metadata.create_all(engine)
    parar = consumidor.iniciar()
    yield
    if parar:
        parar.set()


app = FastAPI(
    title="HelpDesk TI · Serviço de Notificações", version="3.0.0", lifespan=ciclo_de_vida,
    docs_url="/docs" if DOCS_ATIVA else None, redoc_url=None,
    openapi_url="/openapi.json" if DOCS_ATIVA else None,
)
app.add_middleware(CabecalhosDeSeguranca)
app.include_router(notificacoes_router)


@app.get("/saude", tags=["Saúde"])
def saude():
    return {"servico": "notificacoes", "status": "ok"}
