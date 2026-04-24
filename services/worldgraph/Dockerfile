FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
RUN pip install --no-cache-dir .

COPY services/worldgraph ./services/worldgraph

WORKDIR /app/services/worldgraph

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
