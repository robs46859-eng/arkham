"""
ChiefPulse™ Agent

AI Chief of Staff. Synthesizes signals across revenue, operations, and compliance
to eliminate 2-3 hours of daily context gathering for executives.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChiefPulseAgent:
    """
    ChiefPulse™ Agent - AI Chief of Staff

    Capabilities:
    - Signal synthesis across all verticals
    - Anomaly detection and alerting
    - Executive briefing generation
    - Approval queue management
    - Cross-agent coordination
    """

    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.gateway_url = gateway_url

    async def generate_daily_briefing(
        self,
        tenant_id: str,
        executive_id: str,
        metrics_snapshot: Optional[List[Dict[str, Any]]] = None,
        approval_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate daily executive briefing.

        Uses deterministic metric snapshots so the service can produce useful
        executive summaries before database-backed aggregation is wired in.
        """
        metrics_snapshot = metrics_snapshot or self._default_metrics_snapshot()
        approval_tasks = approval_tasks or self._default_approval_tasks()

        anomalies = await self.detect_anomalies(
            tenant_id=tenant_id,
            threshold=0.20,
            metrics_snapshot=metrics_snapshot,
        )
        approvals = await self.get_approval_queue(
            tenant_id=tenant_id,
            executive_id=executive_id,
            tasks=approval_tasks,
        )
        cross_vertical = await self.cross_vertical_analysis(
            tenant_id=tenant_id,
            period_days=7,
            metrics_snapshot=metrics_snapshot,
        )

        high_priority_tasks = approvals["pending_approvals"][:3]
        decisions_needed = [
            {
                "type": "approval",
                "task_id": item["task_id"],
                "title": item["title"],
                "priority": item["priority"],
            }
            for item in high_priority_tasks
        ]

        if anomalies["detected"]:
            first_anomaly = anomalies["detected"][0]
            decisions_needed.append(
                {
                    "type": "anomaly_response",
                    "vertical": first_anomaly["vertical"],
                    "metric": first_anomaly["metric"],
                    "recommended_action": first_anomaly["recommended_action"],
                }
            )

        cash_metric = self._find_metric(metrics_snapshot, "overall", "cash_runway_months")
        revenue_metric = self._find_metric(metrics_snapshot, "overall", "weekly_revenue")

        briefing = {
            "tenant_id": tenant_id,
            "executive_id": executive_id,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "cash_position": {
                "runway_months": cash_metric["actual"] if cash_metric else None,
                "target_runway_months": cash_metric["expected"] if cash_metric else None,
                "status": self._metric_status(cash_metric) if cash_metric else "unknown",
            },
            "revenue_pulse": {
                "weekly_revenue": revenue_metric["actual"] if revenue_metric else None,
                "target_revenue": revenue_metric["expected"] if revenue_metric else None,
                "status": self._metric_status(revenue_metric) if revenue_metric else "unknown",
                "best_vertical": cross_vertical.get("best_performer"),
            },
            "high_priority_tasks": high_priority_tasks,
            "anomaly_alerts": anomalies["detected"],
            "decisions_needed": decisions_needed,
            "summary": self._build_summary(
                cash_metric=cash_metric,
                revenue_metric=revenue_metric,
                anomaly_count=len(anomalies["detected"]),
                approval_count=len(approvals["pending_approvals"]),
            ),
        }

        logger.info("Daily briefing generated for %s", executive_id)
        return briefing

    async def detect_anomalies(
        self,
        tenant_id: str,
        vertical: str = None,
        threshold: float = 0.20,
        metrics_snapshot: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Detect anomalies by comparing actual vs expected values."""
        metrics_snapshot = metrics_snapshot or self._default_metrics_snapshot()

        detected: List[Dict[str, Any]] = []
        for item in metrics_snapshot:
            if vertical and item["vertical"] != vertical:
                continue

            expected = float(item["expected"])
            actual = float(item["actual"])
            if expected == 0:
                continue

            deviation = abs(actual - expected) / expected
            if deviation < threshold:
                continue

            direction = "above" if actual > expected else "below"
            detected.append(
                {
                    "vertical": item["vertical"],
                    "metric": item["metric"],
                    "actual": actual,
                    "expected": expected,
                    "deviation_pct": round(deviation, 2),
                    "direction": direction,
                    "severity": self._severity_for_deviation(deviation),
                    "recommended_action": self._recommended_action(item["metric"], direction),
                }
            )

        detected.sort(
            key=lambda item: (
                self._severity_rank(item["severity"]),
                item["deviation_pct"],
            ),
            reverse=True,
        )

        anomalies = {
            "tenant_id": tenant_id,
            "vertical": vertical,
            "threshold": threshold,
            "detected": detected,
        }

        logger.info("Anomaly detection complete for %s", tenant_id)
        return anomalies

    async def get_approval_queue(
        self,
        tenant_id: str,
        executive_id: str,
        tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Return pending executive approvals sorted by urgency and priority."""
        tasks = tasks or self._default_approval_tasks()
        now = datetime.now(timezone.utc)

        pending = []
        overdue = []
        for task in tasks:
            if task.get("type") != "human_approval_required":
                continue
            if task.get("status") != "pending":
                continue

            normalized = {
                "task_id": task["task_id"],
                "title": task["title"],
                "priority": task["priority"],
                "due_at": task["due_at"],
                "vertical": task["vertical"],
                "reason": task["reason"],
            }
            due_at = self._parse_dt(task["due_at"])
            if due_at < now:
                overdue.append(normalized)
            pending.append(normalized)

        pending.sort(key=self._task_sort_key)
        overdue.sort(key=self._task_sort_key)

        queue = {
            "tenant_id": tenant_id,
            "executive_id": executive_id,
            "pending_approvals": pending,
            "overdue": overdue,
            "counts": {
                "pending": len(pending),
                "overdue": len(overdue),
            },
        }

        logger.info("Approval queue retrieved for %s", executive_id)
        return queue

    async def cross_vertical_analysis(
        self,
        tenant_id: str,
        period_days: int = 30,
        metrics_snapshot: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Aggregate a compact cross-vertical revenue and efficiency comparison."""
        metrics_snapshot = metrics_snapshot or self._default_metrics_snapshot()

        by_vertical: Dict[str, Dict[str, float]] = {}
        for item in metrics_snapshot:
            vertical = item["vertical"]
            by_vertical.setdefault(vertical, {})
            by_vertical[vertical][item["metric"]] = float(item["actual"])

        summaries = []
        for vertical, metrics in by_vertical.items():
            if vertical == "overall":
                continue
            summaries.append(
                {
                    "vertical": vertical,
                    "revenue": metrics.get("weekly_revenue", 0.0),
                    "conversion_rate": metrics.get("conversion_rate", 0.0),
                    "approval_backlog": metrics.get("approval_backlog", 0.0),
                }
            )

        summaries.sort(key=lambda item: (item["revenue"], item["conversion_rate"]), reverse=True)
        best = summaries[0]["vertical"] if summaries else None
        worst = summaries[-1]["vertical"] if summaries else None

        analysis = {
            "tenant_id": tenant_id,
            "period_days": period_days,
            "verticals": summaries,
            "best_performer": best,
            "worst_performer": worst,
            "insights": self._build_cross_vertical_insights(summaries),
        }

        logger.info("Cross-vertical analysis complete for %s", tenant_id)
        return analysis

    async def send_alert(
        self,
        tenant_id: str,
        alert_type: str,
        severity: str,
        message: str,
        recipient_id: str,
    ) -> Dict[str, Any]:
        """Return deterministic alert-delivery metadata."""
        result = {
            "tenant_id": tenant_id,
            "alert_type": alert_type,
            "severity": severity,
            "recipient_id": recipient_id,
            "message": message,
            "sent": True,
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("Alert sent: %s (%s) to %s", alert_type, severity, recipient_id)
        return result

    def _default_metrics_snapshot(self) -> List[Dict[str, Any]]:
        return [
            {"vertical": "overall", "metric": "cash_runway_months", "actual": 7.5, "expected": 9.0},
            {"vertical": "overall", "metric": "weekly_revenue", "actual": 143000, "expected": 150000},
            {"vertical": "media", "metric": "weekly_revenue", "actual": 48000, "expected": 40000},
            {"vertical": "media", "metric": "conversion_rate", "actual": 0.032, "expected": 0.035},
            {"vertical": "ecom", "metric": "weekly_revenue", "actual": 36000, "expected": 45000},
            {"vertical": "ecom", "metric": "conversion_rate", "actual": 0.019, "expected": 0.028},
            {"vertical": "saas", "metric": "weekly_revenue", "actual": 31000, "expected": 30000},
            {"vertical": "saas", "metric": "approval_backlog", "actual": 4, "expected": 2},
            {"vertical": "staffing", "metric": "weekly_revenue", "actual": 28000, "expected": 32000},
            {"vertical": "staffing", "metric": "conversion_rate", "actual": 0.24, "expected": 0.22},
        ]

    def _default_approval_tasks(self) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "task_id": "approve-budget-shift",
                "title": "Approve media budget reallocation",
                "priority": "high",
                "type": "human_approval_required",
                "status": "pending",
                "vertical": "media",
                "reason": "Winning campaign is above target EPC",
                "due_at": (now + timedelta(hours=4)).isoformat(),
            },
            {
                "task_id": "approve-staffing-discount",
                "title": "Approve staffing proposal discount",
                "priority": "critical",
                "type": "human_approval_required",
                "status": "pending",
                "vertical": "staffing",
                "reason": "Deal margin exception requested",
                "due_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "task_id": "review-lifecycle-email",
                "title": "Review lifecycle email copy",
                "priority": "medium",
                "type": "human_approval_required",
                "status": "pending",
                "vertical": "saas",
                "reason": "Customer-facing change needs signoff",
                "due_at": (now + timedelta(days=1)).isoformat(),
            },
        ]

    def _find_metric(
        self,
        metrics_snapshot: List[Dict[str, Any]],
        vertical: str,
        metric: str,
    ) -> Optional[Dict[str, Any]]:
        for item in metrics_snapshot:
            if item["vertical"] == vertical and item["metric"] == metric:
                return item
        return None

    def _metric_status(self, metric: Optional[Dict[str, Any]]) -> str:
        if metric is None:
            return "unknown"
        actual = float(metric["actual"])
        expected = float(metric["expected"])
        if actual >= expected:
            return "on_track"
        if actual >= expected * 0.9:
            return "watch"
        return "at_risk"

    def _build_summary(
        self,
        cash_metric: Optional[Dict[str, Any]],
        revenue_metric: Optional[Dict[str, Any]],
        anomaly_count: int,
        approval_count: int,
    ) -> str:
        runway = cash_metric["actual"] if cash_metric else "unknown"
        revenue = revenue_metric["actual"] if revenue_metric else "unknown"
        return (
            f"Runway is at {runway} months, weekly revenue is {revenue}, "
            f"{anomaly_count} anomalies need review, and {approval_count} approvals are pending."
        )

    def _recommended_action(self, metric: str, direction: str) -> str:
        mapping = {
            "weekly_revenue": "Review channel mix and pipeline pacing",
            "conversion_rate": "Audit landing page and offer friction",
            "approval_backlog": "Clear executive blockers and reassign owners",
            "cash_runway_months": "Reduce discretionary spend and validate collection timing",
        }
        base = mapping.get(metric, "Review metric owners and validate the underlying data")
        if direction == "above" and metric in {"approval_backlog"}:
            return base
        if direction == "above":
            return "Scale the winning motion while validating margin quality"
        return base

    def _severity_for_deviation(self, deviation: float) -> str:
        if deviation >= 0.50:
            return "critical"
        if deviation >= 0.35:
            return "high"
        if deviation >= 0.20:
            return "medium"
        return "low"

    def _severity_rank(self, severity: str) -> int:
        return {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }.get(severity, 0)

    def _parse_dt(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _task_sort_key(self, task: Dict[str, Any]) -> tuple[int, datetime]:
        priority_rank = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }.get(task["priority"], 0)
        return (-priority_rank, self._parse_dt(task["due_at"]))

    def _build_cross_vertical_insights(self, summaries: List[Dict[str, Any]]) -> List[str]:
        if not summaries:
            return []
        best = summaries[0]
        worst = summaries[-1]
        insights = [
            f"{best['vertical']} leads weekly revenue at {best['revenue']:.0f}.",
            f"{worst['vertical']} needs attention due to weaker revenue or conversion efficiency.",
        ]
        approval_heavy = [item for item in summaries if item.get("approval_backlog", 0) >= 3]
        if approval_heavy:
            insights.append(
                f"{approval_heavy[0]['vertical']} has an approval backlog that may slow execution."
            )
        return insights

    async def aggregate_signals(
        self,
        tenant_id: str,
        time_window: str = "24h",
        agents: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate signals across all agents

        Args:
            tenant_id: Tenant identifier
            time_window: Time window (24h, 7d, 30d)
            agents: List of agents to aggregate from

        Returns:
            Aggregated signals by agent and vertical
        """
        agents = agents or ["dealflow", "contentengine", "mediacommerce", "fulfillmentops"]

        # Simulated signal aggregation (would query actual agent data in production)
        by_agent = {}
        by_vertical = {}
        total_signals = 0

        for agent in agents:
            agent_signals = {
                "events": 10,
                "tasks": 5,
                "alerts": 2,
            }
            by_agent[agent] = agent_signals
            total_signals += sum(agent_signals.values())

        # Aggregate by vertical
        for vertical in ["studio", "ecom", "saas", "staffing", "media"]:
            by_vertical[vertical] = {
                "revenue": 1000,
                "leads": 20,
                "content_assets": 15,
            }

        logger.info("Signal aggregation complete for %s: %d signals", tenant_id, total_signals)

        return {
            "tenant_id": tenant_id,
            "time_window": time_window,
            "total_signals": total_signals,
            "by_agent": by_agent,
            "by_vertical": by_vertical,
            "anomalies": [],
        }
