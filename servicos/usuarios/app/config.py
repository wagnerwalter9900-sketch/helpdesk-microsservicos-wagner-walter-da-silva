"""Configurações lidas das variáveis de ambiente."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usuarios.db")


def ler_segredo() -> str:
    """Lê o segredo do JWT: do .env (JWT_SEGREDO) ou do arquivo gerado no Docker.

    O segredo nunca fica no código. Sem segredo, o serviço nem sobe: todos os
    serviços precisam usar o mesmo segredo para conferir os tokens.
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
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))

# Proteção contra tentativas de adivinhar senhas
LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))

# Tamanho máximo do corpo de uma requisição (em bytes)
TAMANHO_MAXIMO_REQUISICAO = 64 * 1024

DOCS_ATIVA = os.getenv("DOCS", "1") == "1"
