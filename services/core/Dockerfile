FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
RUN pip install --no-cache-dir .

COPY services/core ./services/core

WORKDIR /app/services/core

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
