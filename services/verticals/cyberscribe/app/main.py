from pydantic import BaseModel
from typing import List, Dict

from packages.vertical_base import VerticalBase

vertical = VerticalBase(
    service_id="cyberscribe",
    title="CyberScribe",
    port=8000,
    capabilities=["code_analysis", "anomaly_detection", "recommendations"],
    event_subscriptions=[],
)

app = vertical.app


class CodeSnippet(BaseModel):
    code: str
    language: str = "python"
    context: Dict = {}


class AnomalyReport(BaseModel):
    snippet_id: str
    anomalies: List[Dict]
    severity: str
    recommendations: List[str]


# In-memory analysis store
analyses_store = {}


@app.post("/code/analyze")
async def analyze_code(snippet: CodeSnippet):
    """Analyze code for anomalies."""
    snippet_id = f"snippet_{len(analyses_store) + 1}"
    analyses_store[snippet_id] = {
        "code": snippet.code,
        "language": snippet.language,
        "anomalies": [],
        "severity": "low",
        "recommendations": [],
    }
    return {"snippet_id": snippet_id, "status": "analyzed"}


@app.get("/code/{snippet_id}/report")
async def get_anomaly_report(snippet_id: str):
    """Get anomaly report for analyzed code."""
    if snippet_id not in analyses_store:
        return {"error": "Analysis not found"}
    return analyses_store[snippet_id]


@app.get("/code")
async def list_analyses():
    """List all code analyses."""
    return {"analyses": list(analyses_store.keys())}
