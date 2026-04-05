FROM python:3.12-slim

WORKDIR /app

# Install dependencies from repo root
COPY pyproject.toml README.md ./
COPY packages ./packages
RUN pip install --no-cache-dir .

# Copy service code
COPY services/privacy ./services/privacy

WORKDIR /app/services/privacy

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 3010

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3010"]
