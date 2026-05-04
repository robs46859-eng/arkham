"""
Integration Test: Lead-to-Content Journey

Tests the full journey from lead capture → routing → content strategy → CRO.
"""

import asyncio
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION_ROOT = SERVICE_ROOT.parent.parent / "orchestration"

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(ORCHESTRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATION_ROOT))

from app.agents.deal_flow import DealFlowAgent
from app.agents.content_engine import ContentEngineAgent
from app.agents.fulfillment_ops import FulfillmentOpsAgent
from tests.integration.conftest import (
    WorkflowState,
    MockCheckpointStore,
    MockTaskQueue,
)


class TestLeadToContentJourney:
    """Test full lead-to-content journey across multiple agents"""

    @pytest.fixture
    def deal_flow_agent(self):
        return DealFlowAgent()

    @pytest.fixture
    def content_engine_agent(self):
        return ContentEngineAgent()

    @pytest.fixture
    def fulfillment_ops_agent(self):
        return FulfillmentOpsAgent()

    def test_staffing_lead_routes_correctly(
        self,
        deal_flow_agent: DealFlowAgent,
        test_tenant_id: str,
        test_lead_id: str,
        staffing_lead_signals: list[str],
    ):
        """Test staffing lead is routed to staffing vertical with high confidence"""
        result = asyncio.run(
            deal_flow_agent.route_lead(
                tenant_id=test_tenant_id,
                lead_id=test_lead_id,
                intent_signals=staffing_lead_signals,
            )
        )

        assert result["routed_vertical"] == "staffing"
        assert result["confidence"] >= 0.8
        assert result["requires_review"] is False
        assert result["lead_stage"] == "sql"
        assert "staffing" in result["matched_signals"]

    def test_ecom_lead_routes_correctly(
        self,
        deal_flow_agent: DealFlowAgent,
        test_tenant_id: str,
        test_lead_id: str,
        ecom_lead_signals: list[str],
    ):
        """Test e-commerce lead is routed to ecom vertical with high confidence"""
        result = asyncio.run(
            deal_flow_agent.route_lead(
                tenant_id=test_tenant_id,
                lead_id=test_lead_id,
                intent_signals=ecom_lead_signals,
            )
        )

        assert result["routed_vertical"] == "ecom"
        assert result["confidence"] >= 0.8
        assert result["requires_review"] is False
        assert "ecom" in result["matched_signals"]

    def test_media_lead_routes_correctly(
        self,
        deal_flow_agent: DealFlowAgent,
        test_tenant_id: str,
        test_lead_id: str,
        media_lead_signals: list[str],
    ):
        """Test media lead is routed to media vertical with high confidence"""
        result = asyncio.run(
            deal_flow_agent.route_lead(
                tenant_id=test_tenant_id,
                lead_id=test_lead_id,
                intent_signals=media_lead_signals,
            )
        )

        assert result["routed_vertical"] == "media"
        assert result["confidence"] >= 0.7
        assert result["requires_review"] is False

    def test_content_strategy_created_for_routed_vertical(
        self,
        deal_flow_agent: DealFlowAgent,
        content_engine_agent: ContentEngineAgent,
        test_tenant_id: str,
        test_lead_id: str,
        media_lead_signals: list[str],
        content_strategy_input: dict,
    ):
        """Test content strategy is created for the routed vertical"""
        # Step 1: Route lead
        routing_result = asyncio.run(
            deal_flow_agent.route_lead(
                tenant_id=test_tenant_id,
                lead_id=test_lead_id,
                intent_signals=media_lead_signals,
            )
        )

        assert routing_result["routed_vertical"] == "media"

        # Step 2: Create content strategy for routed vertical
        strategy_result = asyncio.run(
            content_engine_agent.create_content_strategy(
                tenant_id=test_tenant_id,
                vertical=routing_result["routed_vertical"],
                topic=content_strategy_input["topic"],
                goals=content_strategy_input["goals"],
            )
        )

        assert strategy_result["topic"] == content_strategy_input["topic"]
        assert strategy_result["vertical"] == "media"
        assert "distribution_channels" in strategy_result

    def test_page_cro_after_content_creation(
        self,
        content_engine_agent: ContentEngineAgent,
        fulfillment_ops_agent: FulfillmentOpsAgent,
        test_tenant_id: str,
        test_page_id: str,
        content_strategy_input: dict,
    ):
        """Test page CRO is applied after content creation"""
        # Step 1: Create content strategy
        strategy_result = asyncio.run(
            content_engine_agent.create_content_strategy(
                tenant_id=test_tenant_id,
                vertical="media",
                topic=content_strategy_input["topic"],
                goals=content_strategy_input["goals"],
            )
        )

        assert strategy_result["topic"] == content_strategy_input["topic"]

        # Step 2: Optimize page for conversions
        cro_result = asyncio.run(
            fulfillment_ops_agent.optimize_page(
                tenant_id=test_tenant_id,
                page_id=test_page_id,
                page_type="landing_page",
            )
        )

        assert cro_result["page_type"] == "landing_page"
        assert "recommendations" in cro_result

    def test_full_journey_staffing_lead_to_content(
        self,
        deal_flow_agent: DealFlowAgent,
        content_engine_agent: ContentEngineAgent,
        fulfillment_ops_agent: FulfillmentOpsAgent,
        test_tenant_id: str,
        test_lead_id: str,
        test_page_id: str,
        staffing_lead_signals: list[str],
        workflow_state: WorkflowState,
    ):
        """Test full journey: staffing lead → route → content strategy → CRO"""
        # Step 1: Route lead
        routing_result = asyncio.run(
            deal_flow_agent.route_lead(
                tenant_id=test_tenant_id,
                lead_id=test_lead_id,
                intent_signals=staffing_lead_signals,
            )
        )
        workflow_state.routing_result = routing_result

        assert routing_result["routed_vertical"] == "staffing"
        assert routing_result["confidence"] >= 0.8

        # Step 2: Create content strategy for staffing vertical
        strategy_result = asyncio.run(
            content_engine_agent.create_content_strategy(
                tenant_id=test_tenant_id,
                vertical=routing_result["routed_vertical"],
                topic="healthcare staffing solutions",
                goals=["lead_generation", "authority"],
            )
        )

        assert strategy_result["vertical"] == "staffing"
        assert strategy_result["topic"] == "healthcare staffing solutions"

        # Step 3: Optimize landing page
        cro_result = asyncio.run(
            fulfillment_ops_agent.optimize_page(
                tenant_id=test_tenant_id,
                page_id=test_page_id,
                page_type="landing_page",
            )
        )

        assert cro_result["page_type"] == "landing_page"
        assert "recommendations" in cro_result
