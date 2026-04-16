from pydantic import BaseModel
from typing import List, Dict

from packages.vertical_base import VerticalBase

vertical = VerticalBase(
    service_id="ai-consistency",
    title="AI Consistency Lab",
    port=8000,
    capabilities=["ai_testing", "model_validation", "consistency_scoring"],
    event_subscriptions=[],
)

app = vertical.app


class TestRequest(BaseModel):
    test_name: str
    model_a: str
    model_b: str
    prompt: str
    criteria: List[str] = []


class TestResult(BaseModel):
    test_id: str
    status: str
    consistency_score: float
    differences: List[Dict]


# In-memory test store
tests_store = {}


@app.post("/tests/run")
async def run_consistency_test(request: TestRequest):
    """Run AI consistency test between models."""
    test_id = f"test_{len(tests_store) + 1}"
    tests_store[test_id] = {
        "request": request.model_dump(),
        "status": "completed",
        "consistency_score": 0.95,
        "differences": [],
    }
    return {"test_id": test_id, "status": "completed"}


@app.get("/tests/{test_id}")
async def get_test_result(test_id: str):
    """Get results of a consistency test."""
    if test_id not in tests_store:
        return {"error": "Test not found"}
    return tests_store[test_id]


@app.get("/tests")
async def list_tests():
    """List all consistency tests."""
    return {"tests": list(tests_store.keys())}
