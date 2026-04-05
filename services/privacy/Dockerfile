"""Privacy service Dockerfile."""

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[privacy]"

# Copy application code
COPY packages/ ./packages/
COPY services/privacy/ ./services/privacy/

# Set environment variables
ENV PYTHONPATH=/app
ENV APP_ENV=production

# Expose port
EXPOSE 3010

# Run the service
CMD ["uvicorn", "services.privacy.app.main:app", "--host", "0.0.0.0", "--port", "3010"]
