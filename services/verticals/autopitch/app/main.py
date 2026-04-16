from pydantic import BaseModel

from packages.vertical_base import VerticalBase

vertical = VerticalBase(
    service_id="autopitch",
    title="AutoPitch",
    port=8000,
    capabilities=["idea_submission", "pitch_tracking", "prioritization"],
    event_subscriptions=[],
)

app = vertical.app


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
    ideas_store[idea_id] = pitch.model_dump()
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
