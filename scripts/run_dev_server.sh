#!/usr/bin/env bash
# 仕様: docs/spec/framework-drivers-layer.md#環境変数必須推奨
# ローカル開発: .env.local 読み込み → DB 初期化 → Flask 起動（port 5001）
# コマンド： ./scripts/run_dev_server.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.local ]]; then
  echo "error: .env.local が見つかりません（$ROOT/.env.local）" >&2
  echo "  .env.example を参考に作成してください。" >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source .env.local
set +a

# 参加者ログイン(docs/spec/participant-login.md)。ローカルは HTTP のため Cookie の Secure を外す
# (.env.local に値があればそれを優先)。本番(HTTPS)では設定しない。
export SESSION_COOKIE_SECURE_DISABLED="${SESSION_COOKIE_SECURE_DISABLED:-1}"
export PARTICIPANT_CREDENTIALS_FILE="${PARTICIPANT_CREDENTIALS_FILE:-secrets/participants.json}"

if [[ -z "${SECRET_KEY:-}" ]]; then
  echo "error: SECRET_KEY が未設定です。.env.local に設定してください(生成方法は README 参照)。" >&2
  exit 1
fi
if [[ ! -f "$PARTICIPANT_CREDENTIALS_FILE" ]]; then
  echo "error: 参加者の設定ファイルが見つかりません（$PARTICIPANT_CREDENTIALS_FILE）。" >&2
  echo "  uv run python scripts/manage_participants.py add で作成してください(README 参照)。" >&2
  exit 1
fi

case "${USE_HTTP_PROXY:-}" in
  1|true|yes|TRUE|True)
    echo "note: USE_HTTP_PROXY is enabled. Off-campus networks require USE_HTTP_PROXY=false in .env.local."
    ;;
  *)
    echo "note: USE_HTTP_PROXY is disabled; clearing HTTP(S)_PROXY for direct connection."
    unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
    ;;
esac

echo "Resetting databases (removing existing data)..."
uv run python -c "from framework_drivers.platform.wiring import reset_databases; reset_databases()"

echo "Starting Flask on http://127.0.0.1:5001 ..."
exec uv run flask --app framework_drivers.platform.main run --port 5001
