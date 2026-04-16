"""
Billing service settings.
Implements: Build Rules §4 — No untyped environment access.
"""

from packages.config.base import BaseServiceSettings, build_settings


class Settings(BaseServiceSettings):
    service_name: str = "billing"

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str

    # The Stripe Price ID tenants are subscribing to.
    # Set per environment (test vs live price IDs differ).
    stripe_price_id: str

    # JWT signing key — same secret as gateway so tenant tokens are verifiable here too.
    signing_key: str

    # URLs embedded in Stripe checkout / portal sessions.
    # These should point to the frontend app.
    stripe_success_url: str = "https://your-app.example.com/billing/success"
    stripe_cancel_url: str = "https://your-app.example.com/billing/cancel"
    stripe_portal_return_url: str = "https://your-app.example.com/billing"

    def require_runtime_config(self) -> None:
        if self.is_test:
            return
        missing = []
        for field in ("stripe_secret_key", "stripe_webhook_secret", "stripe_price_id", "signing_key"):
            if not getattr(self, field, None):
                missing.append(field.upper())
        if missing:
            raise ValueError(
                f"Missing required environment variables for billing: {', '.join(missing)}"
            )


settings: Settings = build_settings(Settings)  # type: ignore[assignment]
settings.require_runtime_config()
