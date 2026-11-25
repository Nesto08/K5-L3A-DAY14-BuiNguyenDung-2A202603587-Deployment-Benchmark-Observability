FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime

RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

COPY --from=builder /install /usr/local

COPY app/ ./app/
COPY utils/ ./utils/

RUN chown -R agent:agent /app

USER agent

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

# One worker per container for consistent Prometheus metrics.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
