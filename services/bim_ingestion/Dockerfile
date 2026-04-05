FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
RUN pip install --no-cache-dir .

COPY services/bim_ingestion ./services/bim_ingestion

WORKDIR /app/services/bim_ingestion

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
