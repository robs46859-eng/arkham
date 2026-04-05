"""
PII redaction and restoration endpoints.

Implements:
- POST /v1/sanitize - Detect and redact PII from text
- POST /v1/restore - Restore original values from redacted text
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from ..settings import settings

router = APIRouter(prefix="/v1", tags=["privacy"])


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
    tier: str | None = None


class RestoreResponse(BaseModel):
    restored_text: str = Field(alias="restoredText")


# In-memory storage for redaction mappings (use Redis in production)
_redaction_store: dict[str, dict[str, str]] = {}


def _verify_service_token(x_request_id: str | None, authorization: str | None) -> str:
    """Verify internal service authentication."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

    token = authorization.replace("Bearer ", "")
    if token != settings.service_token:
        raise HTTPException(status_code=403, detail="Invalid service token")

    if not x_request_id:
        raise HTTPException(status_code=400, detail="Missing X-Request-Id header")

    return x_request_id


def _detect_entities(text: str, tier: str) -> list[dict[str, Any]]:
    """
    Detect PII entities based on privacy tier.

    Tiers:
    - dev: email, phone
    - growth: + person names, addresses
    - pro: + SSN, credit cards, dates of birth
    """
    entities = []

    # Email detection (all tiers)
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    for match in re.finditer(email_pattern, text):
        entities.append(
            {
                "type": "EMAIL",
                "start": match.start(),
                "end": match.end(),
                "value": match.group(),
            }
        )

    # Phone detection (all tiers) - simple US format
    phone_pattern = r"\b(?:\+?1[-.\s]?)?\(?(?:[0-9]{3})\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
    for match in re.finditer(phone_pattern, text):
        entities.append(
            {
                "type": "PHONE",
                "start": match.start(),
                "end": match.end(),
                "value": match.group(),
            }
        )

    if tier in ("growth", "pro"):
        # Simple name detection (capitalized words - basic heuristic)
        name_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"
        for match in re.finditer(name_pattern, text):
            # Filter out common false positives
            value = match.group()
            if not any(word in value.lower() for word in ["the", "and", "with", "from", "this"]):
                entities.append(
                    {
                        "type": "PERSON",
                        "start": match.start(),
                        "end": match.end(),
                        "value": value,
                    }
                )

        # Address detection (basic - street numbers)
        address_pattern = (
            r"\b\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\b"
        )
        for match in re.finditer(address_pattern, text, re.IGNORECASE):
            entities.append(
                {
                    "type": "ADDRESS",
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group(),
                }
            )

    if tier == "pro":
        # SSN detection
        ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
        for match in re.finditer(ssn_pattern, text):
            entities.append(
                {
                    "type": "SSN",
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group(),
                }
            )

        # Credit card detection (basic patterns)
        cc_pattern = r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        for match in re.finditer(cc_pattern, text):
            entities.append(
                {
                    "type": "CREDIT_CARD",
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group(),
                }
            )

    return entities


def _redact_text(text: str, entities: list[dict[str, Any]], request_id: str) -> tuple[str, dict[str, str]]:
    """Replace entities with placeholders and store mapping."""
    mappings = {}
    result = text

    # Sort by position descending to avoid offset issues
    sorted_entities = sorted(entities, key=lambda e: e["start"], reverse=True)

    for entity in sorted_entities:
        placeholder = f"[REDACTED:{entity['type']}:{len(mappings)}]"
        mappings[placeholder] = entity["value"]
        result = result[: entity["start"]] + placeholder + result[entity["end"] :]

    # Store mappings for restoration
    _redaction_store[request_id] = mappings

    return result, mappings


@router.post("/sanitize", response_model=SanitizeResponse)
async def sanitize(
    request: SanitizeRequest,
    x_tenant_id: str = Header(..., description="Tenant identifier"),
    x_request_id: str = Header(..., description="Request identifier"),
    authorization: str | None = Header(None, description="Service auth token"),
) -> SanitizeResponse:
    """
    Sanitize text by detecting and redacting PII.

    Returns redacted text along with a request ID for later restoration.
    """
    _verify_service_token(x_request_id, authorization)

    tier = request.tier or settings.default_tier
    if tier not in ("dev", "growth", "pro"):
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    entities = _detect_entities(request.text, tier)
    redacted_text, _ = _redact_text(request.text, entities, x_request_id)

    return SanitizeResponse(
        request_id=x_request_id,
        redacted_text=redacted_text,
        entities_found=entities,
        tier=tier,
    )


@router.post("/restore", response_model=RestoreResponse)
async def restore(
    request: RestoreRequest,
    x_tenant_id: str = Header(..., description="Tenant identifier"),
    x_request_id: str = Header(..., description="Original request identifier"),
    authorization: str | None = Header(None, description="Service auth token"),
) -> RestoreResponse:
    """
    Restore original PII values in previously redacted text.

    Uses the request ID from the original sanitization call.
    """
    _verify_service_token(x_request_id, authorization)

    mappings = _redaction_store.get(x_request_id, {})
    result = request.text

    # Replace placeholders with original values
    for placeholder, original_value in mappings.items():
        result = result.replace(placeholder, original_value)

    return RestoreResponse(restored_text=result)
