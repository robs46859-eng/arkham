#!/bin/sh
set -e
alembic upgrade head
exec uvicorn services.arkham.app.main:app --host 0.0.0.0 --port 8080
