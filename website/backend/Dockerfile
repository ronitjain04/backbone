FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 CORPUS_PATH=/app/website/backend/data/demo.jsonl RETRIEVAL_MODE=lexical
COPY website/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --create-home backbone
COPY website/backend /app/website/backend
USER backbone
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn website.backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
