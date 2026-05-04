import asyncio
import json
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from mcp_server import _AGENT_INSTANCES, _execute_agent_tool, call_tool


@pytest.fixture(autouse=True)
def clear_agent_cache():
    _AGENT_INSTANCES.clear()
    yield
    _AGENT_INSTANCES.clear()


def test_execute_agent_tool_uses_real_content_engine():
    result = asyncio.run(
        _execute_agent_tool(
            "ContentEngine",
            "create_content_strategy",
            {
                "tenant_id": "tenant-123",
                "vertical": "media",
                "topic": "affiliate content optimization",
            },
        )
    )

    assert result["status"] == "success"
    assert result["agent"] == "ContentEngine"
    assert result["tool"] == "create_content_strategy"
    assert result["data"]["topic"] == "affiliate content optimization"
    assert result["data"]["primary_goal"] == "awareness"
    assert result["data"]["keywords"][:3] == [
        "affiliate content optimization",
        "best affiliate content optimization",
        "how to affiliate content optimization",
    ]
    assert result["data"]["angles"][0] == "How Product solves affiliate content optimization"


def test_execute_agent_tool_routes_deal_flow_and_chief_pulse():
    deal_flow = asyncio.run(
        _execute_agent_tool(
            "DealFlow",
            "route_lead",
            {
                "tenant_id": "tenant-123",
                "lead_id": "lead-1",
                "intent_signals": [
                    "Need nurse staffing support",
                    "Fill shifts urgently",
                    "Credentialing backlog",
                ],
            },
        )
    )
    briefing = asyncio.run(
        _execute_agent_tool(
            "ChiefPulse",
            "generate_daily_briefing",
            {
                "tenant_id": "tenant-123",
                "executive_id": "exec-9",
            },
        )
    )
    approvals = asyncio.run(
        _execute_agent_tool(
            "ChiefPulse",
            "get_approval_queue",
            {
                "tenant_id": "tenant-123",
                "executive_id": "exec-9",
            },
        )
    )

    assert deal_flow["status"] == "success"
    assert deal_flow["data"]["routed_vertical"] == "staffing"
    assert briefing["status"] == "success"
    assert briefing["data"]["executive_id"] == "exec-9"
    assert briefing["data"]["date"]
    assert approvals["status"] == "success"
    assert approvals["data"]["executive_id"] == "exec-9"


def test_call_tool_returns_structured_error_for_invalid_tool_name():
    contents = asyncio.run(call_tool("not-a-valid-tool", {}))
    payload = json.loads(contents[0].text)

    assert payload["status"] == "error"
    assert payload["error"]["type"] == "invalid_tool_name"


def test_call_tool_returns_structured_error_for_unknown_tool_and_bad_args():
    unknown_tool = asyncio.run(call_tool("ContentEngine.nope", {}))
    unknown_payload = json.loads(unknown_tool[0].text)
    assert unknown_payload["status"] == "error"
    assert unknown_payload["error"]["type"] == "unknown_tool"

    bad_args = asyncio.run(
        call_tool(
            "DealFlow.route_lead",
            {
                "tenant_id": "tenant-123",
                "lead_id": "lead-1",
            },
        )
    )
    bad_args_payload = json.loads(bad_args[0].text)
    assert bad_args_payload["status"] == "error"
    assert bad_args_payload["error"]["type"] == "invalid_arguments"
    assert "intent_signals" in bad_args_payload["error"]["message"]
