"""FastAPI app entry point."""
from fastapi import FastAPI

app = FastAPI(title="GARUDA", description="Real-time Airfare Price Index")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
