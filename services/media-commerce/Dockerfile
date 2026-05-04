# Media & Commerce Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code (includes skills in app/skills/)
COPY app/ ./app/

# Set environment
ENV PYTHONPATH=/app

EXPOSE 8087

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8087/health', timeout=5); exit(0 if r.status_code==200 else 1)" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8087"]
