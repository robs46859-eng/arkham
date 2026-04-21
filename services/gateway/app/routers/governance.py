"""Admin governance review routes for Arkham sidecar verdicts."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query

from packages.db import get_db
from packages.models import SidecarParoleVerdict, SidecarPersona, SidecarScorecard
from packages.schemas import (
    AdminAlert,
    GovernanceScorecardResponse,
    GovernanceSummaryResponse,
    GovernanceVerdictResponse,
)
from ..middleware.admin_auth import require_admin

router = APIRouter(
    prefix="/v1/admin/governance",
    tags=["governance"],
    dependencies=[Depends(require_admin)],
)


def _list_records(db: Any, model: type[Any]) -> list[Any]:
    if hasattr(db, "_objects"):
        return [record for record in db._objects.values() if isinstance(record, model)]
    if hasattr(db, "query"):
        return list(db.query(model).all())
    raise RuntimeError("Database session does not support record listing.")


def _filtered_verdicts(
    db: Any,
    *,
    tenant_id: str | None = None,
    verdict: str | None = None,
    checkpoint: str | None = None,
    shadow_mode: bool | None = None,
) -> list[SidecarParoleVerdict]:
    verdicts = [
        record
        for record in _list_records(db, SidecarParoleVerdict)
        if isinstance(record, SidecarParoleVerdict)
    ]
    if tenant_id:
        verdicts = [record for record in verdicts if record.tenant_id == tenant_id]
    if verdict:
        verdicts = [record for record in verdicts if record.verdict == verdict]
    if checkpoint:
        verdicts = [record for record in verdicts if record.checkpoint == checkpoint]
    if shadow_mode is not None:
        verdicts = [record for record in verdicts if bool(record.shadow_mode) is shadow_mode]
    verdicts.sort(key=lambda record: record.created_at, reverse=True)
    return verdicts


def _scorecards_by_request(db: Any) -> dict[tuple[str, str, str], list[SidecarScorecard]]:
    grouped: dict[tuple[str, str, str], list[SidecarScorecard]] = defaultdict(list)
    for record in _list_records(db, SidecarScorecard):
        if not isinstance(record, SidecarScorecard) or not record.request_id:
            continue
        grouped[(record.request_id, record.persona_id, record.checkpoint)].append(record)
    for records in grouped.values():
        records.sort(key=lambda item: (item.created_at, item.battery))
    return grouped


@router.get("/summary", response_model=GovernanceSummaryResponse)
def governance_summary(
    tenant_id: str | None = Query(default=None),
    db: object = Depends(get_db),
) -> GovernanceSummaryResponse:
    verdicts = _filtered_verdicts(db, tenant_id=tenant_id)
    verdict_counts = Counter(record.verdict for record in verdicts)
    checkpoint_counts = Counter(record.checkpoint for record in verdicts)
    latest_verdict_at = verdicts[0].created_at if verdicts else None
    window_start = date.today() - timedelta(days=6)
    daily_counts = Counter(
        record.created_at.date().isoformat()
        for record in verdicts
        if record.created_at.date() >= window_start
    )
    daily_verdicts = [
        {"date": (window_start + timedelta(days=offset)).isoformat(), "count": daily_counts.get((window_start + timedelta(days=offset)).isoformat(), 0)}
        for offset in range(7)
    ]
    recent_alerts: list[AdminAlert] = []
    if verdict_counts.get("reject", 0) > 0:
        recent_alerts.append(
            AdminAlert(
                id="governance-rejects",
                severity="high",
                title="Recent reject verdicts detected",
                detail=f"{verdict_counts['reject']} recent governance verdicts are rejects and need operator review.",
                related_id=verdicts[0].id if verdicts else None,
            )
        )
    low_yard = [record for record in verdicts if record.yard_match_score is not None and record.yard_match_score < 0.25]
    if low_yard:
        recent_alerts.append(
            AdminAlert(
                id="governance-yard-proximity",
                severity="medium",
                title="High-risk yard proximity observed",
                detail=f"{len(low_yard)} recent verdicts matched known escape patterns at yard distance under 0.25.",
                related_id=low_yard[0].id,
            )
        )
    if verdicts and all(record.shadow_mode for record in verdicts):
        recent_alerts.append(
            AdminAlert(
                id="governance-shadow-mode",
                severity="low",
                title="Governance remains in shadow mode",
                detail="All recent verdicts are still shadow-mode only. Enforcement remains disabled.",
                related_id=verdicts[0].id,
            )
        )
    return GovernanceSummaryResponse(
        total_verdicts=len(verdicts),
        shadow_mode_count=sum(1 for record in verdicts if record.shadow_mode),
        enforced_count=sum(1 for record in verdicts if not record.shadow_mode),
        tenant_count=len({record.tenant_id for record in verdicts}),
        verdict_counts=dict(verdict_counts),
        checkpoint_counts=dict(checkpoint_counts),
        latest_verdict_at=latest_verdict_at,
        daily_verdicts=daily_verdicts,
        recent_alerts=recent_alerts,
    )


@router.get("/verdicts", response_model=list[GovernanceVerdictResponse])
def governance_verdicts(
    tenant_id: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
    checkpoint: str | None = Query(default=None),
    shadow_mode: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: object = Depends(get_db),
) -> list[GovernanceVerdictResponse]:
    personas = {
        record.id: record
        for record in _list_records(db, SidecarPersona)
        if isinstance(record, SidecarPersona)
    }
    grouped_scorecards = _scorecards_by_request(db)
    records = _filtered_verdicts(
        db,
        tenant_id=tenant_id,
        verdict=verdict,
        checkpoint=checkpoint,
        shadow_mode=shadow_mode,
    )[:limit]

    response: list[GovernanceVerdictResponse] = []
    for record in records:
        persona = personas.get(record.persona_id)
        scorecards = grouped_scorecards.get(
            (record.request_id or "", record.persona_id, record.checkpoint),
            [],
        )
        response.append(
            GovernanceVerdictResponse(
                verdict_id=record.id,
                persona_id=record.persona_id,
                persona_display_name=persona.display_name if persona else None,
                persona_state=persona.state if persona else None,
                tenant_id=record.tenant_id,
                request_id=record.request_id,
                checkpoint=record.checkpoint,
                verdict=record.verdict,
                shadow_mode=record.shadow_mode,
                reasoning=record.reasoning,
                drift_score=record.drift_score,
                yard_match_score=record.yard_match_score,
                yard_match_id=record.yard_match_id,
                battery_scores=dict(record.battery_scores or {}),
                scorecards=[
                    GovernanceScorecardResponse(
                        scorecard_id=scorecard.id,
                        battery=scorecard.battery,
                        passed=scorecard.passed,
                        total_tokens=scorecard.total_tokens,
                        latency_ms=scorecard.latency_ms,
                        cost_usd=scorecard.cost_usd,
                        scores=dict(scorecard.scores or {}),
                        created_at=scorecard.created_at,
                    )
                    for scorecard in scorecards
                ],
                created_at=record.created_at,
            )
        )
    return response
