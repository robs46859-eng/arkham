"""
Stripe webhook handler.

POST /billing/webhook

Handles:
  checkout.session.completed        — link Stripe customer + subscription to tenant, upgrade plan
  customer.subscription.updated     — sync plan on renewal, upgrade, or downgrade
  customer.subscription.deleted     — downgrade tenant to free

Security: Stripe-Signature header is verified against the webhook secret before
any payload is processed. Unverified requests are rejected with 400.

Routing note: This endpoint is reached via gateway proxy at /billing/webhook.
The gateway passes the raw request body and Stripe-Signature header unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session

from packages.db import get_db
from packages.models import Tenant
from fastapi import Depends

from ..settings import settings

router = APIRouter(prefix="/billing", tags=["billing-webhook"])
logger = logging.getLogger(__name__)

# Map Stripe subscription status → internal plan name
_STATUS_TO_PLAN: dict[str, str] = {
    "active": "pro",
    "trialing": "pro",
    "past_due": "pro",   # keep access during grace period
    "canceled": "free",
    "unpaid": "free",
    "incomplete": "free",
    "incomplete_expired": "free",
    "paused": "free",
}


def _find_tenant_by_customer(db: Session, customer_id: str) -> Tenant | None:
    if hasattr(db, "query"):
        return db.query(Tenant).filter_by(stripe_customer_id=customer_id).first()
    # async-style session fallback
    return db.execute(
        Tenant.__table__.select().where(Tenant.stripe_customer_id == customer_id)
    ).first()


@router.post("/webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Receive and process Stripe webhook events.
    Stripe-Signature is verified before any processing occurs.
    """
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError as exc:
        logger.warning("Webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature.") from exc
    except Exception as exc:
        logger.error("Webhook payload parse error: %s", exc)
        raise HTTPException(status_code=400, detail="Malformed webhook payload.") from exc

    event_type = event["type"]
    logger.info("Received Stripe event: %s (id=%s)", event_type, event["id"])

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(event["data"]["object"], db)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _handle_subscription_change(event["data"]["object"], db)
    else:
        logger.debug("Unhandled event type: %s — ignoring", event_type)

    return {"received": True}


# ── Event handlers ─────────────────────────────────────────────────────────────

def _handle_checkout_completed(session: dict, db: Session) -> None:
    """
    Link Stripe customer + subscription to the tenant and set plan to 'pro'.
    Called when a tenant completes checkout for the first time.
    """
    tenant_id = (session.get("metadata") or {}).get("tenant_id")
    if not tenant_id:
        logger.warning("checkout.session.completed missing tenant_id in metadata — skipping")
        return

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if hasattr(db, "get"):
        tenant = db.get(Tenant, tenant_id)
    else:
        tenant = db.query(Tenant).filter_by(id=tenant_id).first()

    if not tenant:
        logger.error("checkout.session.completed: tenant %s not found — skipping", tenant_id)
        return

    tenant.stripe_customer_id = customer_id
    tenant.stripe_subscription_id = subscription_id
    tenant.plan = "pro"
    tenant.updated_at = datetime.utcnow()

    if hasattr(db, "commit"):
        db.commit()

    logger.info(
        "Tenant %s upgraded to pro (customer=%s, subscription=%s)",
        tenant_id,
        customer_id,
        subscription_id,
    )


def _handle_subscription_change(subscription: dict, db: Session) -> None:
    """
    Sync tenant plan based on subscription status.
    Called on renewals, upgrades, downgrades, and cancellations.
    """
    customer_id = subscription.get("customer")
    status = subscription.get("status", "")
    subscription_id = subscription.get("id")

    tenant = _find_tenant_by_customer(db, customer_id)
    if not tenant:
        logger.warning(
            "subscription event for unknown customer %s — skipping", customer_id
        )
        return

    new_plan = _STATUS_TO_PLAN.get(status, "free")
    old_plan = getattr(tenant, "plan", "free")

    tenant.plan = new_plan
    tenant.stripe_subscription_id = subscription_id
    tenant.updated_at = datetime.utcnow()

    if hasattr(db, "commit"):
        db.commit()

    logger.info(
        "Tenant %s plan %s → %s (subscription=%s, status=%s)",
        tenant.id,
        old_plan,
        new_plan,
        subscription_id,
        status,
    )
