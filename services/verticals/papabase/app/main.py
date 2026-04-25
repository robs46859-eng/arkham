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

# ── Web Suite Models ──────────────────────────────────────────────────────────

class BrandingControl(BaseModel):
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"
    font_family: str = "Inter, sans-serif"
    logo_url: Optional[str] = None
    tone_of_voice: str = "Professional"
    approval_status: str = "pending" # pending | approved | rejected

class WebProject(BaseModel):
    id: str
    lead_id: str
    design_narrative: str = ""
    marketing_copy: str = ""
    html_output: str = ""
    instructions: str = ""
    branding: BrandingControl = Field(default_factory=BrandingControl)
    created_at: str
    status: str = "draft" # drafting | reviewing | ready

# ── MamaNAV & Dad AI Models ───────────────────────────────────────────────────

class TelemetryData(BaseModel):
    device_id: str
    lat: float
    lng: float
    speed: float
    battery: int
    timestamp: str

class DadAIMemory(BaseModel):
    last_known_context: str = "Awaiting signal"
    security_level: str = "standard"
    active_threats: int = 0
    hidden_features_unlocked: bool = False
    
    # Family Life Modules
    reminders: List[Dict[str, str]] = Field(default_factory=list)
    routines: List[str] = Field(default_factory=list)
    grocery_list: List[str] = Field(default_factory=list)
    meal_plan: Dict[str, str] = Field(default_factory=dict)
    budget_status: str = "Healthy"
    dad_jokes_count: int = 0

# ── User & Hierarchy Models ───────────────────────────────────────────────────

class UserRole(str, Enum):
    LEAD = "lead"
    SUB = "sub"

