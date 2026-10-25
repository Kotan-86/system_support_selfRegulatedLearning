# 仕様: docs/spec/db-persistence.md / docs/spec/framework-drivers-layer.md#デプロイ・運用

# --- ビルド用: 修正済みの SQLite(AC20)と Litestream v0.5.17 を用意する ---
# python:3.12-slim(Debian)の libsqlite3 は、WAL-reset の不具合の修正済みの版(3.51.3 以上など)より
# 古い見込みのため、SQLite をソースからビルドして差し替える。最終的な合否は、下の RUN の版の確認が決める。
FROM python:3.12-slim AS fetch
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

ARG SQLITE_YEAR=2026
ARG SQLITE_AUTOCONF=3510300
RUN curl -fsSL "https://www.sqlite.org/${SQLITE_YEAR}/sqlite-autoconf-${SQLITE_AUTOCONF}.tar.gz" -o /tmp/sqlite.tar.gz \
    && tar -xzf /tmp/sqlite.tar.gz -C /tmp \
    && cd "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF}" \
    && ./configure --prefix=/opt/sqlite \
    && make -j"$(nproc)" \
    && make install

ARG LITESTREAM_VERSION=0.5.17
RUN curl -fsSL "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-x86_64.tar.gz" -o /tmp/litestream.tar.gz \
    && tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin litestream \
    && /usr/local/bin/litestream version

# --- 実行用 ---
FROM python:3.12-slim

WORKDIR /app

# 修正済みの SQLite を、システムの libsqlite3 より先に読み込ませる
COPY --from=fetch /opt/sqlite/lib /opt/sqlite/lib
ENV LD_LIBRARY_PATH=/opt/sqlite/lib
COPY --from=fetch /usr/local/bin/litestream /usr/local/bin/litestream

# uv で本番依存のみインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ランタイムに必要なソースのみ(参加者の資格情報の設定ファイルは COPY しない。Secret Manager で /secrets/ に渡す)
COPY application ./application
COPY domain ./domain
COPY interfaces ./interfaces
COPY framework_drivers ./framework_drivers
COPY db ./db
COPY lectures ./lectures
COPY deploy ./deploy

ENV PORT=8080
EXPOSE 8080
ENV PATH="/app/.venv/bin:$PATH"
ENV LEARNING_DB_PATH=/app/db/data/learning.db
ENV TUTOR_DB_PATH=/app/db/data/tutor.db

# AC20: アプリが使う Python の SQLite が修正済みの版でなければ、ビルドを失敗させる
RUN python deploy/sqlite_version_check.py

# 起動の入口: 復元 -> WAL 化 -> Litestream の複製 + gunicorn(終了猶予 4 秒は entrypoint.sh)
CMD ["sh", "/app/deploy/entrypoint.sh"]
