"""Configurações do gateway."""
import os

# Para onde vai cada rota. Dentro do Docker Compose, os serviços se chamam pelo nome.
USUARIOS_URL = os.getenv("USUARIOS_URL", "http://usuarios:8000")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario:8000")
CHAMADOS_URL = os.getenv("CHAMADOS_URL", "http://chamados:8000")
NOTIFICACOES_URL = os.getenv("NOTIFICACOES_URL", "http://notificacoes:8000")

# Primeiro pedaço do caminho -> serviço que responde
ROTAS = {
    "auth": ("Usuários", USUARIOS_URL),
    "usuarios": ("Usuários", USUARIOS_URL),
    "ativos": ("Inventário", INVENTARIO_URL),
    "chamados": ("Chamados", CHAMADOS_URL),
    "notificacoes": ("Notificações", NOTIFICACOES_URL),
}

# Serviços conferidos em GET /saude
SERVICOS = {"usuarios": USUARIOS_URL, "inventario": INVENTARIO_URL,
            "chamados": CHAMADOS_URL, "notificacoes": NOTIFICACOES_URL}

# Tempo máximo esperando um serviço responder (o Chamados espera 3 s por outro serviço)
TIMEOUT = float(os.getenv("TIMEOUT_GATEWAY", "8"))

# Tamanho máximo do corpo de uma requisição (em bytes)
TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
