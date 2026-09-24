"""FastAPI app entry point."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_export, routes_fares, routes_index
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="GARUDA", description="Real-time Airfare Price Index", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
app.include_router(routes_index.router)
app.include_router(routes_fares.router)
app.include_router(routes_export.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
