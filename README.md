# system_support_selfRegulatedLearning

LLM チューター（Vertex AI Gemini）と対話履歴の SQLite 永続化。

## セットアップ・実行

```bash
uv sync
uv run flask --app app.main run
```

## 環境変数（Gemini Enterprise Agent Platform / 旧 Vertex AI）

- **GOOGLE_APPLICATION_CREDENTIALS** … サービスアカウント JSON のパス（未設定時は gcloud ADC を使用）
- **VERTEX_PROJECT_ID** … GCP プロジェクト ID（SA JSON の `project_id` と一致させる）
- **VERTEX_LOCATION** … リージョン（例: `us-east4`）
- **VERTEX_MODEL_NAME** … 任意（未設定時は Gateway のデフォルトモデル）

GCP の API 有効化・課金・SA ロールは次で検証する:

```bash
set -a && source .env.local && set +a
uv run python scripts/verify_gcp_agent_platform.py
```

## テスト

- **通常（モックのみ・認証不要）**
  ```bash
  uv run pytest tests/ -v
  ```
- **実呼び出しテスト（Vertex を本当に呼ぶ）**  
  認証を用意したうえで:
  ```bash
  set RUN_REAL_LLM_TESTS=1
  uv run pytest tests/ -v
  ```
  または実呼び出しだけ実行:
  ```bash
  uv run pytest tests/ -v -m real_llm
  ```
  認証が無い場合は `real_llm` マークのテストはスキップされる。

詳細は [tests/README_TDD.md](tests/README_TDD.md) を参照。
