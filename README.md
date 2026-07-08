# system_support_selfRegulatedLearning

LLM チューター（Vertex AI Gemini）と対話履歴の SQLite 永続化。

## セットアップ・実行

```bash
uv sync
uv run flask --app framework_drivers.platform.main run
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

## Cloud Run デプロイ

仕様: [docs/spec/framework-drivers-layer.md](docs/spec/framework-drivers-layer.md#デプロイ運用what)

### 前提

- `gcloud` にログイン済みで、デプロイ先 GCP プロジェクトを選択済みであること
- Cloud Run の実行サービスアカウントに **`roles/aiplatform.user`**（Vertex AI / Gemini Enterprise Agent Platform）が付与されていること
- LAD（学習行動ダッシュボード）表示には **YouTube Data API キー**（`YOUTUBE_API_KEY`）が必要

GCP の API 有効化・課金・SA ロールは、デプロイ前にローカルで次を実行して確認できる:

```bash
set -a && source .env.local && set +a
uv run python scripts/verify_gcp_agent_platform.py
```

### ローカルで Docker ビルド確認（任意）

```bash
docker build -t sssrl-backend .
docker run -p 8080:8080 sssrl-backend
curl "http://localhost:8080/lecture?participant_id=1"
```

`secrets/` はイメージに含めない（実行時は Cloud Run の付属サービスアカウント + ADC で Vertex 認証）。

### デプロイ

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-east4
export SERVICE_NAME=sssrl-backend

gcloud config set project "${PROJECT_ID}"

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars "VERTEX_PROJECT_ID=${PROJECT_ID},VERTEX_LOCATION=${REGION}" \
  --set-secrets "YOUTUBE_API_KEY=youtube-api-key:latest"
```

Secret Manager に `youtube-api-key` が未整備の場合は、一時的に `--set-env-vars` で `YOUTUBE_API_KEY` を渡してもよい（本番では Secret Manager の利用を推奨）。

デプロイ完了後、表示されたサービス URL で疎通確認する:

```bash
curl "https://<service-url>/lecture?participant_id=1"
```

LAD API（YouTube API キー設定時）:

```bash
curl "https://<service-url>/api/participants/1/lad"
```

Google Apps Script（小テスト Form 等）から呼び出す場合は、スクリプトプロパティの **`API_BASE_URL`** にサービス URL（末尾スラッシュなし）を設定する。

### Cloud Run 環境変数

| 変数 | 必須 | 説明 |
|------|------|------|
| `VERTEX_PROJECT_ID` | AI 利用時 | GCP プロジェクト ID |
| `VERTEX_LOCATION` | AI 利用時 | リージョン（例: `us-east4`） |
| `YOUTUBE_API_KEY` | LAD 利用時 | YouTube Data API キー |
| `SECRET_KEY` | 推奨 | Flask セッション用（未設定時は開発用デフォルト） |
| `TUTOR_DB_PATH` / `LEARNING_DB_PATH` | 任意 | 未設定時 `db/data/*.db` |
| `DEFAULT_LECTURE_ID` | 任意 | マップ外 `participant_id` のフォールバック講義 ID（既定 `lecture-1`） |

Cloud Run では `GOOGLE_APPLICATION_CREDENTIALS` は不要（実行サービスアカウントの ADC を使用）。

### SQLite 永続化の注意

初回デプロイでは **コンテナ内の SQLite**（`db/data/tutor.db` / `db/data/learning.db`）を使用する。Cloud Run のファイルシステムはエフェメラルなため、**再デプロイやインスタンス再起動で対話履歴・学習データは消える**。

本番でデータを保持するには、Cloud SQL や GCS ボリューム等による永続化が必要（現時点の Dockerfile / デプロイ手順のスコープ外）。運用前に `tutor.db` / `learning.db` のバックアップ方針を決めること。
