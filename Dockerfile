# syntax=docker/dockerfile:1
# Single-service image: build the React SPA with Node, then serve API + SPA with Python.

# --- 1. Build the SPA (Vite needs Node) -------------------------------------
FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
# VITE_API_BASE intentionally unset -> the SPA calls the same origin it's served from.
RUN npm run build

# --- 2. Python runtime (serves the API + the built SPA) ---------------------
FROM python:3.12-slim AS run
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8000
WORKDIR /app

# Editable install keeps the package at /app/src so the app's repo-root lookup
# (Path(__file__).parents[3]) resolves to /app — i.e. /app/frontend/dist,
# /app/config.yaml and /app/data all resolve correctly.
COPY pyproject.toml README.md ./
COPY src ./src
COPY config.yaml config_advanced.yaml ./
RUN pip install -e .

# The built SPA from stage 1 (served at "/" by FastAPI).
COPY --from=web /app/frontend/dist ./frontend/dist

# Bake the baseline + stress datasets so the first request is instant.
RUN python -c "from verified_financials import datagen; datagen.generate(scenario='baseline'); datagen.generate(scenario='stress')"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn verified_financials.api.app:app --host 0.0.0.0 --port ${PORT}"]
