"""Arkham AI governance service — FastAPI application.

The central _checkpoint() function closes every fingerprint pipeline gap:
  checkpoint fires
    → run QA batteries           (arkham_qa)
    → run extras batteries       (arkham_extras)
    → build fingerprint          (arkham_fingerprint)
    → compare to intake baseline → drift score
    → compare to yard escapes    → yard_match score
    → feed both into Parole Board → verdict
    → write audit log

request_id flows from gateway through every DB write.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from packages.db import get_db
from packages.models.sidecar import (
    SidecarAuditLog,
    SidecarFingerprint,
    SidecarParoleVerdict,
    SidecarPersona,
)

from .arkham_benchmarks import _seed_defaults
from .arkham_extras import crossover_yard_escapes, run_extras_batteries
from .arkham_fingerprint import (
    build_fingerprint,
    cosine_distance,
    find_closest,
    get_intake_fingerprint,
)
from .arkham_parole_board import issue_verdict
from .arkham_qa import run_checkpoint_batteries
from .arkham import run_adversarial_sim
from .settings import settings

YARD_PATH = Path(__file__).parent.parent / "yard.jsonl"


# ── startup ──────────────────────────────────────────────────────────────────

def _run_yard_crossover() -> None:
    from packages.db import transactional_session
    try:
        with transactional_session() as db:
            crossover_yard_escapes(YARD_PATH, db)
    except Exception:
        logger.exception("yard crossover failed — service continues without it")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from packages.db import transactional_session
    with transactional_session() as db:
        _seed_defaults(db)
    asyncio.get_event_loop().run_in_executor(None, _run_yard_crossover)
    yield


app = FastAPI(
    title="Arkham Sidecar",
    version="0.1.0",
    description="AI persona governance: fingerprinting, QA batteries, Parole Board.",
    lifespan=lifespan,
)


# ── audit helper ─────────────────────────────────────────────────────────────

def _audit(
    db: Session,
    action: str,
    *,
    request_id: str | None = None,
    persona_id: str | None = None,
    tenant_id: str | None = None,
    old_state: str | None = None,
    new_state: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        SidecarAuditLog(
            request_id=request_id,
            persona_id=persona_id,
            tenant_id=tenant_id,
            action=action,
            old_state=old_state,
            new_state=new_state,
            audit_metadata=metadata or {},
            created_at=datetime.utcnow(),
        )
    )


def _ensure_persona(
    db: Session,
    *,
    persona_id: str,
    tenant_id: str,
    checkpoint: str,
) -> SidecarPersona:
    """Create a minimal persona row on first checkpoint so FK-backed writes succeed."""
    persona = db.query(SidecarPersona).filter_by(id=persona_id).first()
    if persona:
        return persona

    state = {
        "intake": "intake",
        "probation": "probation",
        "exit": "released",
    }.get(checkpoint, "intake")
    now = datetime.utcnow()
    persona = SidecarPersona(
        id=persona_id,
        tenant_id=tenant_id,
        display_name=persona_id,
        owner_tenant=tenant_id,
        state=state,
        created_at=now,
        updated_at=now,
    )
    db.add(persona)
    db.flush()
    return persona


# ── core pipeline ─────────────────────────────────────────────────────────────

def _checkpoint(
    persona_id: str,
    checkpoint: str,
    corpus: list[str],
    tenant_id: str,
    db: Session,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Wired pipeline:
      batteries → fingerprint → drift → yard_match → verdict → audit
    """
    if not corpus:
        raise ValueError("corpus must not be empty")

    _ensure_persona(
        db,
        persona_id=persona_id,
        tenant_id=tenant_id,
        checkpoint=checkpoint,
    )

    # 1. QA batteries
    qa_scores = run_checkpoint_batteries(
        persona_id, tenant_id, checkpoint, corpus, db, request_id=request_id
    )

    # 2. Extras batteries
    extras_scores = run_extras_batteries(
        persona_id, tenant_id, corpus, db,
        checkpoint=checkpoint, request_id=request_id,
    )

    # 3. Build fingerprint for this checkpoint
    fp = build_fingerprint(
        persona_id, tenant_id, checkpoint, corpus, db, request_id=request_id
    )

    # 4. Drift: compare to intake fingerprint (skip at intake itself)
    drift_score: float | None = None
    if checkpoint != "intake":
        intake_fp = get_intake_fingerprint(persona_id, db)
        if intake_fp:
            drift_score = cosine_distance(fp.vector, intake_fp.vector)

    # 5. Yard match: compare to all escaped-prisoner fingerprints
    yard_fp, yard_match_score = find_closest(fp.vector, db, checkpoint_filter="yard")
    yard_match_id = yard_fp.persona_id if yard_fp else None

    # 6. Parole Board: sole verdict authority
    all_scores = {**qa_scores, **extras_scores}
    verdict = issue_verdict(
        persona_id, tenant_id, checkpoint, all_scores, db,
        drift_score=drift_score,
        yard_match_score=yard_match_score,
        yard_match_id=yard_match_id,
        request_id=request_id,
    )

    # 7. Audit log (append-only)
    _audit(
        db,
        action=f"checkpoint.{checkpoint}",
        request_id=request_id,
        persona_id=persona_id,
        tenant_id=tenant_id,
        metadata={
            "verdict": verdict.verdict,
            "drift_score": drift_score,
            "yard_match_score": yard_match_score,
            "shadow_mode": verdict.shadow_mode,
            "battery_summary": all_scores,
        },
    )

    db.commit()

    return {
        "verdict": verdict.verdict,
        "verdict_id": verdict.id,
        "shadow_mode": verdict.shadow_mode,
        "reasoning": verdict.reasoning,
        "drift_score": drift_score,
        "yard_match_score": yard_match_score,
        "yard_match_id": yard_match_id,
        "battery_scores": all_scores,
        "fingerprint_id": fp.id,
    }


