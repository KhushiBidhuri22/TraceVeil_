FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend_requirements.txt

RUN pip install --no-cache-dir \
    -r /app/backend_requirements.txt

COPY backend /app/backend
COPY ml /app/ml
COPY frontend /app/frontend

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]