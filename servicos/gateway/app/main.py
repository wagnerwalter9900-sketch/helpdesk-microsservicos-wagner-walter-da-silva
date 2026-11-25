"""API Gateway do HelpDesk TI.

É o único ponto de entrada (porta 8000) e o único contêiner com porta exposta.
Serve a tela e encaminha cada rota para o serviço certo:

    /auth/...  e /usuarios/...  -> serviço de Usuários
    /ativos/...                  -> serviço de Inventário
    /chamados/...                -> serviço de Chamados
    /notificacoes/...            -> serviço de Notificações

O gateway não confere o token: ele repassa o cabeçalho Authorization e cada
serviço confere sozinho (assim, nenhum serviço confia cegamente no gateway).
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from app.config import ROTAS, SERVICOS, TIMEOUT
from app.seguranca_http import CabecalhosDeSeguranca

WEB = Path(__file__).parent / "web"

# Cabeçalhos que passam do navegador para o serviço, e do serviço para o navegador
CABECALHOS_IDA = ("authorization", "content-type", "accept")
CABECALHOS_VOLTA = ("content-type", "www-authenticate")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Um cliente HTTP só, reaproveitado em todas as requisições
    app.state.http = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False)
    yield
    await app.state.http.aclose()


app = FastAPI(title="HelpDesk TI · API Gateway", version="3.0.0", lifespan=ciclo_de_vida,
              docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CabecalhosDeSeguranca)


# ---------- tela ----------

@app.get("/", include_in_schema=False)
def tela_inicial():
    return FileResponse(WEB / "index.html")


@app.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(WEB / "app.js", media_type="text/javascript")


@app.get("/estilo.css", include_in_schema=False)
def estilo():
    return FileResponse(WEB / "estilo.css", media_type="text/css")


# ---------- saúde ----------

@app.get("/saude")
async def saude(request: Request):
    """Mostra quais serviços estão no ar."""
    async def checar(url: str) -> str:
        try:
            r = await request.app.state.http.get(f"{url}/saude", timeout=2)
            return "no ar" if r.status_code == 200 else f"com problema ({r.status_code})"
        except httpx.RequestError:
            return "fora do ar"

    resultados = await asyncio.gather(*(checar(url) for url in SERVICOS.values()))
    return {"gateway": "no ar", "servicos": dict(zip(SERVICOS, resultados))}


# ---------- encaminhamento ----------

@app.api_route("/{servico}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
@app.api_route("/{servico}/{resto:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def encaminhar(servico: str, request: Request, resto: str = ""):
    if servico not in ROTAS:
        return JSONResponse(status_code=404, content={"detail": "Rota não encontrada."})
    nome, destino = ROTAS[servico]
    url = f"{destino}/{servico}" + (f"/{resto}" if resto else "")

    cabecalhos = {k: v for k, v in request.headers.items() if k.lower() in CABECALHOS_IDA}
    # Informa o IP de quem fez o pedido (usado no limite de tentativas de login)
    if request.client:
        cabecalhos["x-forwarded-for"] = request.client.host

    try:
        resposta = await request.app.state.http.request(
            request.method, url, params=request.query_params, content=await request.body(), headers=cabecalhos,
        )
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"detail": f"O serviço de {nome} demorou demais para responder."})
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": f"O serviço de {nome} está fora do ar. Tente de novo em instantes."})

    volta = {k: v for k, v in resposta.headers.items() if k.lower() in CABECALHOS_VOLTA}
    return Response(content=resposta.content, status_code=resposta.status_code, headers=volta)