# ── request/response schemas ──────────────────────────────────────────────────

class CheckpointRequest(BaseModel):
    persona_id: str
    tenant_id: str
    checkpoint: str  # intake | probation | exit
    corpus: list[str]
    request_id: str | None = None


class FingerprintRequest(BaseModel):
    persona_id: str
    tenant_id: str
    checkpoint: str
    corpus: list[str]
    request_id: str | None = None


class CompareRequest(BaseModel):
    vector: list[float]
    tenant_id: str


class AdversarialSimRequest(BaseModel):
    persona_id: str
    tenant_id: str
    responses: list[str]
    evidence: str = ""
    request_id: str | None = None


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.post("/v1/checkpoint")
def checkpoint(req: CheckpointRequest, db: Session = Depends(get_db)) -> dict:
    """Run the full wired pipeline: batteries → fingerprint → drift → yard → verdict."""
    valid_checkpoints = {"intake", "probation", "exit"}
    if req.checkpoint not in valid_checkpoints:
        raise HTTPException(400, f"checkpoint must be one of {valid_checkpoints}")
    if not req.corpus:
        raise HTTPException(400, "corpus must not be empty")

    return _checkpoint(
        req.persona_id,
        req.checkpoint,
        req.corpus,
        req.tenant_id,
        db,
        request_id=req.request_id or f"req_{uuid.uuid4().hex}",
    )


@app.post("/v1/fingerprint")
def fingerprint_build(req: FingerprintRequest, db: Session = Depends(get_db)) -> dict:
    """Build and store a fingerprint from a corpus without running full pipeline."""
    if not req.corpus:
        raise HTTPException(400, "corpus must not be empty")
    fp = build_fingerprint(
        req.persona_id, req.tenant_id, req.checkpoint, req.corpus, db,
        request_id=req.request_id,
    )
    db.commit()
    return {"fingerprint_id": fp.id, "vector": fp.vector, "checkpoint": fp.checkpoint}


@app.post("/v1/fingerprint/compare")
def fingerprint_compare(req: CompareRequest, db: Session = Depends(get_db)) -> dict:
    """Find the closest stored fingerprint to the given vector."""
    if len(req.vector) == 0:
        raise HTTPException(400, "vector must not be empty")
    fp, dist = find_closest(req.vector, db, checkpoint_filter="yard")
    intake_fp, intake_dist = find_closest(req.vector, db, checkpoint_filter="intake")
    return {
        "closest_yard": {
            "persona_id": fp.persona_id if fp else None,
            "fingerprint_id": fp.id if fp else None,
            "cosine_distance": dist,
        },
        "closest_intake": {
            "persona_id": intake_fp.persona_id if intake_fp else None,
            "fingerprint_id": intake_fp.id if intake_fp else None,
            "cosine_distance": intake_dist,
        },
    }


