"""
Media & Commerce Service

FastAPI service for the Unified AI Command Center vertical.
Implements the 13-entity shared data model with autonomous agents.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.settings import settings
from app.agents import (
    ContentEngineAgent,
    DealFlowAgent,
    FulfillmentOpsAgent,
    ComplianceGateAgent,
    ChiefPulseAgent,
    BudgetMindAgent,
    BoardReadyAgent,
    MediaCommerceAgent,
)

logger = logging.getLogger(__name__)


class ContentStrategyRequest(BaseModel):
    tenant_id: str
    vertical: str
    topic: str
    goals: list[str] = Field(default_factory=list)


class LeadRoutingRequest(BaseModel):
    tenant_id: str
    lead_id: str
    intent_signals: list[str] = Field(min_length=1)


class EPCMonitoringRequest(BaseModel):
    tenant_id: str
    content_id: str = None
    vertical: str = None


class PageOptimizationRequest(BaseModel):
    tenant_id: str
    page_id: str
    page_type: str = "landing_page"


class ABTestRequest(BaseModel):
    tenant_id: str
    page_id: str
    variant_config: dict = Field(default_factory=dict)


class AnalyticsTrackingRequest(BaseModel):
    tenant_id: str
    event_type: str
    tracking_config: dict = Field(default_factory=dict)


class EPCMonitoringRequest(BaseModel):
    tenant_id: str
    content_id: str = None
    vertical: str = None


class ContentOptimizationRequest(BaseModel):
    tenant_id: str
    content_id: str


class AffiliatePlacementRequest(BaseModel):
    tenant_id: str
    content_id: str
    new_placement: dict = Field(default_factory=dict)


class ContentRepurposeRequest(BaseModel):
    tenant_id: str
    content_id: str
    target_formats: list[str] = Field(default_factory=lambda: ["social", "email"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Media & Commerce Service")
    
    # Initialize all agents
    app.state.content_engine = ContentEngineAgent(settings.gateway_url)
    app.state.deal_flow = DealFlowAgent(settings.gateway_url)
    app.state.fulfillment_ops = FulfillmentOpsAgent(settings.gateway_url)
    app.state.compliance_gate = ComplianceGateAgent(settings.gateway_url)
    app.state.chief_pulse = ChiefPulseAgent(settings.gateway_url)
    app.state.budget_mind = BudgetMindAgent(settings.gateway_url)
    app.state.board_ready = BoardReadyAgent(settings.gateway_url)
    app.state.media_commerce = MediaCommerceAgent(settings.gateway_url)
    
    logger.info("All agents initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Media & Commerce Service")


app = FastAPI(
    title="Media & Commerce Service",
    description="Unified AI Command Center - Media & Commerce Vertical",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "media-commerce"}


@app.get("/ready")
async def ready_check():
    """Readiness check endpoint"""
    if not hasattr(app.state, "content_engine"):
        return {"status": "not ready", "reason": "agents not initialized"}
    return {"status": "ready"}


# ContentEngine endpoints
@app.post("/api/v1/content/strategy")
async def create_content_strategy(request: ContentStrategyRequest):
    """Create content strategy"""
    agent = app.state.content_engine
    result = await agent.create_content_strategy(
        tenant_id=request.tenant_id,
        vertical=request.vertical,
        topic=request.topic,
        goals=request.goals,
    )
    return result


@app.post("/api/v1/content/strategy/workflow")
async def submit_content_strategy_workflow(request: ContentStrategyRequest):
    """Submit content strategy generation into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "media_content_strategy",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "vertical": request.vertical,
            "topic": request.topic,
            "goals": request.goals,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": request.vertical,
            "requested_capability": "content_strategy",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "media_content_strategy",
        "workflow": workflow_response,
    }


@app.post("/api/v1/content/generate")
async def generate_content(request: ContentStrategyRequest):
    """Generate content"""
    agent = app.state.content_engine
    result = await agent.generate_content(
        tenant_id=request.tenant_id,
        vertical=request.vertical,
        content_type="article",
        topic=request.topic,
        keywords=[],
    )
    return result


