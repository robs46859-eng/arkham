#!/bin/sh
set -e
python3 -c "
import os, sqlalchemy as sa
engine = sa.create_engine(os.environ['DATABASE_URL'])
with engine.connect() as c:
    try:
        row = c.execute(sa.text('SELECT version_num FROM alembic_version LIMIT 1')).fetchone()
    except Exception:
        row = None
    if not row:
        c.execute(sa.text(\"INSERT INTO alembic_version (version_num) VALUES ('20260407_0005') ON CONFLICT DO NOTHING\"))
        c.commit()
" 2>/dev/null || true
alembic upgrade head
exec uvicorn services.arkham.app.main:app --host 0.0.0.0 --port 8080
