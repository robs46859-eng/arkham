"""
Unified Config Router
Centralized configuration management for all services and verticals.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter()

# In-memory config store (will be replaced with Redis/DB in production)
config_store: Dict[str, Dict[str, Any]] = {
    "core": {
        "enabled_verticals": [],
        "max_concurrent_workflows": 10,
        "default_privacy_tier": "dev"
    },
    "verticals": {}
}


class ConfigUpdate(BaseModel):
    section: str
    key: str
    value: Any


class VerticalConfig(BaseModel):
    vertical_id: str
    enabled: bool = True
    config: Dict[str, Any] = {}


@router.get("/config", response_model=Dict[str, Any])
async def get_config(section: Optional[str] = None):
    """Get configuration, optionally filtered by section."""
    if section:
        if section not in config_store:
            raise HTTPException(status_code=404, detail=f"Section '{section}' not found")
        return {section: config_store[section]}
    return config_store


@router.put("/config", response_model=dict)
async def update_config(update: ConfigUpdate):
    """Update a specific configuration value."""
    if update.section not in config_store:
        config_store[update.section] = {}
    
    config_store[update.section][update.key] = update.value
    return {"status": "updated", "section": update.section, "key": update.key}


@router.post("/verticals", response_model=dict)
async def register_vertical(config: VerticalConfig):
    """Register or update a vertical configuration."""
    config_store["verticals"][config.vertical_id] = {
        "enabled": config.enabled,
        "config": config.config
    }
    
    # Update enabled_verticals list
    if config.enabled and config.vertical_id not in config_store["core"]["enabled_verticals"]:
        config_store["core"]["enabled_verticals"].append(config.vertical_id)
    elif not config.enabled and config.vertical_id in config_store["core"]["enabled_verticals"]:
        config_store["core"]["enabled_verticals"].remove(config.vertical_id)
    
    return {"status": "registered", "vertical_id": config.vertical_id}


@router.get("/verticals", response_model=Dict[str, Any])
async def list_verticals(enabled_only: bool = False):
    """List all vertical configurations."""
    verticals = config_store["verticals"]
    if enabled_only:
        verticals = {k: v for k, v in verticals.items() if v.get("enabled", False)}
    return verticals


@router.get("/verticals/{vertical_id}", response_model=Dict[str, Any])
async def get_vertical(vertical_id: str):
    """Get configuration for a specific vertical."""
    if vertical_id not in config_store["verticals"]:
        raise HTTPException(status_code=404, detail=f"Vertical '{vertical_id}' not found")
    return config_store["verticals"][vertical_id]


@router.delete("/verticals/{vertical_id}")
async def unregister_vertical(vertical_id: str):
    """Remove a vertical configuration."""
    if vertical_id not in config_store["verticals"]:
        raise HTTPException(status_code=404, detail=f"Vertical '{vertical_id}' not found")
    
    del config_store["verticals"][vertical_id]
    if vertical_id in config_store["core"]["enabled_verticals"]:
        config_store["core"]["enabled_verticals"].remove(vertical_id)
    
    return {"status": "unregistered", "vertical_id": vertical_id}
