"""FastAPI app entry point."""
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_export, routes_fares, routes_index, routes_status
from app.db import ENGINES, init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    for eng in ENGINES.values():
        init_db(eng)
    yield


# Dashboard origins; override with a comma-separated GARUDA_CORS_ORIGINS.
CORS_ORIGINS = os.environ.get("GARUDA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app = FastAPI(title="GARUDA", description="Real-time Airfare Price Index", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
app.include_router(routes_index.router)
app.include_router(routes_fares.router)
app.include_router(routes_export.router)
app.include_router(routes_status.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
