FROM python:3.11-slim

WORKDIR /app

COPY services/verticals/ai_consistency/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/verticals/ai_consistency/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
