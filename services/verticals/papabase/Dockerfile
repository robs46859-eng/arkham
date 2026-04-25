FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package folder for vertical_base import
COPY packages /app/packages
COPY services/verticals/papabase/app /app/app

ENV PYTHONPATH=/app
ENV PORT=8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
