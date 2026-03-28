FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY config.yml ./config.yml
COPY core ./core
COPY ingest ./ingest
COPY ml ./ml
COPY backend ./backend

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ./core -e ./ingest -e ./ml -e "./backend[genai]"

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
