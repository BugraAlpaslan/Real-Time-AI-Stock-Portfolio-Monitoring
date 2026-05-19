from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import init_db
from app.routers import export, health, portfolios, trades


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Stock Portfolio Tracker", version="0.1.0", lifespan=lifespan)

app.include_router(health.router, tags=["health"])
app.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
app.include_router(trades.router, prefix="/portfolios", tags=["trades"])
app.include_router(export.router, prefix="/portfolios", tags=["export"])

Instrumentator().instrument(app).expose(app)  # /metrics — Agent 3 buraya scrape edecek

# Agent 3: static/ hazır — UI mount aktif
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")
