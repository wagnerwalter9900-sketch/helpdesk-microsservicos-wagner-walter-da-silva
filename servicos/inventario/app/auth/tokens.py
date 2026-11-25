"""Leitura dos tokens JWT emitidos pelo serviço de Usuários."""
import jwt

from app.config import JWT_ALGORITMO, JWT_EMISSOR, JWT_SEGREDO

PERFIS = ("solicitante", "tecnico", "admin")


class TokenInvalido(Exception):
    pass


def ler(token: str) -> tuple[int, str]:
    """Devolve (id do usuário, perfil), ou lança TokenInvalido."""
    try:
        dados = jwt.decode(
            token, JWT_SEGREDO, algorithms=[JWT_ALGORITMO], issuer=JWT_EMISSOR,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
        perfil = dados.get("perfil")
        if perfil not in PERFIS:
            raise TokenInvalido()
        return int(dados["sub"]), perfil
    except (jwt.PyJWTError, ValueError) as erro:
        raise TokenInvalido() from erro
