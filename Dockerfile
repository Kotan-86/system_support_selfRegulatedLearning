FROM python:3.12-slim

WORKDIR /app

# uv で本番依存のみインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ランタイムに必要なソースのみ
COPY application ./application
COPY domain ./domain
COPY interfaces ./interfaces
COPY framework_drivers ./framework_drivers
COPY db ./db
COPY lectures ./lectures

ENV PORT=8080
EXPOSE 8080
ENV PATH="/app/.venv/bin:$PATH"

# 仕様: docs/spec/framework-drivers-layer.md#デプロイ・運用
CMD gunicorn -w 1 -b 0.0.0.0:${PORT} --timeout 120 framework_drivers.platform.main:app
