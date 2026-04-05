from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Digital IT Girl", version="0.1.0")


class TechTrend(BaseModel):
    trend_id: str
    name: str
    description: str
    maturity_level: str  # emerging, growing, mature
    impact_score: float = 0.0


# In-memory trends store
trends_store = {}


@app.post("/trends/add")
async def add_trend(trend: TechTrend):
    """Add a new emerging tech trend."""
    trends_store[trend.trend_id] = trend.dict()
    return {"status": "added", "trend_id": trend.trend_id}


@app.get("/trends")
async def list_trends(maturity_level: str = None):
    """List all tech trends with optional filtering."""
    trends = trends_store
    if maturity_level:
        trends = {k: v for k, v in trends.items() if v.get("maturity_level") == maturity_level}
    return {"trends": trends}


@app.get("/trends/{trend_id}")
async def get_trend(trend_id: str):
    """Get details of a specific trend."""
    if trend_id not in trends_store:
        return {"error": "Trend not found"}
    return trends_store[trend_id]


@app.get("/trends/emerging")
async def get_emerging_techs():
    """Get only emerging technologies."""
    emerging = {k: v for k, v in trends_store.items() if v.get("maturity_level") == "emerging"}
    return {"emerging_techs": emerging}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "digital-it-girl"}
