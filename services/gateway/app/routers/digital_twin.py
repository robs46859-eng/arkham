"""Admin digital twin routes backed by project and domain truth records."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from packages.db import get_db
from packages.models import (
    BuildingElementRecord,
    DocumentChunkRecord,
    IngestionJob,
    IssueRecord,
    Project,
    ProjectFile,
    SidecarParoleVerdict,
    Tenant,
    TenantActorRoleRecord,
    WorkflowRunRecord,
)
from packages.schemas import DigitalTwinProjectSummary, PredictabilityFactor, PredictabilityScale
from ..middleware.admin_auth import require_admin

router = APIRouter(
    prefix="/v1/admin/digital-twins",
    tags=["digital-twins"],
    dependencies=[Depends(require_admin)],
)


def _list_records(db: Any, model: type[Any]) -> list[Any]:
    if hasattr(db, "_objects"):
        return [record for record in db._objects.values() if isinstance(record, model)]
    if hasattr(db, "query"):
        return list(db.query(model).all())
    raise RuntimeError("Database session does not support record listing.")


def _twin_status(
    *,
    file_total: int,
    has_completed_job: bool,
    has_active_job: bool,
    element_count: int,
    chunk_count: int,
    workflow_count: int,
) -> tuple[str, str]:
    if file_total == 0:
        return "seeded", "0.0.1"
    if has_active_job:
        return "syncing", "0.1.0"
    if has_completed_job and element_count == 0 and chunk_count == 0:
        return "ingested", "0.2.0"
    if workflow_count > 0 or element_count > 0 or chunk_count > 0:
        return "active", "0.3.0"
    return "registered", "0.1.0"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "moderate"
    if score >= 0.25:
        return "low"
    return "volatile"


def _normalize_count(count: int, ceiling: int) -> float:
    if ceiling <= 0:
        return 0.0
    return _clamp(count / ceiling)


def _keyword_hits(haystacks: list[str], keywords: set[str]) -> int:
    return sum(1 for text in haystacks if any(keyword in text.lower() for keyword in keywords))


def _factor(key: str, label: str, score: float, detail: str) -> PredictabilityFactor:
    if score >= 0.66:
        impact = "high"
    elif score >= 0.33:
        impact = "moderate"
    else:
        impact = "low"
    return PredictabilityFactor(
        key=key,
        label=label,
        score=round(score, 2),
        impact=impact,
        detail=detail,
    )


def _operational_predictability(
    *,
    actors: list[TenantActorRoleRecord],
    issues: list[IssueRecord],
    runs: list[WorkflowRunRecord],
    verdicts: list[SidecarParoleVerdict],
    readiness_score: float,
) -> PredictabilityScale:
    active_actor_count = sum(1 for actor in actors if actor.is_active)
    human_interaction = _clamp(
        0.35 + (0.25 * _normalize_count(active_actor_count, 8)) + (0.15 * readiness_score)
    )
    bad_actor_count = sum(1 for verdict in verdicts if verdict.verdict in {"hold", "reject"})
    bad_actor_pressure = _clamp(
        (0.55 * _normalize_count(bad_actor_count, 8))
        + (0.25 * _normalize_count(sum(1 for verdict in verdicts if verdict.shadow_mode), 12))
        + (0.2 * _normalize_count(sum(1 for issue in issues if issue.severity == "high"), 6))
    )
    fallout_risk = _clamp(
        (0.5 * _normalize_count(sum(1 for issue in issues if issue.severity == "high"), 5))
        + (0.3 * _normalize_count(sum(1 for run in runs if run.status == "failed"), 4))
        + (0.2 * (1.0 - readiness_score))
    )
    resilient_runs = sum(1 for run in runs if run.status in {"complete", "paused"})
    failed_runs = sum(1 for run in runs if run.status == "failed")
    workflow_stability = _clamp(
        0.3
        + (0.45 * _normalize_count(resilient_runs, max(len(runs), 1)))
        - (0.35 * _normalize_count(failed_runs, max(len(runs), 1)))
        + (0.15 * readiness_score)
    )
    coverage_confidence = _clamp(0.4 + (0.6 * readiness_score))

    score = _clamp(
        (0.26 * human_interaction)
        + (0.22 * workflow_stability)
        + (0.18 * coverage_confidence)
        - (0.18 * bad_actor_pressure)
        - (0.16 * fallout_risk)
    )
    confidence = _clamp(
        0.45 + (0.35 * readiness_score) + (0.2 * _normalize_count(len(verdicts) + len(runs), 16))
    )
    return PredictabilityScale(
        score=round(score, 2),
        band=_band(score),
        confidence=round(confidence, 2),
        summary=(
            f"Operational predictability blends human interaction, workflow stability, "
            f"adversarial pressure, and fallout risk across {len(issues)} tracked issues."
        ),
        factors=[
            _factor(
                "human_interaction",
                "Human Interaction",
                human_interaction,
                f"{active_actor_count} active tenant actors and readiness at {round(readiness_score * 100)}%.",
            ),
            _factor(
                "bad_actor_pressure",
                "Bad Actor Pressure",
                bad_actor_pressure,
                f"{bad_actor_count} hold/reject governance verdicts in the trailing 30 days.",
            ),
            _factor(
                "fallout_risk",
                "Fallout Risk",
                fallout_risk,
                f"{sum(1 for issue in issues if issue.severity == 'high')} high-severity issues and {failed_runs} failed workflows.",
            ),
            _factor(
                "workflow_stability",
                "Workflow Stability",
                workflow_stability,
                f"{resilient_runs} resilient runs out of {len(runs)} total.",
            ),
            _factor(
                "coverage_confidence",
                "Coverage Confidence",
                coverage_confidence,
                "Derived from ingest completeness and structured twin coverage.",
            ),
        ],
    )


def _environmental_predictability(
    *,
    elements: list[BuildingElementRecord],
    chunks: list[DocumentChunkRecord],
    issues: list[IssueRecord],
    readiness_score: float,
) -> PredictabilityScale:
    weather_terms = {"weather", "storm", "rain", "snow", "freeze", "flood", "heat", "temperature", "exposure", "moisture"}
    solar_terms = {"solar", "sun", "pv", "photovoltaic", "irradiance", "glare", "insolation"}
    wind_terms = {"wind", "gust", "turbine", "uplift", "draft", "ventilation", "crosswind"}
    envelope_terms = {"roof", "facade", "window", "wall", "envelope", "drainage", "site", "civil", "exterior"}

    element_text = [
        " ".join(
            part
            for part in [
                element.category,
                " ".join(f"{key}:{value}" for key, value in (element.properties or {}).items()),
            ]
            if part
        )
        for element in elements
    ]
    chunk_text = [chunk.text for chunk in chunks]
    corpus = element_text + chunk_text + [issue.type for issue in issues]

    corpus_ceiling = max(len(corpus), 1)
    weather_exposure = _clamp(
        0.15
        + (0.35 * _normalize_count(_keyword_hits(corpus, weather_terms), corpus_ceiling))
        + (0.25 * _normalize_count(_keyword_hits(corpus, envelope_terms), corpus_ceiling))
        + (0.15 * _normalize_count(sum(1 for issue in issues if issue.severity == "high"), 6))
    )
    solar_exposure = _clamp(
        0.1 + (0.7 * _normalize_count(_keyword_hits(corpus, solar_terms), corpus_ceiling))
    )
    wind_exposure = _clamp(
        0.1 + (0.7 * _normalize_count(_keyword_hits(corpus, wind_terms), corpus_ceiling))
    )
    envelope_sensitivity = _clamp(
        0.15 + (0.7 * _normalize_count(_keyword_hits(corpus, envelope_terms), corpus_ceiling))
    )
    data_confidence = _clamp(0.35 + (0.65 * readiness_score))

    instability = _clamp(
        (0.4 * weather_exposure)
        + (0.2 * solar_exposure)
        + (0.2 * wind_exposure)
        + (0.2 * envelope_sensitivity)
    )
    score = _clamp((0.7 * data_confidence) + (0.3 * (1.0 - instability)))
    confidence = _clamp(0.4 + (0.4 * readiness_score) + (0.2 * _normalize_count(len(corpus), 20)))
    return PredictabilityScale(
        score=round(score, 2),
        band=_band(score),
        confidence=round(confidence, 2),
        summary=(
            "Environmental predictability blends weather, solar, and wind exposure cues "
            "with the twin's current coverage confidence."
        ),
        factors=[
            _factor(
                "weather_exposure",
                "Weather Exposure",
                weather_exposure,
                f"{_keyword_hits(corpus, weather_terms)} weather-linked signals across the twin corpus.",
            ),
            _factor(
                "solar_exposure",
                "Solar Exposure",
                solar_exposure,
                f"{_keyword_hits(corpus, solar_terms)} solar-linked signals detected.",
            ),
            _factor(
                "wind_exposure",
                "Wind Exposure",
                wind_exposure,
                f"{_keyword_hits(corpus, wind_terms)} wind-linked signals detected.",
            ),
            _factor(
                "envelope_sensitivity",
                "Envelope Sensitivity",
                envelope_sensitivity,
                "Exterior, roof, facade, drainage, and site references increase environmental sensitivity.",
            ),
            _factor(
                "data_confidence",
                "Data Confidence",
                data_confidence,
                f"Driven by current twin readiness at {round(readiness_score * 100)}%.",
            ),
        ],
    )


@router.get("/projects", response_model=list[DigitalTwinProjectSummary])
def list_digital_twin_projects(
    tenant_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: object = Depends(get_db),
) -> list[DigitalTwinProjectSummary]:
    tenants = {
        record.id: record
        for record in _list_records(db, Tenant)
        if isinstance(record, Tenant)
    }
    actor_roles = [
        record
        for record in _list_records(db, TenantActorRoleRecord)
        if isinstance(record, TenantActorRoleRecord)
    ]
    governance_verdicts = [
        record
        for record in _list_records(db, SidecarParoleVerdict)
        if isinstance(record, SidecarParoleVerdict)
        and record.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
    ]
    projects = [
        record
        for record in _list_records(db, Project)
        if isinstance(record, Project) and (tenant_id is None or record.tenant_id == tenant_id)
    ]
    files_by_project: dict[str, list[ProjectFile]] = defaultdict(list)
    for record in _list_records(db, ProjectFile):
        if isinstance(record, ProjectFile):
            files_by_project[record.project_id].append(record)
    elements_by_project: dict[str, list[BuildingElementRecord]] = defaultdict(list)
    for record in _list_records(db, BuildingElementRecord):
        if isinstance(record, BuildingElementRecord):
            elements_by_project[record.project_id].append(record)
    issues_by_project: dict[str, list[IssueRecord]] = defaultdict(list)
    for record in _list_records(db, IssueRecord):
        if isinstance(record, IssueRecord):
            issues_by_project[record.project_id].append(record)
    jobs_by_project: dict[str, list[IngestionJob]] = defaultdict(list)
    for record in _list_records(db, IngestionJob):
        if isinstance(record, IngestionJob):
            jobs_by_project[record.project_id].append(record)
    runs_by_project: dict[str, list[WorkflowRunRecord]] = defaultdict(list)
    for record in _list_records(db, WorkflowRunRecord):
        if isinstance(record, WorkflowRunRecord):
            runs_by_project[record.project_id].append(record)

    chunks_by_project: dict[str, list[DocumentChunkRecord]] = defaultdict(list)
    file_to_project = {
        record.id: record.project_id
        for record in _list_records(db, ProjectFile)
        if isinstance(record, ProjectFile)
    }
    for record in _list_records(db, DocumentChunkRecord):
        if not isinstance(record, DocumentChunkRecord):
            continue
        project_id_for_chunk = file_to_project.get(record.file_id)
        if project_id_for_chunk:
            chunks_by_project[project_id_for_chunk].append(record)

    summaries: list[DigitalTwinProjectSummary] = []
    for project in projects:
        tenant = tenants.get(project.tenant_id)
        files = files_by_project.get(project.id, [])
        elements = elements_by_project.get(project.id, [])
        issues = issues_by_project.get(project.id, [])
        jobs = jobs_by_project.get(project.id, [])
        runs = runs_by_project.get(project.id, [])
        chunks = chunks_by_project.get(project.id, [])

        file_counts: dict[str, int] = defaultdict(int)
        for file_record in files:
            file_counts[file_record.file_type] += 1

        has_completed_job = any(job.status == "complete" for job in jobs)
        has_active_job = any(job.status in {"queued", "processing"} for job in jobs)
        twin_status, twin_version = _twin_status(
            file_total=len(files),
            has_completed_job=has_completed_job,
            has_active_job=has_active_job,
            element_count=len(elements),
            chunk_count=len(chunks),
            workflow_count=len(runs),
        )
        readiness_score = round(
            (
                (0.2 if len(files) > 0 else 0.0)
                + (0.2 if has_completed_job else 0.0)
                + (0.2 if len(elements) > 0 else 0.0)
                + (0.15 if len(chunks) > 0 else 0.0)
                + (0.15 if len(runs) > 0 else 0.0)
                + (0.1 if len(issues) == 0 and len(files) > 0 else 0.0)
            ),
            2,
        )

        latest_activity_candidates = [
            *[job.updated_at for job in jobs if getattr(job, "updated_at", None)],
            *[run.updated_at for run in runs if getattr(run, "updated_at", None)],
            *[element.created_at for element in elements if getattr(element, "created_at", None)],
            project.created_at,
        ]
        latest_activity_at = max(latest_activity_candidates) if latest_activity_candidates else None

        alerts: list[str] = []
        if any(job.status == "failed" for job in jobs):
            alerts.append("ingestion_failed")
        if sum(1 for issue in issues if issue.severity == "high") > 0:
            alerts.append("high_severity_issues")
        if len(files) > 0 and len(elements) == 0 and len(chunks) == 0:
            alerts.append("no_structured_domain_records")

        latest_job = max(jobs, key=lambda job: job.updated_at, default=None)
        operational_predictability = _operational_predictability(
            actors=[actor for actor in actor_roles if actor.tenant_id == project.tenant_id],
            issues=issues,
            runs=runs,
            verdicts=[verdict for verdict in governance_verdicts if verdict.tenant_id == project.tenant_id],
            readiness_score=readiness_score,
        )
        environmental_predictability = _environmental_predictability(
            elements=elements,
            chunks=chunks,
            issues=issues,
            readiness_score=readiness_score,
        )

        summaries.append(
            DigitalTwinProjectSummary(
                project_id=project.id,
                tenant_id=project.tenant_id,
                tenant_name=tenant.name if tenant else project.tenant_id,
                project_name=project.name,
                twin_status=twin_status,
                twin_version=twin_version,
                readiness_score=readiness_score,
                file_counts=dict(file_counts),
                building_element_count=len(elements),
                document_chunk_count=len(chunks),
                issue_count=len(issues),
                high_severity_issue_count=sum(1 for issue in issues if issue.severity == "high"),
                workflow_run_count=len(runs),
                latest_ingestion_status=latest_job.status if latest_job else None,
                latest_activity_at=latest_activity_at,
                alerts=alerts,
                operational_predictability=operational_predictability,
                environmental_predictability=environmental_predictability,
            )
        )

    summaries.sort(
        key=lambda summary: summary.latest_activity_at or summary.project_name,
        reverse=True,
    )
    return summaries[:limit]