@app.post("/api/v1/content/optimize-ai-seo")
async def optimize_for_ai_search(tenant_id: str, content_id: str):
    """Optimize content for AI search"""
    agent = app.state.content_engine
    result = await agent.optimize_for_ai_search(tenant_id, content_id)
    return result


# DealFlow endpoints
@app.post("/api/v1/leads/route")
async def route_lead(request: LeadRoutingRequest):
    """Route lead to highest-LTV vertical (Scenario 5)"""
    agent = app.state.deal_flow
    try:
        result = await agent.route_lead(
            tenant_id=request.tenant_id,
            lead_id=request.lead_id,
            intent_signals=request.intent_signals,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@app.post("/api/v1/leads/route/workflow")
async def submit_lead_routing_workflow(request: LeadRoutingRequest):
    """Submit lead routing into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "dealflow_lead_routing",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "lead_id": request.lead_id,
            "intent_signals": request.intent_signals,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "lead_routing",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "dealflow_lead_routing",
        "workflow": workflow_response,
    }


@app.post("/api/v1/deals/proposal")
async def generate_proposal(tenant_id: str, deal_id: str):
    """Generate proposal"""
    agent = app.state.deal_flow
    result = await agent.generate_proposal(tenant_id, deal_id)
    return result


# FulfillmentOps endpoints
@app.post("/api/v1/cro/optimize-page")
async def optimize_page(tenant_id: str, page_id: str, page_type: str):
    """Optimize page for conversions"""
    agent = app.state.fulfillment_ops
    result = await agent.optimize_page(tenant_id, page_id, page_type)
    return result


@app.post("/api/v1/cro/optimize-page/workflow")
async def submit_page_cro_workflow(request: PageOptimizationRequest):
    """Submit page CRO optimization into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "page_cro_optimization",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "page_id": request.page_id,
            "page_type": request.page_type,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "page_cro",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "page_cro_optimization",
        "workflow": workflow_response,
    }


@app.post("/api/v1/cro/ab-test/workflow")
async def submit_ab_test_workflow(request: ABTestRequest):
    """Submit A/B test setup into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "ab_test_lifecycle",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "page_id": request.page_id,
            "variant_config": request.variant_config,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "ab_test",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "ab_test_lifecycle",
        "workflow": workflow_response,
    }


@app.post("/api/v1/analytics/track/workflow")
async def submit_analytics_tracking_workflow(request: AnalyticsTrackingRequest):
    """Submit analytics tracking setup into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "analytics_tracking_setup",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "event_type": request.event_type,
            "tracking_config": request.tracking_config,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "analytics_tracking",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "analytics_tracking_setup",
        "workflow": workflow_response,
    }


@app.post("/api/v1/cro/setup-ab-test")
async def setup_ab_test(tenant_id: str, page_id: str, variant_config: dict):
    """Set up A/B test"""
    agent = app.state.fulfillment_ops
    result = await agent.setup_ab_test(tenant_id, page_id, variant_config)
    return result


# MediaCommerce endpoints
@app.post("/api/v1/epc/monitor")
async def monitor_epc(request: EPCMonitoringRequest):
    """Monitor EPC for content assets"""
    agent = app.state.media_commerce
    result = await agent.monitor_epc(
        tenant_id=request.tenant_id,
        content_id=request.content_id,
        vertical=request.vertical,
    )
    return result


@app.post("/api/v1/epc/monitor/workflow")
async def submit_epc_monitoring_workflow(request: EPCMonitoringRequest):
    """Submit EPC monitoring into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "epc_monitoring_loop",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "content_id": request.content_id,
            "vertical": request.vertical,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "epc_monitoring",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "epc_monitoring_loop",
        "workflow": workflow_response,
    }


@app.post("/api/v1/epc/auto-optimize/workflow")
async def submit_content_optimization_workflow(request: ContentOptimizationRequest):
    """Submit content auto-optimization into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "epc_monitoring_loop",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "content_id": request.content_id,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "content_auto_optimize",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "epc_monitoring_loop",
        "workflow": workflow_response,
    }


