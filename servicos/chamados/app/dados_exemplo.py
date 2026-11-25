"""Cria os chamados de exemplo quando o banco está vazio (só para aula).

Os ids vêm dos dados de exemplo dos outros serviços:
usuários 2 = Ana, 3 = Bruno, 4 = Carla (técnica); ativos 1 = PC, 2 = impressora.
Aqui não há chamada HTTP: no início, os outros serviços podem ainda estar subindo.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app import eventos
from app.chamados import repositorio
from app.chamados.modelos import Chamado
from app.chamados.servico import calcular_prazo

ANA, BRUNO, CARLA = 2, 3, 4
PC, IMPRESSORA = 1, 2


def carregar(db: Session) -> None:
    if repositorio.listar(db):
        return
    agora = datetime.now()
    exemplos = [
        ("Computador não liga", "Apertei o botão e nada acontece.", "alta", ANA, PC, CARLA, "em_atendimento"),
        ("Impressora atolando papel", "Atola a cada 3 folhas.", "media", BRUNO, IMPRESSORA, None, "aberto"),
        ("Acesso ao sistema de RH", "Preciso de acesso para a nova estagiária.", "baixa", BRUNO, None, None, "aberto"),
    ]
    for titulo, descricao, prioridade, solicitante, ativo, tecnico, status in exemplos:
        c = repositorio.salvar(db, Chamado(
            titulo=titulo, descricao=descricao, prioridade=prioridade, solicitante_id=solicitante,
            ativo_id=ativo, tecnico_id=tecnico, status=status, criado_em=agora,
            prazo_sla=calcular_prazo(prioridade, agora),
        ))
        eventos.publicar("ChamadoAberto", solicitante,
                         f"Seu chamado #{c.id} foi aberto. Prazo: {c.prazo_sla:%d/%m %H:%M}.")
        if tecnico:
            eventos.publicar("ChamadoAtribuido", tecnico, f"O chamado #{c.id} foi atribuído a você.")
