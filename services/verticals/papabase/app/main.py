"""
PapaBase — Lead and Delivery CRM Vertical.
Provides tenant-scoped lead intake, pipeline tracking, and task management.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, Field

from packages.vertical_base import VerticalBase

# ── Initialization ───────────────────────────────────────────────────────────

vertical = VerticalBase(
    service_id="papabase",
    title="PapaBase — CRM & Delivery",
    port=8000,
    capabilities=["lead_management", "task_tracking", "pipeline_ops"],
    event_subscriptions=["lead.created", "task.completed"],
)

app = vertical.app

# ── Persistence ──────────────────────────────────────────────────────────────

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

FIRESTORE_DATABASE = os.environ.get("FIRESTORE_DATABASE", "(default)")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "arkham-492414")

def get_db():
    if firestore is None:
        raise RuntimeError("google-cloud-firestore is not installed")
    return firestore.Client(project=GOOGLE_CLOUD_PROJECT, database=FIRESTORE_DATABASE)

def get_tenant_collection(tenant_id: str, collection_name: str):
    """Scope every collection by tenant_id for multi-tenancy."""
    db = get_db()
    return db.collection("tenants").document(tenant_id).collection(collection_name)

# ── Models ───────────────────────────────────────────────────────────────────

class User(BaseModel):
    id: str
    name: str
    role: str = "operator"
    created_at: str

class Lead(BaseModel):
    id: str
    name: str
    company: str
    offer_type: str = "Other"
    status: str = "lead"
    source: str = "operator"
    phone: str = ""
    email: str = ""
    notes: str = ""
    next_action: str = "Follow up"
    created_at: str
    updated_at: Optional[str] = None

class Task(BaseModel):
    id: str
    lead_id: str
    description: str
    status: str = "todo"
    owner: str = "operator"
    due: str = ""
    created_at: str
    updated_at: Optional[str] = None

# ── Helpers ──────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

async def record_event(tenant_id: str, entity_type: str, entity_id: str, action: str, details: dict):
    event = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "timestamp": now_iso(),
        "details": details
    }
    get_tenant_collection(tenant_id, "events").document(event["id"]).set(event)
    await vertical.publish_event(f"{entity_type}.{action}", {**event, "tenant_id": tenant_id})

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def papabase_health(x_tenant_id: Optional[str] = Header(None)):
    return {
        "service": "papabase",
        "ok": True,
        "firestore_database": FIRESTORE_DATABASE,
        "tenant_id": x_tenant_id,
        "storage": "firestore",
        "pipeline_stages": ["lead", "qualified", "quote", "scheduled", "delivery", "invoiced", "done"],
        "offer_types": ["Proposal Sprint", "Scope + Spec Starter", "Coordination Risk Review", "Other"]
    }

@app.post("/api/users")
async def create_user(data: dict, x_tenant_id: str = Header(...)):
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "name": data.get("name", "Unknown Operator"),
        "role": data.get("role", "operator"),
        "created_at": now_iso()
    }
    get_tenant_collection(x_tenant_id, "users").document(user_id).set(user)
    return user

@app.get("/api/leads")
async def list_leads(x_tenant_id: str = Header(...)):
    docs = get_tenant_collection(x_tenant_id, "leads").order_by("created_at", direction="DESCENDING").stream()
    return [doc.to_dict() for doc in docs]

@app.post("/api/leads")
async def create_lead(data: dict, x_tenant_id: str = Header(...)):
    lead_id = str(uuid.uuid4())
    lead = {
        "id": lead_id,
        "name": data.get("name", ""),
        "company": data.get("company", ""),
        "offer_type": data.get("offer_type", "Other"),
        "status": "lead",
        "source": data.get("source", "operator"),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "notes": data.get("notes", ""),
        "next_action": "Follow up",
        "created_at": now_iso()
    }
    get_tenant_collection(x_tenant_id, "leads").document(lead_id).set(lead)
    await record_event(x_tenant_id, "lead", lead_id, "created", {"company": lead["company"]})
    return lead

@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: str, x_tenant_id: str = Header(...)):
    doc = get_tenant_collection(x_tenant_id, "leads").document(lead_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Lead not found")
    return doc.to_dict()

@app.patch("/api/leads/{lead_id}")
async def update_lead(lead_id: str, data: dict, x_tenant_id: str = Header(...)):
    ref = get_tenant_collection(x_tenant_id, "leads").document(lead_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    current = doc.to_dict()
    updates = {k: v for k, v in data.items() if k in [
        "name", "company", "offer_type", "status", "phone", "email", "notes", "next_action"
    ]}
    updates["updated_at"] = now_iso()
    ref.update(updates)
    
    if "status" in updates and updates["status"] != current.get("status"):
        await record_event(x_tenant_id, "lead", lead_id, "status_changed", {
            "from": current.get("status"),
            "to": updates["status"]
        })
        
    return {**current, **updates}

@app.get("/api/tasks")
async def list_tasks(lead_id: Optional[str] = None, x_tenant_id: str = Header(...)):
    coll = get_tenant_collection(x_tenant_id, "tasks")
    if lead_id:
        docs = coll.where("lead_id", "==", lead_id).stream()
    else:
        docs = coll.order_by("created_at", direction="DESCENDING").stream()
    return [doc.to_dict() for doc in docs]

@app.post("/api/tasks")
async def create_task(data: dict, x_tenant_id: str = Header(...)):
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "lead_id": data.get("lead_id"),
        "description": data.get("description", ""),
        "status": "todo",
        "owner": data.get("owner", "operator"),
        "due": data.get("due", ""),
        "created_at": now_iso()
    }
    if not task["lead_id"]:
        raise HTTPException(status_code=400, detail="lead_id is required")
        
    get_tenant_collection(x_tenant_id, "tasks").document(task_id).set(task)
    await record_event(x_tenant_id, "task", task_id, "created", {"lead_id": task["lead_id"]})
    return task

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, data: dict, x_tenant_id: str = Header(...)):
    ref = get_tenant_collection(x_tenant_id, "tasks").document(task_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")
        
    current = doc.to_dict()
    updates = {k: v for k, v in data.items() if k in ["description", "status", "owner", "due"]}
    updates["updated_at"] = now_iso()
    ref.update(updates)
    
    if "status" in updates and updates["status"] != current.get("status"):
        await record_event(x_tenant_id, "task", task_id, "status_changed", {
            "from": current.get("status"),
            "to": updates["status"]
        })
        
    return {**current, **updates}

@app.get("/api/events")
async def list_events(lead_id: Optional[str] = None, x_tenant_id: str = Header(...)):
    coll = get_tenant_collection(x_tenant_id, "events")
    if lead_id:
        docs = coll.where("entity_id", "==", lead_id).stream()
    else:
        docs = coll.order_by("timestamp", direction="DESCENDING").limit(50).stream()
    return [doc.to_dict() for doc in docs]