@app.post("/api/v1/affiliate/optimize/workflow")
async def submit_affiliate_optimization_workflow(request: AffiliatePlacementRequest):
    """Submit affiliate placement optimization into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "affiliate_optimization",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "content_id": request.content_id,
            "new_placement": request.new_placement,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "affiliate_optimization",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "affiliate_optimization",
        "workflow": workflow_response,
    }


@app.post("/api/v1/content/repurpose/workflow")
async def submit_content_repurpose_workflow(request: ContentRepurposeRequest):
    """Submit content repurposing into the horizontal orchestration layer."""
    payload = {
        "workflow_type": "content_repurposing",
        "tenant_id": request.tenant_id,
        "input_data": {
            "tenant_id": request.tenant_id,
            "content_id": request.content_id,
            "target_formats": request.target_formats,
        },
        "metadata": {
            "source_service": settings.service_name,
            "vertical": "media",
            "requested_capability": "content_repurpose",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestration_url}/api/v1/workflows",
                json=payload,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestration service: {exc}",
        ) from exc

    if response.status_code != 200:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestration service rejected workflow submission",
                "upstream_status": response.status_code,
                "upstream_detail": detail,
            },
        )

    workflow_response = response.json()
    return {
        "submitted": True,
        "workflow_type": "content_repurposing",
        "workflow": workflow_response,
    }


@app.post("/api/v1/epc/auto-optimize")
async def auto_optimize_content(tenant_id: str, content_id: str):
    """Auto-optimize content based on EPC"""
    agent = app.state.media_commerce
    result = await agent.auto_optimize_content(tenant_id, content_id)
    return result


@app.post("/api/v1/content/repurpose")
async def repurpose_content(tenant_id: str, content_id: str, formats: list[str] = None):
    """Repurpose top-performing content"""
    agent = app.state.media_commerce
    result = await agent.repurpose_content(tenant_id, content_id, formats)
    return result


# ChiefPulse endpoints
@app.get("/api/v1/executive/briefing")
async def get_daily_briefing(tenant_id: str, executive_id: str):
    """Get daily executive briefing"""
    agent = app.state.chief_pulse
    result = await agent.generate_daily_briefing(tenant_id, executive_id)
    return result


@app.get("/api/v1/executive/approval-queue")
async def get_approval_queue(tenant_id: str, executive_id: str):
    """Get approval queue"""
    agent = app.state.chief_pulse
    result = await agent.get_approval_queue(tenant_id, executive_id)
    return result


# BudgetMind endpoints
@app.get("/api/v1/finance/budget-monitor")
async def monitor_budget(tenant_id: str, department: str = None):
    """Monitor budget vs actual"""
    agent = app.state.budget_mind
    result = await agent.monitor_budget(tenant_id, department)
    return result


@app.get("/api/v1/finance/unit-economics")
async def get_unit_economics(tenant_id: str, vertical: str):
    """Get unit economics"""
    agent = app.state.budget_mind
    result = await agent.calculate_unit_economics(tenant_id, vertical)
    return result


# BoardReady endpoints
@app.get("/api/v1/investor/board-deck")
async def generate_board_deck(tenant_id: str, quarter: str, year: int):
    """Generate board deck"""
    agent = app.state.board_ready
    result = await agent.generate_board_deck(tenant_id, quarter, year)
    return result


@app.get("/api/v1/investor/update")
async def generate_investor_update(tenant_id: str, month: str, year: int):
    """Generate investor update"""
    agent = app.state.board_ready
    result = await agent.generate_investor_update(tenant_id, month, year)
    return result


# ComplianceGate endpoints
@app.post("/api/v1/compliance/enforce-policy")
async def enforce_policy(tenant_id: str, policy_name: str, entity_data: dict):
    """Enforce policy compliance"""
    agent = app.state.compliance_gate
    result = await agent.enforce_policy(tenant_id, policy_name, entity_data)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8087,
        reload=True,
    )
