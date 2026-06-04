import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import Response
from starlette.types import Scope

from app.database import init_db
from app.routers import export, health, portfolios, signals, telegram, trades
from app.services import telegram_bot_service


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    polling_task = asyncio.create_task(telegram_bot_service.start_polling())
    yield
    telegram_bot_service.stop_polling()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Stock Portfolio Tracker", version="0.1.0", lifespan=lifespan)

app.include_router(health.router, tags=["health"])
app.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
app.include_router(trades.router, prefix="/portfolios", tags=["trades"])
app.include_router(export.router, prefix="/portfolios", tags=["export"])
app.include_router(signals.router, prefix="/portfolios", tags=["signals"])
app.include_router(telegram.router, prefix="/portfolios", tags=["telegram"])

Instrumentator().instrument(app).expose(app)  # /metrics — Agent 3 buraya scrape edecek

# Eski UI (korunur)
app.mount("/ui", NoCacheStaticFiles(directory="static", html=True), name="ui")
# Yeni UI
app.mount("/app", NoCacheStaticFiles(directory="static/app", html=True), name="app")
