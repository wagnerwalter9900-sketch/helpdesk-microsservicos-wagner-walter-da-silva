"""Dependências do FastAPI para exigir login e perfil.

No monólito, o usuário era buscado no banco. Aqui não existe a tabela de
usuários: quem está logado vem do próprio token, que é assinado e não pode
ser alterado sem o segredo.
"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import tokens

esquema = HTTPBearer(auto_error=False)

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Faça login para continuar.",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass(frozen=True)
class UsuarioLogado:
    id: int
    perfil: str
    token: str  # guardado para repassar a outros serviços


def usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> UsuarioLogado:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NAO_AUTENTICADO
    try:
        usuario_id, perfil = tokens.ler(credenciais.credentials)
    except tokens.TokenInvalido:
        raise NAO_AUTENTICADO
    return UsuarioLogado(id=usuario_id, perfil=perfil, token=credenciais.credentials)


def exigir_perfil(*perfis: str):
    """Libera a rota só para os perfis informados."""
    def verificar(usuario: UsuarioLogado = Depends(usuario_atual)) -> UsuarioLogado:
        if usuario.perfil not in perfis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para esta ação.")
        return usuario
    return verificar