@app.post("/v1/adversarial")
def adversarial_sim(req: AdversarialSimRequest, db: Session = Depends(get_db)) -> dict:
    """Run adversarial escape detection. If escaped, writes to yard.jsonl and cross-imports fingerprint."""
    result = run_adversarial_sim(
        req.persona_id, req.tenant_id, req.responses, YARD_PATH, evidence=req.evidence
    )
    if result["escaped"]:
        # Cross-import the new escape into the fingerprint table immediately
        crossover_yard_escapes(YARD_PATH, db)
        _audit(
            db,
            action="escape.detected",
            persona_id=req.persona_id,
            tenant_id=req.tenant_id,
            request_id=req.request_id,
            old_state="active",
            new_state="escaped",
            metadata={"trigger": result["trigger"]},
        )
        db.commit()
    return result


@app.get("/v1/stix/export")
def stix_export(db: Session = Depends(get_db)) -> dict:
    """Export governance data as a STIX 2.1 bundle (from real governance tables)."""
    verdicts = (
        db.query(SidecarParoleVerdict)
        .order_by(SidecarParoleVerdict.created_at.desc())
        .limit(500)
        .all()
    )
    objects = []
    for v in verdicts:
        objects.append({
            "type": "observed-data",
            "id": f"observed-data--{uuid.uuid4()}",
            "spec_version": "2.1",
            "created": v.created_at.isoformat() + "Z",
            "modified": v.created_at.isoformat() + "Z",
            "first_observed": v.created_at.isoformat() + "Z",
            "last_observed": v.created_at.isoformat() + "Z",
            "number_observed": 1,
            "x_arkham_verdict": {
                "verdict_id": v.id,
                "persona_id": v.persona_id,
                "tenant_id": v.tenant_id,
                "checkpoint": v.checkpoint,
                "verdict": v.verdict,
                "drift_score": v.drift_score,
                "yard_match_score": v.yard_match_score,
                "yard_match_id": v.yard_match_id,
                "shadow_mode": v.shadow_mode,
                "reasoning": v.reasoning,
                "request_id": v.request_id,
            },
            "object_refs": [],
        })

    escapes = (
        db.query(SidecarFingerprint)
        .filter(SidecarFingerprint.checkpoint == "yard")
        .order_by(SidecarFingerprint.created_at.desc())
        .limit(200)
        .all()
    )
    for e in escapes:
        objects.append({
            "type": "threat-actor",
            "id": f"threat-actor--{uuid.uuid4()}",
            "spec_version": "2.1",
            "created": e.created_at.isoformat() + "Z",
            "modified": e.created_at.isoformat() + "Z",
            "name": f"escaped-persona:{e.persona_id}",
            "x_arkham_escape": {
                "fingerprint_id": e.id,
                "persona_id": e.persona_id,
                "tenant_id": e.tenant_id,
                "trigger": e.fp_metadata.get("trigger"),
                "escape_timestamp": e.fp_metadata.get("escape_timestamp"),
            },
        })

    return {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid4()}",
        "spec_version": "2.1",
        "objects": objects,
    }


@app.get("/v1/yard")
def yard_list(db: Session = Depends(get_db)) -> dict:
    """List all escaped-prisoner fingerprints in the Yard."""
    escapes = (
        db.query(SidecarFingerprint)
        .filter(SidecarFingerprint.checkpoint == "yard")
        .order_by(SidecarFingerprint.created_at.desc())
        .all()
    )
    return {
        "count": len(escapes),
        "escapes": [
            {
                "id": e.id,
                "persona_id": e.persona_id,
                "tenant_id": e.tenant_id,
                "trigger": e.fp_metadata.get("trigger"),
                "escape_timestamp": e.fp_metadata.get("escape_timestamp"),
                "created_at": e.created_at.isoformat(),
            }
            for e in escapes
        ],
    }


