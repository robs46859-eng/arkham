from uuid import uuid4
from typing import Any

from pydantic import BaseModel, Field

from packages.vertical_base import VerticalBase

vertical = VerticalBase(
    service_id="workflow-architect",
    title="Workflow Architect",
    port=8000,
    capabilities=["workflow_design", "workflow_validation", "planning"],
    event_subscriptions=[],
)

app = vertical.app


class WorkflowStep(BaseModel):
    step_id: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class WorkflowPlan(BaseModel):
    workflow_id: str
    name: str
    steps: list[WorkflowStep]
    metadata: dict[str, Any] = Field(default_factory=dict)


class SalesToCashRequest(BaseModel):
    workflow_id: str | None = None
    customer_name: str = "New prospect"
    offer_name: str = "Robco pilot"
    amount_usd: int | None = None
    target_customer_profile: str | None = None
    lead_source: str | None = None
    outreach_channel: str = "email"
    outreach_provider: str | None = None
    daily_send_limit: int = 25
    follow_up_days: list[int] = Field(default_factory=lambda: [2, 5, 10])
    product_url: str | None = None
    payment_url: str | None = None
    success_url: str | None = None


def build_sales_to_cash_workflow(request: SalesToCashRequest) -> WorkflowPlan:
    """Create the default sales workflow for closing and collecting payment."""
    workflow_id = request.workflow_id or f"wf_sales_{uuid4().hex}"
    missing_connectors = []
    if not request.lead_source:
        missing_connectors.append("lead_source")
    if not request.outreach_provider:
        missing_connectors.append("outreach_provider")
    if not request.payment_url:
        missing_connectors.append("payment_url")

    return WorkflowPlan(
        workflow_id=workflow_id,
        name="Automated Sales to Cash",
        steps=[
            WorkflowStep(
                step_id="source_leads",
                action="pull_leads_from_configured_source",
                parameters={
                    "lead_source": request.lead_source,
                    "target_customer_profile": request.target_customer_profile,
                    "required_fields": ["name", "company", "contact", "fit_signal"],
                },
            ),
            WorkflowStep(
                step_id="qualify",
                action="score_leads_for_offer_fit",
                parameters={
                    "offer_name": request.offer_name,
                    "criteria": ["budget", "authority", "urgency", "deliverable_fit"],
                },
                dependencies=["source_leads"],
            ),
            WorkflowStep(
                step_id="draft_outreach",
                action="generate_personalized_outreach",
                parameters={
                    "channel": request.outreach_channel,
                    "product_url": request.product_url,
                    "amount_usd": request.amount_usd,
                    "message_rules": ["short", "specific", "plain_language", "include_payment_link_only_after_interest"],
                },
                dependencies=["qualify"],
            ),
            WorkflowStep(
                step_id="send_outreach",
                action="send_outreach_via_provider",
                parameters={
                    "channel": request.outreach_channel,
                    "provider": request.outreach_provider,
                    "daily_send_limit": request.daily_send_limit,
                },
                dependencies=["draft_outreach"],
            ),
            WorkflowStep(
                step_id="follow_up",
                action="schedule_automated_follow_ups",
                parameters={
                    "days_after_initial_send": request.follow_up_days,
                    "stop_conditions": ["reply_received", "payment_completed", "unsubscribe"],
                },
                dependencies=["send_outreach"],
            ),
            WorkflowStep(
                step_id="interested_reply",
                action="detect_interested_reply",
                parameters={
                    "signals": ["pricing_question", "demo_request", "buying_intent", "positive_response"],
                },
                dependencies=["send_outreach"],
            ),
            WorkflowStep(
                step_id="send_payment_link",
                action="send_existing_payment_link" if request.payment_url else "create_stripe_checkout_session",
                parameters={
                    "billing_endpoint": "/billing/checkout",
                    "product_url": request.product_url,
                    "payment_url": request.payment_url,
                    "success_url": request.success_url,
                },
                dependencies=["interested_reply"],
            ),
            WorkflowStep(
                step_id="payment_confirmed",
                action="wait_for_stripe_webhook",
                parameters={
                    "event": "checkout.session.completed",
                    "result": "mark_customer_paid",
                },
                dependencies=["send_payment_link"],
            ),
            WorkflowStep(
                step_id="onboarding",
                action="start_paid_customer_onboarding",
                parameters={
                    "handoff": ["create_tenant", "create_project", "schedule_kickoff", "open_delivery_task"],
                },
                dependencies=["payment_confirmed"],
            ),
        ],
        metadata={
            "template": "sales-to-cash",
            "customer_name": request.customer_name,
            "offer_name": request.offer_name,
            "target_customer_profile": request.target_customer_profile,
            "lead_source": request.lead_source,
            "outreach_channel": request.outreach_channel,
            "outreach_provider": request.outreach_provider,
            "payment_provider": "stripe",
            "product_url": request.product_url,
            "payment_url": request.payment_url,
            "automation_ready": not missing_connectors,
            "missing_connectors": missing_connectors,
            "status": "ready" if not missing_connectors else "needs_configuration",
        },
    )


# In-memory workflow store
workflows_store = {}


@app.post("/workflows/design")
async def design_workflow(plan: WorkflowPlan):
    """Design a new workflow."""
    workflows_store[plan.workflow_id] = plan.model_dump()
    return {"status": "designed", "workflow_id": plan.workflow_id}


@app.get("/workflows/templates/sales-to-cash")
async def get_sales_to_cash_template():
    """Preview the default workflow for making a sale and collecting payment."""
    return build_sales_to_cash_workflow(SalesToCashRequest()).model_dump()


@app.post("/workflows/templates/sales-to-cash")
async def design_sales_to_cash_workflow(request: SalesToCashRequest):
    """Create a sales-to-cash workflow draft from the default template."""
    plan = build_sales_to_cash_workflow(request)
    workflows_store[plan.workflow_id] = plan.model_dump()
    return {"status": "designed", "workflow_id": plan.workflow_id, "workflow": workflows_store[plan.workflow_id]}


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
