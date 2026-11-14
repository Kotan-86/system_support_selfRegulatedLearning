# 仕様: docs/spec/db-persistence.md / docs/spec/framework-drivers-layer.md#デプロイ・運用

# --- ビルド用: 修正済みの SQLite(AC20)と Litestream v0.5.17 を用意する ---
# python:3.12-slim(Debian)の libsqlite3 は、WAL-reset の不具合の修正済みの版(3.51.3 以上など)より
# 古い見込みのため、SQLite をソースからビルドして差し替える。最終的な合否は、下の RUN の版の確認が決める。
# 再現性のため版を固定。fetch ステージと実行ステージで同じ Debian にそろえる
ARG PYTHON_VERSION=3.12.16

# Litestream は公式イメージから取り出す。GitHub のリリースからの取得は、Cloud Build から 504 で
# 失敗し続けることがあった(2026-11-09)。版はタグで示し、中身は digest で固定する
ARG LITESTREAM_VERSION=0.5.17
# 再現性のため uv の版を固定。Cloud Build の docker build(BuildKit なし)は COPY --from の
# 変数を展開しないため、版の変数は FROM で使い、ステージ名から COPY する
ARG UV_VERSION=0.13.1
# FROM で使う ARG は、最初の FROM より前に置く(後ろに置くと、そのステージの中だけの変数になる)

FROM litestream/litestream:${LITESTREAM_VERSION}@sha256:4b02b9859a6b6b4087d8b8944e15f7e984bd7957cba322bbeee38b0e27b9656a AS litestream
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim AS fetch
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

COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream
RUN /usr/local/bin/litestream version

# --- 実行用 ---
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# 修正済みの SQLite を、システムの libsqlite3 より先に読み込ませる
COPY --from=fetch /opt/sqlite/lib /opt/sqlite/lib
ENV LD_LIBRARY_PATH=/opt/sqlite/lib
COPY --from=fetch /usr/local/bin/litestream /usr/local/bin/litestream

# uv で本番依存のみインストール
COPY --from=uv /uv /usr/local/bin/uv
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
