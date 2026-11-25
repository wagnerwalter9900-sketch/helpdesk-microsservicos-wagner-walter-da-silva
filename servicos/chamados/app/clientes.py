"""Chamadas HTTP para os serviços de Usuários e de Inventário.

No monólito, estas consultas eram chamadas de função. Agora passam pela rede,
e a rede pode falhar. Por isso:
- toda chamada tem tempo limite (timeout), para nunca travar o Chamados;
- se o outro serviço estiver fora do ar, lança ServicoIndisponivel (vira 503);
- o token do usuário é repassado no cabeçalho Authorization, porque o outro
  serviço também confere o login.
"""
import logging

import httpx

from app.config import INVENTARIO_URL, TIMEOUT_SERVICOS, USUARIOS_URL
from app.erros import NaoEncontrado, RegraDeNegocio, ServicoIndisponivel

log = logging.getLogger("chamados.clientes")


def _get(url: str, token: str, servico: str) -> httpx.Response:
    try:
        return httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SERVICOS)
    except httpx.TimeoutException:
        log.warning("%s demorou mais de %ss para responder", servico, TIMEOUT_SERVICOS)
        raise ServicoIndisponivel(f"O serviço de {servico} demorou demais para responder. Tente de novo em instantes.")
    except httpx.RequestError as erro:
        log.warning("%s fora do ar: %s", servico, erro)
        raise ServicoIndisponivel(f"O serviço de {servico} está fora do ar. Tente de novo em instantes.")


def _conferir_resposta(resposta: httpx.Response, servico: str) -> dict:
    if resposta.status_code >= 500:
        raise ServicoIndisponivel(f"O serviço de {servico} está com problemas. Tente de novo em instantes.")
    if resposta.status_code != 200:
        log.warning("%s respondeu %s", servico, resposta.status_code)
        raise ServicoIndisponivel(f"Não foi possível consultar o serviço de {servico}.")
    return resposta.json()


def obter_ativo(ativo_id: int, token: str) -> dict:
    """Confere se o equipamento existe: GET /ativos/{id} no serviço de Inventário."""
    resposta = _get(f"{INVENTARIO_URL}/ativos/{ativo_id}", token, "Inventário")
    if resposta.status_code == 404:
        raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
    return _conferir_resposta(resposta, "Inventário")


def obter_tecnico(usuario_id: int, token: str) -> dict:
    """Confere se a pessoa existe e é técnica: GET /usuarios/{id} no serviço de Usuários."""
    resposta = _get(f"{USUARIOS_URL}/usuarios/{usuario_id}", token, "Usuários")
    if resposta.status_code == 404:
        raise NaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    usuario = _conferir_resposta(resposta, "Usuários")
    if usuario.get("perfil") != "tecnico":
        raise RegraDeNegocio(f"Usuário {usuario_id} não é técnico.")
    return usuario
