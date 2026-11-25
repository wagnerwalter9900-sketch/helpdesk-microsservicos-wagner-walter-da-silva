"""Configurações lidas das variáveis de ambiente."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chamados.db")


def ler_segredo() -> str:
    """Lê o segredo do JWT: do .env (JWT_SEGREDO) ou do arquivo gerado no Docker.

    Precisa ser o mesmo segredo do serviço de Usuários, que emite os tokens.
    """
    segredo = os.getenv("JWT_SEGREDO", "").strip()
    if not segredo:
        arquivo = Path(os.getenv("JWT_SEGREDO_ARQUIVO", "/run/segredos/jwt"))
        segredo = arquivo.read_text().strip() if arquivo.is_file() else ""
    if len(segredo) < 32:
        raise RuntimeError("Defina JWT_SEGREDO no .env com pelo menos 32 caracteres.")
    return segredo


JWT_SEGREDO = ler_segredo()
JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"

# Tamanho máximo do corpo de uma requisição (em bytes)
TAMANHO_MAXIMO_REQUISICAO = 64 * 1024

DOCS_ATIVA = os.getenv("DOCS", "1") == "1"

# Endereços dos outros serviços. No Docker Compose, cada serviço é chamado pelo nome.
USUARIOS_URL = os.getenv("USUARIOS_URL", "http://usuarios:8000")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario:8000")
# Tempo máximo (em segundos) esperando a resposta de outro serviço
TIMEOUT_SERVICOS = float(os.getenv("TIMEOUT_SERVICOS", "3"))

# Fila de eventos (Redis). Vazio = não publica eventos.
REDIS_URL = os.getenv("REDIS_URL", "")
FILA_EVENTOS = os.getenv("FILA_EVENTOS", "helpdesk:eventos")
