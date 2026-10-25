#!/bin/sh
# 仕様: docs/spec/db-persistence.md#実現内容what (起動時の復元 / 停止時の最終同期)
#
# 順序: 設定の確認 -> 2つの DB の復元 -> 2つの DB を WAL 化 -> Litestream の複製 + アプリ(gunicorn)。
# 復元が終わる前に DB へ書き込む処理(スキーマ適用など)は動かさない。
# 復元に失敗したら、空の DB で起動せず、非0で終わる。
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONFIG="${LITESTREAM_CONFIG:-$DIR/litestream.yml}"

LEARNING_DB_PATH="${LEARNING_DB_PATH:-/app/db/data/learning.db}"
TUTOR_DB_PATH="${TUTOR_DB_PATH:-/app/db/data/tutor.db}"
export LEARNING_DB_PATH TUTOR_DB_PATH

# 終了猶予は Cloud Run の停止の猶予(10秒)より短く(AC19)。SECRET_KEY などの環境変数はそのまま引き継ぐ。
GUNICORN_CMD="gunicorn -w 1 -b 0.0.0.0:${PORT:-8080} --timeout 120 --graceful-timeout 4 framework_drivers.platform.main:app"

if [ "${DB_REPLICA_DISABLED:-}" = "1" ]; then
  echo "DB_REPLICA_DISABLED=1: 複製しない(復元も複製もせずにアプリを起動する)" >&2
  exec $GUNICORN_CMD
fi

if [ -z "${DB_REPLICA_BUCKET:-}" ]; then
  echo "エラー: 複製先の設定がない(DB_REPLICA_BUCKET が未設定または空)。" >&2
  echo "  Cloud Run では DB_REPLICA_BUCKET にバケット名を設定する。ローカルで複製しないときは DB_REPLICA_DISABLED=1 を指定する。" >&2
  exit 1
fi

mkdir -p "$(dirname -- "$LEARNING_DB_PATH")" "$(dirname -- "$TUTOR_DB_PATH")"

restore_db() {
  # 複製がなければ(初回)何もせず成功。複製があるのに失敗したら非0。
  if ! litestream restore -config "$CONFIG" -if-replica-exists "$1"; then
    echo "エラー: 復元に失敗した(DB: $1, 複製先: gs://${DB_REPLICA_BUCKET})。空の DB では起動しない。" >&2
    exit 1
  fi
}

restore_db "$LEARNING_DB_PATH"
restore_db "$TUTOR_DB_PATH"

# 復元の後に、明示に WAL 化する(Litestream の挙動に頼らない。AC21)。DB がなければ作られる。
for db in "$LEARNING_DB_PATH" "$TUTOR_DB_PATH"; do
  python -c '
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])
try:
    mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
finally:
    conn.close()
if str(mode).lower() != "wal":
    sys.exit("WAL にできない: %s (%s)" % (sys.argv[1], mode))
' "$db" || { echo "エラー: WAL 化に失敗した: $db" >&2; exit 1; }
done

exec litestream replicate -config "$CONFIG" -exec "$GUNICORN_CMD"
