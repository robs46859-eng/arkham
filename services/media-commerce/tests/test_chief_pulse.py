import asyncio
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.agents.chief_pulse import ChiefPulseAgent


def test_detect_anomalies_flags_material_deviations():
    agent = ChiefPulseAgent()

    result = asyncio.run(
        agent.detect_anomalies(
            tenant_id="tenant-123",
            threshold=0.20,
            metrics_snapshot=[
                {"vertical": "ecom", "metric": "weekly_revenue", "actual": 80, "expected": 100},
                {"vertical": "media", "metric": "conversion_rate", "actual": 0.06, "expected": 0.03},
                {"vertical": "saas", "metric": "approval_backlog", "actual": 3, "expected": 3},
            ],
        )
    )

    assert len(result["detected"]) == 2
    assert result["detected"][0]["severity"] == "critical"
    assert result["detected"][0]["vertical"] == "media"


def test_get_approval_queue_sorts_overdue_and_priority():
    agent = ChiefPulseAgent()

    result = asyncio.run(
        agent.get_approval_queue(
            tenant_id="tenant-123",
            executive_id="exec-1",
            tasks=[
                {
                    "task_id": "later-medium",
                    "title": "Later task",
                    "priority": "medium",
                    "type": "human_approval_required",
                    "status": "pending",
                    "vertical": "media",
                    "reason": "Routine review",
                    "due_at": "2099-01-01T10:00:00+00:00",
                },
                {
                    "task_id": "overdue-critical",
                    "title": "Critical exception",
                    "priority": "critical",
                    "type": "human_approval_required",
                    "status": "pending",
                    "vertical": "staffing",
                    "reason": "Margin exception",
                    "due_at": "2000-01-01T10:00:00+00:00",
                },
            ],
        )
    )

    assert result["counts"] == {"pending": 2, "overdue": 1}
    assert result["pending_approvals"][0]["task_id"] == "overdue-critical"
    assert result["overdue"][0]["task_id"] == "overdue-critical"


def test_generate_daily_briefing_summarizes_runway_revenue_and_decisions():
    agent = ChiefPulseAgent()

    result = asyncio.run(
        agent.generate_daily_briefing(
            tenant_id="tenant-123",
            executive_id="exec-42",
            metrics_snapshot=[
                {"vertical": "overall", "metric": "cash_runway_months", "actual": 6, "expected": 9},
                {"vertical": "overall", "metric": "weekly_revenue", "actual": 120000, "expected": 150000},
                {"vertical": "media", "metric": "weekly_revenue", "actual": 50000, "expected": 42000},
                {"vertical": "staffing", "metric": "weekly_revenue", "actual": 26000, "expected": 32000},
            ],
            approval_tasks=[
                {
                    "task_id": "approve-discount",
                    "title": "Approve discount",
                    "priority": "high",
                    "type": "human_approval_required",
                    "status": "pending",
                    "vertical": "staffing",
                    "reason": "Competitive deal desk request",
                    "due_at": "2099-01-01T10:00:00+00:00",
                }
            ],
        )
    )

    assert result["cash_position"]["status"] == "at_risk"
    assert result["revenue_pulse"]["best_vertical"] == "media"
    assert result["high_priority_tasks"][0]["task_id"] == "approve-discount"
    assert result["decisions_needed"][0]["type"] == "approval"
    assert "Runway is at 6 months" in result["summary"]
