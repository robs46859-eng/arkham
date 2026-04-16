"""
Billing proxy routes — gateway forwards billing requests to the billing service.

/billing/checkout  → POST  — create Stripe checkout session (tenant auth required)
/billing/portal    → POST  — create customer portal session (tenant auth required)
/billing/webhook   → POST  — Stripe webhook (public, signature-verified by billing service)

The webhook is the key reason this proxy exists: the billing service is
INGRESS_TRAFFIC_INTERNAL_ONLY so Stripe cannot reach it directly. All external
traffic enters through the gateway, which forwards with the raw body and
Stripe-Signature header preserved.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from ..settings import settings

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)

_BILLING_TIMEOUT = 30.0  # seconds


def _billing_url(path: str) -> str:
    base = settings.billing_service_url.rstrip("/")
    return f"{base}/billing/{path.lstrip('/')}"


# ── Webhook proxy (no auth — Stripe-Signature verified downstream) ─────────────

@router.post("/webhook")
async def proxy_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> JSONResponse:
    """Forward Stripe webhook to billing service with raw body preserved."""
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")

    raw_body = await request.body()
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": stripe_signature,
    }

    try:
        async with httpx.AsyncClient(timeout=_BILLING_TIMEOUT) as client:
            resp = await client.post(_billing_url("webhook"), content=raw_body, headers=headers)
    except httpx.RequestError as exc:
        logger.error("Billing service unreachable for webhook: %s", exc)
        raise HTTPException(status_code=503, detail="Billing service unavailable.") from exc

    return JSONResponse(status_code=resp.status_code, content=resp.json())


# ── Checkout proxy (tenant auth forwarded as-is) ──────────────────────────────

@router.post("/checkout")
async def proxy_checkout(request: Request) -> JSONResponse:
    """Forward checkout session creation to billing service."""
    raw_body = await request.body()
    headers = _forward_headers(request)

    try:
        async with httpx.AsyncClient(timeout=_BILLING_TIMEOUT) as client:
            resp = await client.post(_billing_url("checkout"), content=raw_body, headers=headers)
    except httpx.RequestError as exc:
        logger.error("Billing service unreachable for checkout: %s", exc)
        raise HTTPException(status_code=503, detail="Billing service unavailable.") from exc

    return JSONResponse(status_code=resp.status_code, content=resp.json())


# ── Portal proxy (tenant auth forwarded as-is) ────────────────────────────────

@router.post("/portal")
async def proxy_portal(request: Request) -> JSONResponse:
    """Forward customer portal session creation to billing service."""
    headers = _forward_headers(request)

    try:
        async with httpx.AsyncClient(timeout=_BILLING_TIMEOUT) as client:
            resp = await client.post(_billing_url("portal"), headers=headers)
    except httpx.RequestError as exc:
        logger.error("Billing service unreachable for portal: %s", exc)
        raise HTTPException(status_code=503, detail="Billing service unavailable.") from exc

    return JSONResponse(status_code=resp.status_code, content=resp.json())


def _forward_headers(request: Request) -> dict:
    """Extract auth headers to forward to billing service."""
    headers = {"Content-Type": "application/json"}
    if auth := request.headers.get("Authorization"):
        headers["Authorization"] = auth
    return headers
