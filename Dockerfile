# ---------- Stage 1: build React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python backend + static assets ----------
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
# bcc is Linux-kernel-only and not needed on Cloud Run; CPU torch keeps the image small
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && grep -viE '^\s*(bcc)\b' requirements.txt > /tmp/req.txt \
 && pip install -r /tmp/req.txt

COPY . .
COPY --from=frontend /fe/dist /app/static
RUN mkdir -p logs controller/models

ENV NBT_REMEDIATION_MODE=simulate \
    NBT_REMEDIATION_DB=/tmp/remediation.sqlite3

EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
