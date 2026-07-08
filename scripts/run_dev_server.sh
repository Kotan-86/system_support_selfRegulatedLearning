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
