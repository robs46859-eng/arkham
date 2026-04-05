from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Workflow Architect", version="0.1.0")


class WorkflowStep(BaseModel):
    step_id: str
    action: str
    parameters: Dict = {}
    dependencies: List[str] = []


class WorkflowPlan(BaseModel):
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    metadata: Dict = {}


# In-memory workflow store
workflows_store = {}


@app.post("/workflows/design")
async def design_workflow(plan: WorkflowPlan):
    """Design a new workflow."""
    workflows_store[plan.workflow_id] = plan.dict()
    return {"status": "designed", "workflow_id": plan.workflow_id}


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details."""
    if workflow_id not in workflows_store:
        return {"error": "Workflow not found"}
    return workflows_store[workflow_id]


@app.post("/workflows/{workflow_id}/validate")
async def validate_workflow(workflow_id: str):
    """Validate workflow structure."""
    if workflow_id not in workflows_store:
        return {"error": "Workflow not found"}

    workflow = workflows_store[workflow_id]
    is_valid = len(workflow.get("steps", [])) > 0
    return {"valid": is_valid, "issues": [] if is_valid else ["No steps defined"]}


@app.get("/workflows")
async def list_workflows():
    """List all workflows."""
    return {"workflows": list(workflows_store.keys())}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "workflow-architect"}
