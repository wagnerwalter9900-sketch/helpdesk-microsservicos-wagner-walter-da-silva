import os
from datetime import datetime, timedelta, timezone

# Segredo só para os testes (precisa existir antes de importar a aplicação)
os.environ.setdefault("JWT_SEGREDO", "segredo-de-teste-com-mais-de-32-caracteres")
os.environ["DADOS_EXEMPLO"] = "0"

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import config  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


ATIVO_EXEMPLO = {"patrimonio": "PAT-1", "tipo": "computador", "descricao": "Desktop", "setor": "TI"}


def gerar_token(usuario_id: int, perfil: str, segredo: str | None = None, **mudar) -> str:
    """Cria um token igual ao que o serviço de Usuários emite no login."""
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(usuario_id), "perfil": perfil, "iss": config.JWT_EMISSOR,
             "iat": agora, "exp": agora + timedelta(minutes=60), **mudar}
    return jwt.encode(dados, segredo or config.JWT_SEGREDO, algorithm="HS256")


def cabecalho(usuario_id: int, perfil: str) -> dict:
    return {"Authorization": f"Bearer {gerar_token(usuario_id, perfil)}"}


@pytest.fixture
def cliente():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def db_de_teste():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = db_de_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def contas():
    return {"admin": cabecalho(1, "admin"), "ana": cabecalho(2, "solicitante"), "carla": cabecalho(4, "tecnico")}
