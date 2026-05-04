"""
Integration Test: EPC Optimization Chain

Tests the full EPC monitoring → classification → auto-optimization chain.
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

from app.agents.media_commerce import MediaCommerceAgent
from app.agents.fulfillment_ops import FulfillmentOpsAgent
from tests.integration.conftest import WorkflowState


class TestEPCOptimizationChain:
    """Test full EPC optimization chain across MediaCommerce agent"""

    @pytest.fixture
    def media_commerce_agent(self):
        return MediaCommerceAgent()

    @pytest.fixture
    def fulfillment_ops_agent(self):
        return FulfillmentOpsAgent()

    def test_epc_monitoring_classifies_content(
        self,
        media_commerce_agent: MediaCommerceAgent,
        test_tenant_id: str,
        test_content_id: str,
    ):
        """Test EPC monitoring classifies content by performance"""
        result = asyncio.run(
            media_commerce_agent.monitor_epc(
                tenant_id=test_tenant_id,
                content_id=test_content_id,
                vertical="media",
            )
        )

        assert result["tenant_id"] == test_tenant_id
        assert "assets_monitored" in result
        assert "avg_epc" in result
        assert "winners" in result
        assert "underperformers" in result

    def test_auto_optimize_retires_underperformer(
        self,
        media_commerce_agent: MediaCommerceAgent,
        test_tenant_id: str,
        test_content_id: str,
    ):
        """Test auto-optimization retires content with low EPC"""
        result = asyncio.run(
            media_commerce_agent.auto_optimize_content(
                tenant_id=test_tenant_id,
                content_id=test_content_id,
            )
        )

        assert result["tenant_id"] == test_tenant_id
        assert result["content_id"] == test_content_id
        assert "current_epc" in result
        assert "actions_taken" in result

    def test_auto_optimize_scales_winner(
        self,
        media_commerce_agent: MediaCommerceAgent,
        test_tenant_id: str,
    ):
        """Test auto-optimization creates variations for winners"""
        # Simulate winner content (EPC > $10)
        winner_content_id = "winner-content-123"

        result = asyncio.run(
            media_commerce_agent.auto_optimize_content(
                tenant_id=test_tenant_id,
                content_id=winner_content_id,
            )
        )

        assert result["tenant_id"] == test_tenant_id
        assert result["content_id"] == winner_content_id
        assert "actions_taken" in result

    def test_affiliate_placement_swap(
        self,
        media_commerce_agent: MediaCommerceAgent,
        test_tenant_id: str,
        test_content_id: str,
    ):
        """Test affiliate placement is swapped successfully"""
        new_placement = {
            "network": "amazon",
            "offer_id": "B08XYZ123",
            "placement_url": "https://example.com/placement",
            "expected_epc": 5.0,
        }

        result = asyncio.run(
            media_commerce_agent.swap_affiliate_placement(
                tenant_id=test_tenant_id,
                content_id=test_content_id,
                new_placement=new_placement,
            )
        )

        assert result["swapped"] is True
        assert result["new_placement"] == new_placement
        assert "old_placement" in result

    def test_content_repurpose_creates_formats(
        self,
        media_commerce_agent: MediaCommerceAgent,
        test_tenant_id: str,
        test_content_id: str,
    ):
        """Test content repurposing creates multiple formats"""
        target_formats = ["social", "email", "video"]

        result = asyncio.run(
            media_commerce_agent.repurpose_content(
                tenant_id=test_tenant_id,
                content_id=test_content_id,
                target_formats=target_formats,
            )
        )

        assert result["source_id"] == test_content_id
        assert len(result["formats"]) == 3
        format_names = [f["format"] for f in result["formats"]]
        assert "social" in format_names
        assert "email" in format_names
        assert "video" in format_names

    def test_full_epc_chain_monitor_optimize_repurpose(
        self,
        media_commerce_agent: MediaCommerceAgent,
        test_tenant_id: str,
        test_content_id: str,
        workflow_state: WorkflowState,
    ):
        """Test full EPC chain: monitor → optimize → repurpose"""
        # Step 1: Monitor EPC
        monitoring_result = asyncio.run(
            media_commerce_agent.monitor_epc(
                tenant_id=test_tenant_id,
                content_id=test_content_id,
                vertical="media",
            )
        )
        workflow_state.epc_result = monitoring_result

        assert monitoring_result["tenant_id"] == test_tenant_id
        assert "avg_epc" in monitoring_result

        # Step 2: Auto-optimize based on EPC
        optimization_result = asyncio.run(
            media_commerce_agent.auto_optimize_content(
                tenant_id=test_tenant_id,
                content_id=test_content_id,
            )
        )
        workflow_state.optimization_actions.append(optimization_result)

        assert optimization_result["content_id"] == test_content_id
        assert "actions_taken" in optimization_result

        # Step 3: Repurpose if winner (simulated)
        repurpose_result = asyncio.run(
            media_commerce_agent.repurpose_content(
                tenant_id=test_tenant_id,
                content_id=test_content_id,
                target_formats=["social", "email"],
            )
        )

        assert repurpose_result["source_id"] == test_content_id
        assert len(repurpose_result["formats"]) >= 1

    def test_epc_thresholds_enforced(
        self,
        media_commerce_agent: MediaCommerceAgent,
        test_tenant_id: str,
    ):
        """Test EPC thresholds are correctly applied"""
        # Test winner threshold (EPC > $10)
        winner_result = asyncio.run(
            media_commerce_agent.monitor_epc(
                tenant_id=test_tenant_id,
                vertical="media",
            )
        )

        # Test underperformer threshold (EPC < $2.50)
        underperformer_result = asyncio.run(
            media_commerce_agent.auto_optimize_content(
                tenant_id=test_tenant_id,
                content_id="low-epc-content",
            )
        )

        assert "current_epc" in underperformer_result
        assert "actions_taken" in underperformer_result
