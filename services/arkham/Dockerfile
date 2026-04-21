FROM python:3.12-slim

WORKDIR /app

COPY services/arkham/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY packages ./packages
COPY services/arkham ./services/arkham
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

ENV PYTHONPATH=/app

COPY services/arkham/start.sh ./start.sh
RUN chmod +x ./start.sh

CMD ["./start.sh"]
