# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies into an isolated prefix so we can copy cleanly
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Ensure Python output is not buffered (so logs appear immediately)
ENV PYTHONUNBUFFERED=1

# Expose health check port
EXPOSE 8080

# Run the watcher
CMD ["python", "main.py"]
