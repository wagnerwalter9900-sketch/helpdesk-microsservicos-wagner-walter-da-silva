"""Regras dos chamados.

O que mudou em relação ao monólito:
- conferir o equipamento e o técnico agora é uma chamada HTTP (app/clientes.py);
- notificar agora é publicar um evento na fila (app/eventos.py);
- quem está logado vem do token (UsuarioLogado), não do banco de usuários.

As regras continuam as mesmas (SLA, transições de status e permissões):
- solicitante: abre chamados e só vê, comenta e fecha os próprios;
- técnico e admin: veem todos, atribuem e mudam o status.
"""
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import clientes, eventos
from app.auth.dependencias import UsuarioLogado
from app.chamados import repositorio
from app.chamados.esquemas import ChamadoCriar, ComentarioCriar
from app.chamados.modelos import Chamado, Comentario
from app.erros import NaoEncontrado, RegraDeNegocio, SemPermissao

# Prazo para resolver o chamado, conforme a prioridade (SLA)
HORAS_SLA = {"critica": 4, "alta": 8, "media": 24, "baixa": 72}

# De qual status para quais status um chamado pode ir
TRANSICOES = {
    "aberto": {"em_atendimento"},
    "em_atendimento": {"resolvido"},
    "resolvido": {"fechado", "em_atendimento"},  # reabrir se o problema voltar
    "fechado": set(),
}

EQUIPE = ("tecnico", "admin")


def eh_equipe(usuario: UsuarioLogado) -> bool:
    return usuario.perfil in EQUIPE


def calcular_prazo(prioridade: str, inicio: datetime) -> datetime:
    return inicio + timedelta(hours=HORAS_SLA[prioridade])


def abrir(db: Session, dados: ChamadoCriar, usuario: UsuarioLogado) -> Chamado:
    if dados.ativo_id is not None:
        clientes.obter_ativo(dados.ativo_id, usuario.token)          # chamada HTTP ao Inventário

    agora = datetime.now()
    chamado = repositorio.salvar(db, Chamado(
        **dados.model_dump(), solicitante_id=usuario.id, status="aberto", criado_em=agora,
        prazo_sla=calcular_prazo(dados.prioridade, agora),
    ))
    eventos.publicar(                                                 # evento ChamadoAberto
        "ChamadoAberto", usuario.id,
        f"Seu chamado #{chamado.id} foi aberto. Prazo: {chamado.prazo_sla:%d/%m %H:%M}.",
    )
    return chamado


def obter(db: Session, chamado_id: int, usuario: UsuarioLogado) -> Chamado:
    chamado = repositorio.buscar_por_id(db, chamado_id)
    # Para quem não pode ver, responde "não encontrado": não revela que o chamado existe
    if chamado is None or not (eh_equipe(usuario) or chamado.solicitante_id == usuario.id):
        raise NaoEncontrado(f"Chamado {chamado_id} não encontrado.")
    return chamado


def listar(db: Session, usuario: UsuarioLogado, status: str | None = None, tecnico_id: int | None = None) -> list[Chamado]:
    solicitante_id = None if eh_equipe(usuario) else usuario.id
    return repositorio.listar(db, status, tecnico_id, solicitante_id)


def atribuir(db: Session, chamado_id: int, tecnico_id: int, usuario: UsuarioLogado) -> Chamado:
    if not eh_equipe(usuario):
        raise SemPermissao("Só técnicos e administradores atribuem chamados.")
    chamado = obter(db, chamado_id, usuario)
    if chamado.status in ("resolvido", "fechado"):
        raise RegraDeNegocio("Não é possível atribuir um chamado resolvido ou fechado.")
    tecnico = clientes.obter_tecnico(tecnico_id, usuario.token)      # chamada HTTP a Usuários
    chamado.tecnico_id = tecnico["id"]
    if chamado.status == "aberto":
        chamado.status = "em_atendimento"
    repositorio.salvar(db, chamado)
    eventos.publicar(                                                 # evento ChamadoAtribuido
        "ChamadoAtribuido", tecnico["id"], f"O chamado #{chamado.id} foi atribuído a você."
    )
    return chamado


def mudar_status(db: Session, chamado_id: int, novo_status: str, usuario: UsuarioLogado) -> Chamado:
    chamado = obter(db, chamado_id, usuario)
    # O solicitante só pode confirmar (fechar) ou reabrir o próprio chamado resolvido
    pode_solicitante = chamado.status == "resolvido" and novo_status in ("fechado", "em_atendimento")
    if not (eh_equipe(usuario) or pode_solicitante):
        raise SemPermissao("Você não pode mudar o status deste chamado.")
    if novo_status not in TRANSICOES[chamado.status]:
        raise RegraDeNegocio(f"Não é possível ir de '{chamado.status}' para '{novo_status}'.")
    if novo_status == "em_atendimento" and chamado.tecnico_id is None:
        raise RegraDeNegocio("Atribua um técnico antes de iniciar o atendimento.")
    chamado.status = novo_status
    repositorio.salvar(db, chamado)
    if novo_status == "resolvido":
        eventos.publicar(                                             # evento ChamadoResolvido
            "ChamadoResolvido", chamado.solicitante_id,
            f"Seu chamado #{chamado.id} foi resolvido. Confirme se está tudo certo.",
        )
    return chamado


def comentar(db: Session, chamado_id: int, dados: ComentarioCriar, usuario: UsuarioLogado) -> Comentario:
    chamado = obter(db, chamado_id, usuario)
    if chamado.status == "fechado":
        raise RegraDeNegocio("Chamados fechados não recebem comentários.")
    return repositorio.salvar_comentario(db, Comentario(
        chamado_id=chamado.id, autor_id=usuario.id, texto=dados.texto, criado_em=datetime.now()
    ))


def painel(db: Session, usuario: UsuarioLogado) -> dict:
    chamados = listar(db, usuario)
    agora = datetime.now()
    atrasados = sum(1 for c in chamados if c.status in ("aberto", "em_atendimento") and c.prazo_sla < agora)
    return {"total": len(chamados), "por_status": dict(Counter(c.status for c in chamados)), "atrasados": atrasados}
