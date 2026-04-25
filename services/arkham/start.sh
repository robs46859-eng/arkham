#!/bin/sh
set -e
python3 -c "
import os
import sqlalchemy as sa

url = os.environ['DATABASE_URL']
engine = sa.create_engine(url)
with engine.begin() as c:
    c.execute(sa.text('''
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
    '''))
    row = c.execute(sa.text('SELECT version_num FROM alembic_version LIMIT 1')).fetchone()
    if not row:
        c.execute(sa.text(\"INSERT INTO alembic_version (version_num) VALUES ('20260407_0005')\"))
        print('Stamped alembic baseline to 20260407_0005')
    else:
        print('alembic_version already set to:', row[0])
"
if ! alembic upgrade head; then
    echo "Arkham startup warning: alembic upgrade head failed; continuing with existing schema." >&2
fi
exec uvicorn services.arkham.app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
