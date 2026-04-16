FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
RUN pip install --no-cache-dir .

COPY services/billing ./services/billing

WORKDIR /app/services/billing

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 3020

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3020"]
