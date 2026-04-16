from pydantic import BaseModel

from packages.vertical_base import VerticalBase

vertical = VerticalBase(
    service_id="public-beta",
    title="PublicBeta",
    port=8000,
    capabilities=["feature_preview", "beta_management", "release_toggles"],
    event_subscriptions=[],
)

app = vertical.app


class FeaturePreview(BaseModel):
    feature_id: str
    name: str
    description: str
    enabled: bool = False


# In-memory features store
features_store = {}


@app.post("/features/preview")
async def create_preview(feature: FeaturePreview):
    """Create a feature preview for beta testing."""
    features_store[feature.feature_id] = feature.model_dump()
    return {"status": "created", "feature_id": feature.feature_id}


@app.get("/features/previews")
async def list_previews(enabled_only: bool = False):
    """List all feature previews."""
    previews = features_store
    if enabled_only:
        previews = {k: v for k, v in previews.items() if v.get("enabled", False)}
    return {"previews": previews}


@app.put("/features/{feature_id}/toggle")
async def toggle_feature(feature_id: str):
    """Toggle feature availability."""
    if feature_id not in features_store:
        return {"error": "Feature not found"}

    features_store[feature_id]["enabled"] = not features_store[feature_id]["enabled"]
    return {"feature_id": feature_id, "enabled": features_store[feature_id]["enabled"]}
