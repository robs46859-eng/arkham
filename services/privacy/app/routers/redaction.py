"""PII redaction and restoration endpoints.

- POST /v1/sanitize  — detect and redact PII from text
- POST /v1/restore   — restore original values from a prior sanitize call

Tier capability matrix:
  dev:    email, phone
  growth: + names, addresses          (Presidio NER)
  pro:    + SSN, credit cards, DOB    (Presidio NER)
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from ..settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["privacy"])

# ---------------------------------------------------------------------------
# Presidio — loaded once at module import; gracefully absent in dev/test envs
# ---------------------------------------------------------------------------

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()
    _PRESIDIO_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PRESIDIO_AVAILABLE = False
    logger.warning("presidio not installed — name/address detection unavailable")

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SanitizeRequest(BaseModel):
    text: str
    tier: str | None = None


class SanitizeResponse(BaseModel):
    request_id: str = Field(alias="requestId")
    redacted_text: str = Field(alias="redactedText")
    entities_found: list[dict[str, Any]] = Field(alias="entitiesFound")
    tier: str


class RestoreRequest(BaseModel):
    text: str


class RestoreResponse(BaseModel):
    restored_text: str = Field(alias="restoredText")


# ---------------------------------------------------------------------------
# Redaction store with TTL eviction (in-process; use Redis in multi-instance)
# ---------------------------------------------------------------------------

_TTL_SECONDS = 3600  # 1 hour

_redaction_store: dict[str, tuple[dict[str, str], float]] = {}


def _store_set(request_id: str, mappings: dict[str, str]) -> None:
    _evict_expired()
    _redaction_store[request_id] = (mappings, time.monotonic())


def _store_get(request_id: str) -> dict[str, str]:
    entry = _redaction_store.get(request_id)
    if entry is None:
        return {}
    mappings, ts = entry
    if time.monotonic() - ts > _TTL_SECONDS:
        del _redaction_store[request_id]
        return {}
    return mappings


def _evict_expired() -> None:
    now = time.monotonic()
    expired = [k for k, (_, ts) in _redaction_store.items() if now - ts > _TTL_SECONDS]
    for k in expired:
        del _redaction_store[k]


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def _verify_service_token(x_request_id: str | None, authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    token = authorization[7:]
    if token != settings.service_token:
        raise HTTPException(status_code=403, detail="Invalid service token")
    if not x_request_id:
        raise HTTPException(status_code=400, detail="Missing X-Request-Id header")
    return x_request_id


# ---------------------------------------------------------------------------
# Entity detection
# ---------------------------------------------------------------------------

# Tiers that activate Presidio NER
_NER_TIERS = {"growth", "pro"}

# Presidio entity types mapped per tier
_PRESIDIO_ENTITIES: dict[str, list[str]] = {
    "growth": ["PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER"],
    "pro": ["PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD", "DATE_TIME"],
}

# Regex-only entities (all tiers, or Presidio fallback)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"""
    (?:\+?1[\s.\-]?)?          # optional country code
    (?:\(\d{3}\)|\d{3})        # area code
    [\s.\-]?\d{3}[\s.\-]?\d{4} # local number
    """,
    re.VERBOSE,
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_RE = re.compile(
    r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"
)


def _regex_entities(text: str, tier: str) -> list[dict[str, Any]]:
    """Fallback regex detection used when Presidio is unavailable."""
    found: list[dict[str, Any]] = []

    for m in _EMAIL_RE.finditer(text):
        found.append({"type": "EMAIL", "start": m.start(), "end": m.end(), "value": m.group()})

    for m in _PHONE_RE.finditer(text):
        found.append({"type": "PHONE", "start": m.start(), "end": m.end(), "value": m.group()})

    if tier == "pro":
        for m in _SSN_RE.finditer(text):
            found.append({"type": "SSN", "start": m.start(), "end": m.end(), "value": m.group()})
        for m in _CC_RE.finditer(text):
            found.append({"type": "CREDIT_CARD", "start": m.start(), "end": m.end(), "value": m.group()})

    return found


def _detect_entities(text: str, tier: str) -> list[dict[str, Any]]:
    if tier in _NER_TIERS and _PRESIDIO_AVAILABLE:
        entity_types = _PRESIDIO_ENTITIES[tier]
        results = _analyzer.analyze(text=text, entities=entity_types, language="en")
        return [
            {
                "type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "value": text[r.start : r.end],
                "score": round(r.score, 3),
            }
            for r in results
            if r.score >= 0.6
        ]

    return _regex_entities(text, tier)


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def _redact_text(
    text: str, entities: list[dict[str, Any]], request_id: str
) -> tuple[str, dict[str, str]]:
    mappings: dict[str, str] = {}
    result = text

    # Process highest-offset first to avoid shifting positions
    for entity in sorted(entities, key=lambda e: e["start"], reverse=True):
        placeholder = f"[REDACTED:{entity['type']}:{len(mappings)}]"
        mappings[placeholder] = entity["value"]
        result = result[: entity["start"]] + placeholder + result[entity["end"] :]

    _store_set(request_id, mappings)
    return result, mappings


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sanitize", response_model=SanitizeResponse)
async def sanitize(
    request: SanitizeRequest,
    x_tenant_id: str = Header(...),
    x_request_id: str = Header(...),
    authorization: str | None = Header(None),
) -> SanitizeResponse:
    _verify_service_token(x_request_id, authorization)

    tier = request.tier or settings.default_tier
    if tier not in ("dev", "growth", "pro"):
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier!r}")

    entities = _detect_entities(request.text, tier)
    redacted_text, _ = _redact_text(request.text, entities, x_request_id)

    logger.info(
        "sanitize tenant=%s request_id=%s tier=%s entities=%d",
        x_tenant_id,
        x_request_id,
        tier,
        len(entities),
    )

    return SanitizeResponse(
        request_id=x_request_id,
        redacted_text=redacted_text,
        entities_found=entities,
        tier=tier,
    )


@router.post("/restore", response_model=RestoreResponse)
async def restore(
    request: RestoreRequest,
    x_tenant_id: str = Header(...),
    x_request_id: str = Header(...),
    authorization: str | None = Header(None),
) -> RestoreResponse:
    _verify_service_token(x_request_id, authorization)

    mappings = _store_get(x_request_id)
    if not mappings:
        logger.warning("restore called with unknown/expired request_id=%s", x_request_id)

    result = request.text
    for placeholder, original in mappings.items():
        result = result.replace(placeholder, original)

    return RestoreResponse(restored_text=result)
