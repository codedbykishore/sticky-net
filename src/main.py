"""FastAPI application entry point."""

from fastapi import FastAPI

from src.api.routes import router
from src.api.middleware import setup_middleware

app = FastAPI(
    title="Sticky-Net",
    description="AI Agentic Honey-Pot for Scam Detection",
    version="0.1.0",
)

setup_middleware(app)
app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
