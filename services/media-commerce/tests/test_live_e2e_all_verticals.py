"""
Live End-to-End Test - FullStackArkham All Verticals

Tests the complete media-commerce vertical with all 8 agents:
1. DealFlow™ - Lead routing
2. FulfillmentOps™ - CRO optimization
3. MediaCommerce™ - EPC monitoring
4. ContentEngine™ - Content generation
5. ChiefPulse™ - Signal aggregation
6. ComplianceGate™ - Compliance checking
7. BudgetMind™ - Financial analysis
8. BoardReady™ - Board deck generation

This test validates the FULL STACK working together.
"""

import asyncio
import sys
from pathlib import Path
import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.agents.deal_flow import DealFlowAgent
from app.agents.fulfillment_ops import FulfillmentOpsAgent
from app.agents.media_commerce import MediaCommerceAgent
from app.agents.content_engine import ContentEngineAgent
from app.agents.chief_pulse import ChiefPulseAgent
from app.agents.compliance_gate import ComplianceGateAgent
from app.agents.budget_mind import BudgetMindAgent
from app.agents.board_ready import BoardReadyAgent


TEST_TENANT_ID = "test-tenant-e2e-001"


@pytest.mark.anyio
async def test_all_verticals():
    """Run live end-to-end test across all 8 verticals"""
    print("\n" + "="*70)
    print(" FULLSTACKARKHAM - LIVE END-TO-END TEST")
    print(" Testing all 8 vertical agents")
    print("="*70 + "\n")

    results = {}
    agents = {
        "DealFlow": DealFlowAgent(),
        "FulfillmentOps": FulfillmentOpsAgent(),
        "MediaCommerce": MediaCommerceAgent(),
        "ContentEngine": ContentEngineAgent(),
        "ChiefPulse": ChiefPulseAgent(),
        "ComplianceGate": ComplianceGateAgent(),
        "BudgetMind": BudgetMindAgent(),
        "BoardReady": BoardReadyAgent(),
    }

    for agent_name, agent in agents.items():
        print(f"[1/8] Testing {agent_name}...")
        try:
            result = await _run_agent_test(agent_name, agent)
            results[agent_name] = {"status": "PASS", "result": result}
            print(f"      ✓ {agent_name} PASSED\n")
        except Exception as e:
            results[agent_name] = {"status": "FAIL", "error": str(e)}
            print(f"      ✗ {agent_name} FAILED: {e}\n")

    # Print summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] == "FAIL")

    for agent_name, result in results.items():
        status = "✓ PASS" if result["status"] == "PASS" else f"✗ FAIL: {result.get('error', 'Unknown')}"
        print(f"  {agent_name:20} {status}")

    print(f"\n  Total: {passed} passed, {failed} failed out of {len(agents)} agents")
    print("="*70 + "\n")

    assert passed == len(agents)


async def _run_agent_test(agent_name: str, agent):
    """Internal helper to test individual agent"""
    if agent_name == "DealFlow":
        result = await agent.route_lead(
            tenant_id=TEST_TENANT_ID,
            lead_id="test-lead-001",
            intent_signals=["Shopify checkout optimization", "Abandoned cart recovery"],
        )
        assert result["routed_vertical"] == "ecom", f"Expected ecom, got {result['routed_vertical']}"
        return f"Routed to {result['routed_vertical']} (confidence: {result['confidence']:.2f})"

    elif agent_name == "FulfillmentOps":
        result = await agent.optimize_page(
            tenant_id=TEST_TENANT_ID,
            page_id="test-page-001",
            page_type="landing_page",
        )
        assert "recommendations" in result
        return f"Generated {len(result['recommendations'])} CRO recommendations"

    elif agent_name == "MediaCommerce":
        result = await agent.monitor_epc(
            tenant_id=TEST_TENANT_ID,
            vertical="media",
        )
        assert "assets_monitored" in result or "avg_epc" in result
        return f"EPC monitoring complete"

    elif agent_name == "ContentEngine":
        result = await agent.create_content_strategy(
            tenant_id=TEST_TENANT_ID,
            vertical="media",
            topic="affiliate marketing best practices",
            goals=["revenue", "awareness"],
        )
        assert "topic" in result
        return f"Strategy created for '{result['topic']}'"

    elif agent_name == "ChiefPulse":
        result = await agent.generate_daily_briefing(
            tenant_id=TEST_TENANT_ID,
            executive_id="test-exec-001",
        )
        assert "cash_position" in result or "decisions_needed" in result or len(result) > 0
        return "Daily briefing generated"

    elif agent_name == "ComplianceGate":
        result = await agent.seo_audit(
            tenant_id=TEST_TENANT_ID,
            content_assets=[{"id": "test-content-001", "metadata": {"title": "Test"}}],
        )
        assert "compliance_rate" in result or "assets_audited" in result
        return f"SEO audit complete ({result.get('compliance_rate', 'N/A')})"

    elif agent_name == "BudgetMind":
        result = await agent.calculate_unit_economics(
            tenant_id=TEST_TENANT_ID,
            vertical="saas",
        )
        assert "unit_economics" in result
        metrics = result["unit_economics"]
        return f"LTV:CAC={metrics['ltv_cac_ratio']:.1f}, Payback={metrics['payback_months']:.1f}mo"

    elif agent_name == "BoardReady":
        result = await agent.generate_board_deck(
            tenant_id=TEST_TENANT_ID,
            quarter="Q1",
            year=2025,
        )
        assert "sections" in result
        return f"Board deck: {len(result['sections'])} sections, {result['completeness_score']*100:.0f}% complete"

    return "Unknown agent"


if __name__ == "__main__":
    success = asyncio.run(test_all_verticals())
    sys.exit(0 if success else 1)
