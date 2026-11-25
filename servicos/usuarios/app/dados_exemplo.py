"""Cria os usuários de exemplo quando o banco está vazio (só para aula).

A ordem importa: os outros serviços usam estes ids nos dados de exemplo
(1 admin, 2 Ana, 3 Bruno, 4 Carla, 5 Diego).
"""
import os

from sqlalchemy.orm import Session

from app.usuarios import servico as usuarios
from app.usuarios.esquemas import UsuarioCriar

SENHA = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")


def carregar(db: Session) -> None:
    if usuarios.listar(db):
        return
    for nome, email, perfil in [
        ("Admin TI", "admin@empresa.com", "admin"),
        ("Ana Souza", "ana@empresa.com", "solicitante"),
        ("Bruno Lima", "bruno@empresa.com", "solicitante"),
        ("Carla Dias", "carla@empresa.com", "tecnico"),
        ("Diego Rocha", "diego@empresa.com", "tecnico"),
    ]:
        usuarios.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=SENHA))
