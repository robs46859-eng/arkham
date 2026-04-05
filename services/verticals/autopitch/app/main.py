from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AutoPitch", version="0.1.0")


class IdeaPitch(BaseModel):
    title: str
    description: str
    category: str
    priority: str = "medium"


# In-memory ideas store
ideas_store = {}


@app.post("/ideas/pitch")
async def submit_pitch(pitch: IdeaPitch):
    """Submit a new idea pitch."""
    idea_id = f"idea_{len(ideas_store) + 1}"
    ideas_store[idea_id] = pitch.dict()
    return {"idea_id": idea_id, "status": "submitted"}


@app.get("/ideas")
async def list_ideas(category: str | None = None, priority: str | None = None):
    """List all idea pitches with optional filtering."""
    ideas = ideas_store
    if category:
        ideas = {k: v for k, v in ideas.items() if v.get("category") == category}
    if priority:
        ideas = {k: v for k, v in ideas.items() if v.get("priority") == priority}
    return {"ideas": ideas}


@app.get("/ideas/{idea_id}")
async def get_idea(idea_id: str):
    """Get details of a specific idea."""
    if idea_id not in ideas_store:
        return {"error": "Idea not found"}
    return ideas_store[idea_id]


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "autopitch"}
