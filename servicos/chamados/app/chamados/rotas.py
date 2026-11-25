from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencias import UsuarioLogado, usuario_atual
from app.chamados import servico
from app.chamados.esquemas import (
    Atribuicao, ChamadoCriar, ChamadoSaida, ComentarioCriar, ComentarioSaida, MudancaStatus, Painel, Status,
)
from app.database import get_db

router = APIRouter(prefix="/chamados", tags=["Chamados"])


@router.post("", response_model=ChamadoSaida, status_code=201)
def abrir_chamado(dados: ChamadoCriar, usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.abrir(db, dados, usuario)


@router.get("", response_model=list[ChamadoSaida])
def listar_chamados(status: Status | None = None, tecnico_id: int | None = None,
                    usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.listar(db, usuario, status, tecnico_id)


@router.get("/painel", response_model=Painel)
def painel(usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.painel(db, usuario)


@router.get("/{chamado_id}", response_model=ChamadoSaida)
def obter_chamado(chamado_id: int, usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.obter(db, chamado_id, usuario)


@router.patch("/{chamado_id}/atribuir", response_model=ChamadoSaida)
def atribuir_chamado(chamado_id: int, dados: Atribuicao, usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.atribuir(db, chamado_id, dados.tecnico_id, usuario)


@router.patch("/{chamado_id}/status", response_model=ChamadoSaida)
def mudar_status(chamado_id: int, dados: MudancaStatus, usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.mudar_status(db, chamado_id, dados.status, usuario)


@router.post("/{chamado_id}/comentarios", response_model=ComentarioSaida, status_code=201)
def comentar(chamado_id: int, dados: ComentarioCriar, usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.comentar(db, chamado_id, dados, usuario)