class UserAccount(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: UserRole = UserRole.LEAD
    permissions: List[str] = ["ask_lead"] # Default: Sub-accounts must ask lead
    created_at: str

# ── Business Manager (Chief AI) Models ───────────────────────────────────────

class BusinessInsight(BaseModel):
    title: str
    summary: str
    action_item: str
    impact_level: str # low | medium | high

class ChiefAIMemory(BaseModel):
    business_name: str = "My Family Business"
    revenue_metrics: str = "$0.00 this month"
    lead_velocity: float = 0.0
    strategy_status: str = "Optimization mode"
    business_insights: List[BusinessInsight] = Field(default_factory=list)
    imported_branding_id: Optional[str] = None

# ── Chief AI Expansion ──────────────────────────────────────────────────────

@app.post("/api/business/customize-name")
async def update_business_name(data: dict, x_tenant_id: str = Header(...)):
    name = data.get("name", "My Family Business")
    ref = get_tenant_collection(x_tenant_id, "chief_ai_state").document("memory")
    ref.update({"business_name": name})
    return {"status": "updated", "name": name}

@app.post("/api/business/import-web-data")
async def import_web_data(data: dict, x_tenant_id: str = Header(...)):
    """
    Import branding and narrative from the Presence Engine.
    """
    lead_id = data.get("lead_id")
    # 1. Fetch web project
    docs = get_tenant_collection(x_tenant_id, "web_projects").where("lead_id", "==", lead_id).limit(1).stream()
    web_project = None
    for doc in docs:
        web_project = doc.to_dict()
    
    if not web_project:
        raise HTTPException(status_code=404, detail="No web project found for this lead.")

    # 2. Sync to Chief AI Memory
    ref = get_tenant_collection(x_tenant_id, "chief_ai_state").document("memory")
    ref.update({
        "imported_branding_id": web_project["id"],
        "strategy_status": f"Aligning with {web_project['branding']['tone_of_voice']} brand."
    })
    
    return {"status": "imported", "project_id": web_project["id"]}

# ── Family Insights ──────────────────────────────────────────────────────────

class FamilyInsight(BaseModel):
    subject: str
    insight: str
    dad_advice: str
    is_private_to_lead: bool = True

# ── Web Suite Models ──────────────────────────────────────────────────────────

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

# ── Vertical Integration ─────────────────────────────────────────────────────

@app.post("/api/leads/{lead_id}/trigger/{vertical_id}")
async def trigger_vertical(
    lead_id: str, 
    vertical_id: str, 
    x_tenant_id: str = Header(...),
    authorization: str = Header(...)
):
    """
    Trigger a vertical (AutoPitch, Omniscale, etc) for a specific lead.
    Calls the vertical via the Gateway.
    """
    # 1. Get the lead
    doc = get_tenant_collection(x_tenant_id, "leads").document(lead_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = doc.to_dict()

    # 2. Determine target endpoint and payload based on vertical
    gateway_url = os.environ.get("GATEWAY_URL", "http://gateway:8000")
    target_url = f"{gateway_url}/v1/verticals/{vertical_id}"
    
    payload = {}
    if vertical_id == "autopitch":
        target_url += "/generate"
        payload = {
            "project_name": lead.get("company", "New Project"),
            "project_type": lead.get("offer_type", "Other"),
            "client_name": lead.get("name", "Client"),
            "context": lead.get("notes", "No notes provided"),
            "scope_notes": f"Generated from lead {lead_id}"
        }
    elif vertical_id == "cyberscribe":
        target_url += "/draft"
        payload = {
            "project_id": lead_id,
            "source_material": lead.get("notes", "")
        }
    elif vertical_id == "omniscale":
        target_url += "/review"
        payload = {
            "project_id": lead_id,
            "source_package": lead.get("notes", "")
        }
    elif vertical_id == "ai-consistency":
        target_url += "/check"
        payload = {
            "project_name": lead.get("company", "Project"),
            "sections": [
                {"discipline": "General", "document_type": "Notes", "content": lead.get("notes", "")}
            ]
        }
    elif vertical_id == "presence-engine":
        # Initialize a Web Project inside PapaBase
        project_id = f"web_{uuid.uuid4().hex[:6]}"
        web_project = {
            "id": project_id,
            "lead_id": lead_id,
            "design_narrative": f"Design narrative for {lead.get('company')}...",
            "status": "drafting",
            "created_at": now_iso(),
            "branding": {
                "primary_color": "#1A1A1A",
                "tone_of_voice": "Sophisticated",
                "approval_status": "pending"
            }
        }
        get_tenant_collection(x_tenant_id, "web_projects").document(project_id).set(web_project)
        return web_project
    elif vertical_id == "dad-ai":
        # Initialize Dad AI Memory for this tenant
        memory = {
            "last_known_context": "Dad AI is online. MamaNAV linked.",
            "security_level": "standard",
            "active_threats": 0,
            "hidden_features_unlocked": False,
            "family_insights": [
                {"subject": "Morning Routine", "insight": "Family is moving 15% slower on Tuesdays.", "dad_advice": "Start breakfast 10 mins earlier.", "is_private_to_lead": True}
            ]
        }
        get_tenant_collection(x_tenant_id, "dad_ai_state").document("memory").set(memory)
        return memory
    elif vertical_id == "chief-ai":
        # Initialize Chief AI (Business Manager)
        memory = {
            "revenue_metrics": "$12,400 projected",
            "lead_velocity": 4.2,
            "strategy_status": "Growth focus",
            "business_insights": [
                {"title": "Lead Drift", "summary": "3 high-value leads haven't been contacted in 48h.", "action_item": "Trigger Pursuit Engine for Wayne Ent.", "impact_level": "high"}
            ]
        }
        get_tenant_collection(x_tenant_id, "chief_ai_state").document("memory").set(memory)
        return memory
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported vertical: {vertical_id}")

# ── Chief AI (Business Manager) Routes ────────────────────────────────────────

@app.post("/api/chief-ai/command")
async def chief_ai_command(command: dict, x_tenant_id: str = Header(...)):
    """
    Business Manager AI handles revenue, leads, and strategy.
    """
    cmd_text = command.get("text", "").lower()
    ref = get_tenant_collection(x_tenant_id, "chief_ai_state").document("memory")
    doc = ref.get()
    state = doc.to_dict() if doc.exists else {}

    response = "I'm analyzing the business state. How can I help?"
    
    if "revenue" in cmd_text or "money" in cmd_text:
        response = f"Current revenue metrics: {state.get('revenue_metrics')}. Growth is stable."
    elif "strategy" in cmd_text:
        response = f"Current Strategy: {state.get('strategy_status')}. I recommend focusing on Lead Velocity."
    elif "insight" in cmd_text:
        insights = state.get("business_insights", [])
        if insights:
            i = insights[0]
            response = f"Critical Insight: {i['summary']} Action: {i['action_item']}"
        else:
            response = "No new business insights at this time."

    return {"response": response, "state": state}

@app.get("/api/chief-ai/state")
async def get_chief_ai_state(x_tenant_id: str = Header(...)):
    doc = get_tenant_collection(x_tenant_id, "chief_ai_state").document("memory").get()
    if not doc.exists:
        return {"revenue_metrics": "$0", "strategy_status": "Idle"}
    return doc.to_dict()

# ── User Hierarchy Routes ───────────────────────────────────────────────────

@app.get("/api/family/insights")
async def get_family_insights(x_tenant_id: str = Header(...), x_user_role: str = Header("sub")):
    """
    Retrieve Dad AI insights. restricted to 'lead' role.
    """
    if x_user_role != "lead":
        raise HTTPException(status_code=403, detail="Only the Family-Lead can view private insights.")
    
    doc = get_tenant_collection(x_tenant_id, "dad_ai_state").document("memory").get()
    if not doc.exists:
        return []
    
    return doc.to_dict().get("family_insights", [])

# ── Dad AI & MamaNAV Routes ───────────────────────────────────────────────────

@app.post("/api/mamanav/telemetry")
async def ingest_telemetry(data: TelemetryData, x_tenant_id: str = Header(...)):
    """
    Ingest raw data from the Android app. 
    Dad AI processes it into narrative and discards raw coords.
    """
    # 1. Dad AI Logic: Interpret the coordinates
    # (Mock logic: In reality, compare against geofences)
    context = f"Asset moving at {data.speed} mph. Battery at {data.battery}%."
    if data.speed > 0:
        context = "Asset is currently in transit."
    
    # 2. Update Dad AI Memory (Save context, discard lat/lng)
    ref = get_tenant_collection(x_tenant_id, "dad_ai_state").document("memory")
    ref.update({"last_known_context": context})
    
    return {"status": "ingested", "processed_by": "Dad AI"}

@app.post("/api/dad-ai/command")
async def dad_ai_command(command: dict, x_tenant_id: str = Header(...)):
    """
    Process natural language commands for MamaNAV and Family Hub.
    """
    cmd_text = command.get("text", "").lower()
    ref = get_tenant_collection(x_tenant_id, "dad_ai_state").document("memory")
    doc = ref.get()
    state = doc.to_dict() if doc.exists else {"dad_jokes_count": 0}
    
    response = "I'm on it. What else do you need?"
    
    # 1. Privacy & MamaNAV Intents
    if "where" in cmd_text:
        response = state.get("last_known_context", "I've lost the signal.")
    elif "secure" in cmd_text:
        ref.update({"security_level": "high", "hidden_features_unlocked": True})
        response = "Perimeter secured. Hidden protocols engaged."
    
    # 2. Family Life Intents
    elif "joke" in cmd_text:
        jokes = [
            "I'm afraid for the calendar. Its days are numbered.",
            "My wife said I should stop impersonating a flamingo. I had to put my foot down.",
            "Why did the architect get fired? He was making too many 'lofty' promises."
        ]
        import random
        response = random.choice(jokes)
        ref.update({"dad_jokes_count": state.get("dad_jokes_count", 0) + 1})
        
    elif "meal" in cmd_text or "eat" in cmd_text:
        meal = "How about Grilled Salmon and Asparagus? I've added the ingredients to the grocery list."
        ref.update({
            "meal_plan": {"tonight": "Grilled Salmon"},
            "grocery_list": state.get("grocery_list", []) + ["Salmon", "Asparagus", "Lemon"]
        })
        response = meal
        
    elif "grocery" in cmd_text or "list" in cmd_text:
        items = state.get("grocery_list", [])
        if not items:
            response = "The list is empty. We're looking good."
        else:
            response = f"Current list: {', '.join(items)}."
            
    elif "budget" in cmd_text or "money" in cmd_text:
        response = f"The Family Ledger is {state.get('budget_status', 'Healthy')}. We are currently 12% under budget for the month."
        
    elif "remind" in cmd_text:
        # Simple extraction logic mock
        response = "Reminder set. I'll make sure the family stays on track."
        ref.update({"reminders": state.get("reminders", []) + [{"text": cmd_text, "time": "scheduled"}]})

    return {"response": response, "state": state}

@app.get("/api/dad-ai/state")
async def get_dad_ai_state(x_tenant_id: str = Header(...)):
    doc = get_tenant_collection(x_tenant_id, "dad_ai_state").document("memory").get()
    if not doc.exists:
        return {"last_known_context": "Offline", "security_level": "none"}
    return doc.to_dict()

# ── Web Suite Routes ──────────────────────────────────────────────────────────

@app.get("/api/leads/{lead_id}/web-project")
async def get_web_project(lead_id: str, x_tenant_id: str = Header(...)):
    docs = get_tenant_collection(x_tenant_id, "web_projects").where("lead_id", "==", lead_id).limit(1).stream()
    for doc in docs:
        return doc.to_dict()
    return None

@app.post("/api/web-projects/{project_id}/approve-branding")
async def approve_branding(project_id: str, x_tenant_id: str = Header(...)):
    ref = get_tenant_collection(x_tenant_id, "web_projects").document(project_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Web project not found")
    
    ref.update({"branding.approval_status": "approved", "status": "generating_html"})
    
    # Simulate high-end HTML generation
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>High-End Presence</title></head>
    <body style="background: #1A1A1A; color: white; font-family: Inter;">
        <header><h1>Design. Precision. Presence.</h1></header>
        <main><p>Constructed by the PapaBase Presence Engine.</p></main>
    </body>
    </html>
    """
    
    instructions = """
    ## Usage Instructions
    1. Download the generated 'index.html' file.
    2. Upload it to your root directory on any host (Cloudflare Pages, Vercel, Netlify).
    
    ## Domain & Email Setup
    1. Point your A records to your host's provided IP.
    2. To set up email, use a provider like Google Workspace or Zoho.
    3. Update MX records in your domain dashboard (e.g., GoDaddy, Namecheap) to match your email provider's settings.
    """
    
    ref.update({
        "html_output": html_content,
        "instructions": instructions,
        "status": "ready"
    })
    
    return {"status": "approved", "project_id": project_id}

    # 3. Call the Gateway
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                target_url,
                json=payload,
                headers={
                    "Authorization": authorization,
                    "X-Tenant-ID": x_tenant_id
                }
            )
            resp.raise_for_status()
            result = resp.json()
            
            # Record the integration event
            await record_event(x_tenant_id, "lead", lead_id, "vertical_triggered", {
                "vertical_id": vertical_id,
                "result_id": result.get("id")
            })
            
            return result
    except Exception as exc:
        logger.error("Failed to trigger vertical %s for lead %s", vertical_id, lead_id, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to trigger vertical: {str(exc)}")
