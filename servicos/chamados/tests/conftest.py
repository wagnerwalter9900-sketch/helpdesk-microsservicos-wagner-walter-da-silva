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


# Dados "dos outros serviços" usados nos testes: no lugar de chamar a rede,
# os testes trocam as funções de app.clientes por versões falsas.
USUARIOS = {1: "admin", 2: "solicitante", 3: "solicitante", 4: "tecnico"}
ATIVOS = {1: {"id": 1, "patrimonio": "PAT-1"}}


@pytest.fixture(autouse=True)
def servicos_falsos(monkeypatch):
    from app import clientes, eventos
    from app.erros import NaoEncontrado, RegraDeNegocio

    def obter_ativo(ativo_id, token):
        assert token, "o token precisa ser repassado"
        if ativo_id not in ATIVOS:
            raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
        return ATIVOS[ativo_id]

    def obter_tecnico(usuario_id, token):
        assert token, "o token precisa ser repassado"
        if usuario_id not in USUARIOS:
            raise NaoEncontrado(f"Usuário {usuario_id} não encontrado.")
        if USUARIOS[usuario_id] != "tecnico":
            raise RegraDeNegocio(f"Usuário {usuario_id} não é técnico.")
        return {"id": usuario_id, "perfil": "tecnico"}

    publicados = []
    monkeypatch.setattr(clientes, "obter_ativo", obter_ativo)
    monkeypatch.setattr(clientes, "obter_tecnico", obter_tecnico)
    monkeypatch.setattr(eventos, "publicar", lambda tipo, dest, msg: publicados.append((tipo, dest)) or True)
    return publicados


@pytest.fixture
def contas():
    return {
        "admin": {"headers": cabecalho(1, "admin"), "id": 1},
        "ana": {"headers": cabecalho(2, "solicitante"), "id": 2},
        "bia": {"headers": cabecalho(3, "solicitante"), "id": 3},
        "carla": {"headers": cabecalho(4, "tecnico"), "id": 4},
    }


@pytest.fixture
def ativo():
    return ATIVOS[1]
