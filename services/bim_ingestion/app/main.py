from fastapi import FastAPI

app = FastAPI(title="Robco BIM Ingestion")

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    config = settings
    return HealthResponse(
        status="ok",
        service=config.service_name,
        environment=config.app_env,
    )
