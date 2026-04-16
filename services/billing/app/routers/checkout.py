"""
Billing checkout and customer portal endpoints.

POST /billing/checkout  — create a Stripe Checkout Session for a tenant.
POST /billing/portal    — create a Stripe Customer Portal session.

Both endpoints require a valid tenant JWT (Authorization: Bearer <token>).
The billing service verifies the token itself using the shared signing_key
so it can be called directly from the frontend or via the gateway.
"""

from __future__ import annotations

from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.db import get_db
from packages.models import Tenant

from ..auth import require_tenant
from ..settings import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def _stripe() -> stripe.Stripe:
    return stripe.Stripe(settings.stripe_secret_key)


def _get_tenant(tenant_id: str, db) -> Tenant:
    tenant = db.get(Tenant, tenant_id) if hasattr(db, "get") else db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found.")
    return tenant


# ── Checkout ──────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    price_id: Optional[str] = None  # falls back to settings.stripe_price_id


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    body: CheckoutRequest,
    tenant_auth: tuple[str, str] = Depends(require_tenant),
    db=Depends(get_db),
) -> CheckoutResponse:
    """
    Create a Stripe Checkout Session for the authenticated tenant.
    Returns the hosted checkout URL; the frontend redirects the user there.
    """
    tenant_id, _ = tenant_auth
    tenant = _get_tenant(tenant_id, db)

    price_id = body.price_id or settings.stripe_price_id
    client = _stripe()

    # Reuse existing Stripe customer if one already exists for this tenant.
    customer_id = getattr(tenant, "stripe_customer_id", None)

    session_kwargs: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{settings.stripe_success_url}?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": settings.stripe_cancel_url,
        "metadata": {"tenant_id": tenant_id},
        "subscription_data": {"metadata": {"tenant_id": tenant_id}},
    }

    if customer_id:
        session_kwargs["customer"] = customer_id
    else:
        session_kwargs["customer_email"] = None  # Stripe prompts for email at checkout

    try:
        session = client.checkout.sessions.create(**session_kwargs)
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message}") from exc

    return CheckoutResponse(checkout_url=session.url, session_id=session.id)


# ── Customer Portal ───────────────────────────────────────────────────────────

class PortalResponse(BaseModel):
    portal_url: str


@router.post("/portal", response_model=PortalResponse)
def create_portal_session(
    tenant_auth: tuple[str, str] = Depends(require_tenant),
    db=Depends(get_db),
) -> PortalResponse:
    """
    Create a Stripe Customer Portal session for the authenticated tenant.
    The tenant must have completed at least one checkout (stripe_customer_id must exist).
    """
    tenant_id, _ = tenant_auth
    tenant = _get_tenant(tenant_id, db)

    customer_id = getattr(tenant, "stripe_customer_id", None)
    if not customer_id:
        raise HTTPException(
            status_code=409,
            detail="No billing account found. Complete a checkout first.",
        )

    client = _stripe()
    try:
        session = client.billing_portal.sessions.create(
            customer=customer_id,
            return_url=settings.stripe_portal_return_url,
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message}") from exc

    return PortalResponse(portal_url=session.url)
