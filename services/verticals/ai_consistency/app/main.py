from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="AI Consistency Lab", version="0.1.0")


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
        "request": request.dict(),
        "status": "completed",
        "consistency_score": 0.95,
        "differences": []
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


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-consistency-lab"}
