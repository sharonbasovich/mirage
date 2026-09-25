# Mirage — single-container build: frontend build + FastAPI backend
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY mirage/ ./mirage/
COPY data/ ./data/
RUN pip install --no-cache-dir .
COPY --from=frontend /app/frontend/dist ./frontend/dist
EXPOSE 8000
CMD ["uvicorn", "mirage.api:app", "--host", "0.0.0.0", "--port", "8000"]
