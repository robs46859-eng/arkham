from fastapi import FastAPI

from packages.schemas import HealthResponse
from .settings import settings

app = FastAPI(title="Robco Orchestration")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    config = settings
    return HealthResponse(
        status="ok",
        service=config.service_name,
        environment=config.app_env,
    )
