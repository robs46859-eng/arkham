FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
RUN pip install --no-cache-dir .

COPY services/verticals/workflow_architect ./services/verticals/workflow_architect

WORKDIR /app/services/verticals/workflow_architect

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 3099

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3099"]
