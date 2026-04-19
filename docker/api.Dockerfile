FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8 shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 app

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY resume_builder.py ats_checker.py cli.py discovery.py ./
COPY api ./api
COPY templates ./templates
COPY fonts ./fonts
COPY data ./data

RUN mkdir -p /app/db /app/outputs && chown -R app:app /app/db /app/outputs

USER app

ENV PYTHONUNBUFFERED=1
ENV RESUME_BUILDER_REPO_ROOT=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