@app.get("/v1/verdicts")
def verdict_list(
    limit: int = 50,
    offset: int = 0,
    verdict: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """List recent Parole Board verdicts for the dashboard."""
    q = db.query(SidecarParoleVerdict).order_by(SidecarParoleVerdict.created_at.desc())
    if verdict:
        q = q.filter(SidecarParoleVerdict.verdict == verdict)
    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "verdicts": [
            {
                "id": v.id,
                "persona_id": v.persona_id,
                "tenant_id": v.tenant_id,
                "checkpoint": v.checkpoint,
                "verdict": v.verdict,
                "points": v.points,
                "drift_score": v.drift_score,
                "yard_match_score": v.yard_match_score,
                "yard_match_id": v.yard_match_id,
                "shadow_mode": v.shadow_mode,
                "reasoning": v.reasoning,
                "request_id": v.request_id,
                "created_at": v.created_at.isoformat(),
            }
            for v in rows
        ],
    }


@app.get("/v1/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    """Aggregate governance stats for dashboard overview."""
    from sqlalchemy import func
    total_verdicts = db.query(func.count(SidecarParoleVerdict.id)).scalar() or 0
    approve_count = db.query(func.count(SidecarParoleVerdict.id)).filter(SidecarParoleVerdict.verdict == "approve").scalar() or 0
    hold_count = db.query(func.count(SidecarParoleVerdict.id)).filter(SidecarParoleVerdict.verdict == "hold").scalar() or 0
    reject_count = db.query(func.count(SidecarParoleVerdict.id)).filter(SidecarParoleVerdict.verdict == "reject").scalar() or 0
    total_personas = db.query(func.count(SidecarPersona.id)).scalar() or 0
    yard_count = db.query(func.count(SidecarFingerprint.id)).filter(SidecarFingerprint.checkpoint == "yard").scalar() or 0
    total_fingerprints = db.query(func.count(SidecarFingerprint.id)).scalar() or 0
    return {
        "verdicts": {
            "total": total_verdicts,
            "approve": approve_count,
            "hold": hold_count,
            "reject": reject_count,
        },
        "personas": total_personas,
        "yard_escapes": yard_count,
        "fingerprints": total_fingerprints,
        "shadow_mode": settings.shadow_mode,
    }


@app.get("/v1/verdicts/stream")
async def verdict_stream(db: Session = Depends(get_db)):
    """SSE stream — pushes new verdicts as they arrive (polls DB every 3s)."""
    import json
    import asyncio
    from fastapi.responses import StreamingResponse

    last_id: str | None = (
        db.query(SidecarParoleVerdict.id)
        .order_by(SidecarParoleVerdict.created_at.desc())
        .limit(1)
        .scalar()
    )

    async def event_generator():
        nonlocal last_id
        from packages.db import transactional_session
        yield "data: {\"type\":\"connected\"}\n\n"
        while True:
            await asyncio.sleep(3)
            try:
                with transactional_session() as session:
                    q = session.query(SidecarParoleVerdict).order_by(
                        SidecarParoleVerdict.created_at.desc()
                    ).limit(20)
                    rows = q.all()
                    new_rows = []
                    found_last = False
                    for row in rows:
                        if row.id == last_id:
                            found_last = True
                            break
                        new_rows.append(row)
                    if not found_last:
                        new_rows = rows[:1]
                    for row in reversed(new_rows):
                        payload = json.dumps({
                            "type": "verdict",
                            "id": row.id,
                            "persona_id": row.persona_id,
                            "tenant_id": row.tenant_id,
                            "checkpoint": row.checkpoint,
                            "verdict": row.verdict,
                            "points": row.points,
                            "drift_score": row.drift_score,
                            "yard_match_score": row.yard_match_score,
                            "shadow_mode": row.shadow_mode,
                            "created_at": row.created_at.isoformat(),
                        })
                        yield f"data: {payload}\n\n"
                        last_id = row.id
            except Exception:
                logger.exception("SSE stream error")
                yield "data: {\"type\":\"error\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "arkham"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(503, f"database not ready: {e}")
