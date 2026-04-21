import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from services.arkham.app.main import _ensure_persona
from tests.conftest import MockSession


def test_ensure_persona_creates_missing_persona():
    db = MockSession()

    persona = _ensure_persona(
        db,
        persona_id="persona_test_001",
        tenant_id="tenant_test",
        checkpoint="intake",
    )

    assert persona.id == "persona_test_001"
    assert persona.tenant_id == "tenant_test"
    assert persona.owner_tenant == "tenant_test"
    assert persona.state == "intake"

    stored = db.query(type(persona)).filter_by(id="persona_test_001").first()
    assert stored is not None


def test_ensure_persona_reuses_existing_persona():
    db = MockSession()

    first = _ensure_persona(
        db,
        persona_id="persona_existing",
        tenant_id="tenant_test",
        checkpoint="intake",
    )
    second = _ensure_persona(
        db,
        persona_id="persona_existing",
        tenant_id="tenant_test",
        checkpoint="probation",
    )

    assert second.id == first.id
    assert second.tenant_id == first.tenant_id
    assert len(db.query(type(first)).all()) == 1
