# system_support_selfRegulatedLearning

LLM チューター（Vertex AI Gemini）と対話履歴の SQLite 永続化。

## セットアップ・実行

```powershell
uv sync
uv run flask --app framework_drivers.platform.main run
```

## 環境変数（Gemini Enterprise Agent Platform / 旧 Vertex AI）

- **GOOGLE_APPLICATION_CREDENTIALS** … サービスアカウント JSON のパス（未設定時は gcloud ADC を使用）
- **VERTEX_PROJECT_ID** … GCP プロジェクト ID（SA JSON の `project_id` と一致させる）
- **VERTEX_LOCATION** … リージョン（例: `asia-northeast1`）
- **VERTEX_MODEL_NAME** … 任意（未設定時は Gateway のデフォルトモデル）

GCP の API 有効化・課金・SA ロールは次で検証する:

```powershell
Get-Content .env.local | ForEach-Object { if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*)$') { Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2].Trim('"') } }
uv run python scripts/verify_gcp_agent_platform.py
```

## テスト

- **通常（モックのみ・認証不要）**
  ```powershell
  uv run pytest tests/ -v
  ```
- **実呼び出しテスト（Vertex を本当に呼ぶ）**  
  認証を用意したうえで:
  ```powershell
  $env:RUN_REAL_LLM_TESTS = "1"
  uv run pytest tests/ -v
  ```
  または実呼び出しだけ実行:
  ```powershell
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

```powershell
Get-Content .env.local | ForEach-Object { if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*)$') { Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2].Trim('"') } }
uv run python scripts/verify_gcp_agent_platform.py
```

### ローカルで Docker ビルド確認（任意）

```powershell
docker build -t sssrl-backend .
docker run -p 8080:8080 -e DB_REPLICA_DISABLED=1 sssrl-backend
curl.exe "http://localhost:8080/lecture?participant_id=1"
```

ローカルの `docker run` では GCS に接続しないため、`DB_REPLICA_DISABLED=1`（復元も複製もしない）が必要。指定しないと「複製先の設定がない」で起動が失敗する。なお、このビルドは SQLite のバージョン確認（修正済みの版でなければ失敗）を含み、この文書の作成時点で `docker build` は実行して確かめていない。

`secrets/` はイメージに含めない（実行時は Cloud Run の付属サービスアカウント + ADC で Vertex 認証）。

### デプロイ

```powershell
$PROJECT_ID = "your-gcp-project-id"
$REGION = "asia-northeast1"
$SERVICE_NAME = "sssrl-backend"
$REPLICA_BUCKET = "your-replica-bucket"   # 後述「GCS バケットの準備」で作るバケット名（gs:// なし）

gcloud config set project "${PROJECT_ID}"

gcloud run deploy "${SERVICE_NAME}" `
  --source . `
  --region "${REGION}" `
  --max-instances=1 `
  --min-instances=1 `
  --no-cpu-throttling `
  --allow-unauthenticated `
  --set-env-vars "VERTEX_PROJECT_ID=${PROJECT_ID},VERTEX_LOCATION=${REGION},DB_REPLICA_BUCKET=${REPLICA_BUCKET}" `
  --set-secrets "YOUTUBE_API_KEY=youtube-api-key:latest"
```

デプロイの条件（変えない）:

- リージョンは **`asia-northeast1`**（Cloud Run・GCS バケット・Vertex AI の `VERTEX_LOCATION` をすべて同じに揃える）。
- **`--max-instances=1`**: 複数のインスタンスが同じ複製先へ書くと、複製が壊れるか、片方の書き込みが失われる。
- **`--no-cpu-throttling`** と **`--min-instances=1`**: リクエストがない間も Litestream が複製を続け、インスタンスが落ちる機会を減らすため。
- **`DB_REPLICA_BUCKET` を必ず渡す**: 未設定または空のままコンテナを起動すると、起動を失敗させ、ログに「複製先の設定がない」と残す（永続化なしで稼働するのを防ぐため）。
- 上の例は永続化に関わる部分だけを示す。`SECRET_KEY` や `PARTICIPANT_CREDENTIALS_FILE` など、アプリが読む他の環境変数は、起動の手順（`deploy/entrypoint.sh`）が消さずにそのままアプリへ渡す。

Secret Manager に `youtube-api-key` が未整備の場合は、一時的に `--set-env-vars` で `YOUTUBE_API_KEY` を渡してもよい（本番では Secret Manager の利用を推奨）。

デプロイ完了後、表示されたサービス URL で疎通確認する:

```powershell
curl.exe "https://<service-url>/lecture?participant_id=1"
```

LAD API（YouTube API キー設定時）:

```powershell
curl.exe "https://<service-url>/api/participants/1/lad"
```

Google Apps Script（小テスト Form 等）から呼び出す場合は、スクリプトプロパティの **`API_BASE_URL`** にサービス URL（末尾スラッシュなし）を設定する。

### Cloud Run 環境変数

| 変数 | 必須 | 説明 |
|------|------|------|
| `VERTEX_PROJECT_ID` | AI 利用時 | GCP プロジェクト ID |
| `VERTEX_LOCATION` | AI 利用時 | リージョン（例: `asia-northeast1`） |
| `DB_REPLICA_BUCKET` | Cloud Run では必須 | 複製先の GCS バケット名（`gs://` を付けない名前だけ）。`learning.db` と `tutor.db` はこのバケットの中の別々の場所（`learning/`、`tutor/`）に複製される。未設定または空だとコンテナの起動が失敗する |
| `DB_REPLICA_DISABLED` | ローカル専用 | `1` のときだけ有効。復元も複製もせずにアプリを起動する（ログに「複製しない」と残る）。**Cloud Run では設定しない**（設定すると永続化なしで稼働する）。それ以外の値と未設定は「指定なし」 |
| `YOUTUBE_API_KEY` | LAD 利用時 | YouTube Data API キー |
| `SECRET_KEY` | 推奨 | Flask セッション用（未設定時は開発用デフォルト） |
| `TUTOR_DB_PATH` / `LEARNING_DB_PATH` | 任意 | 未設定時 `db/data/*.db` |
| `DEFAULT_LECTURE_ID` | 任意 | マップ外 `participant_id` のフォールバック講義 ID（既定 `lecture-1`） |
| `RESEARCHER_BASIC_AUTH_USER` | 研究用ダウンロード利用時 | 研究者の Basic 認証のユーザー名 |
| `RESEARCHER_BASIC_AUTH_PASSWORD` | 研究用ダウンロード利用時 | 研究者の Basic 認証のパスワード |

Cloud Run では `GOOGLE_APPLICATION_CREDENTIALS` は不要（実行サービスアカウントの ADC を使用）。

`RESEARCHER_BASIC_AUTH_USER` / `RESEARCHER_BASIC_AUTH_PASSWORD` は、**どちらかが未設定または空文字なら、研究用ダウンロードは常に 401 で拒否される**（設定の有無は外から区別できない）。パスワードは Secret Manager（`--set-secrets`）で渡すことを推奨する。

### 研究用の対話ログのダウンロード

仕様: [docs/spec/research-dialog-download.md](docs/spec/research-dialog-download.md)

研究者だけが、対話ログ(終了の保存の有無によらず、記録された発言 `messages` を元にした対話セッション)を JSON（対話セッションのリスト）で取得できる。

| 取得 | URL |
|------|-----|
| 参加者別 | `GET /research/participants/<participant_id>/dialog-logs` |
| 全参加者一括 | `GET /research/dialog-logs` |

- ブラウザ: URL を開くと資格情報の入力欄が出る。研究者のユーザー名・パスワードを入力する。
- curl.exe（`-u` で Basic 認証。PowerShell では `curl` が `Invoke-WebRequest` の別名になるため `curl.exe` を使う）:
  ```powershell
  curl.exe -u "<user>:<password>" "https://<service-url>/research/dialog-logs" -o dialog-logs.json
  curl.exe -u "<user>:<password>" "https://<service-url>/research/participants/1/dialog-logs"
  ```
- 対象データがなければ `[]`（状態 200）。応答は `Cache-Control: no-store`。

**注意（セキュリティ）**: 上記のデプロイは `--allow-unauthenticated` を前提としており、研究用ダウンロードを守るのは **この Basic 認証だけ**である。Cloud Run の IAM 認証を有効にすると、ブラウザからの Basic 認証による取得と両立しない。HTTP（ローカル起動）では資格情報は暗号化されない。資格情報は研究者で共有する1組のため、誰が取得したかは区別できず、取得の記録も残さない。

**既知の限界**: 取得できるのは、複製されて復元された範囲のデータである（再デプロイ・再起動の前のデータも、復元されていれば取得できる。許容損失は下記「SQLite 永続化の注意」を参照）。インスタンスは1つ（`--max-instances=1`）なので、要求を受けたインスタンスのデータだけが返る問題は、通常の構成では起きない。`/` を含む参加者ID、空の参加者IDは参加者別 URL で指定できない（一括には含まれる）。

### SQLite 永続化の注意

仕様: [docs/spec/db-persistence.md](docs/spec/db-persistence.md)

> **検証状況**（PO の実機確認、2026-10-26）:
>
> - **実機で確認済み**: `docker build`（Cloud Build で成功。AC20）、GCS バケットの準備手順（AC12）、インスタンスの入れ替え（方法A。AC10）、再デプロイ後にデータが残ること（AC9）、初回起動（AC14）、手元への復元（AC13）、停止時の終了順序（AC11 のうち、ログで観察した範囲）。デプロイ上の Vertex 実呼び出しも確認した（AC15-2）。
> - **未確認**: AC11 の「停止直前の書き込みが最終同期で複製される」ことは直接観察できておらず、PO が未検証（中）として受け入れた。AC8（往復の自動テスト）の Linux での実行。U9（30 日経過後の復元）。複数回の運用。手元の `real_llm` テスト（AC15-1）。
>
> 「未確認」と書いた箇所は、確認が済むまで鵜呑みにしないこと。

#### 方式

DB は SQLite の2ファイル（`db/data/learning.db` / `db/data/tutor.db`。パスは `LEARNING_DB_PATH` / `TUTOR_DB_PATH`）で、アプリのコードは変えていない。コンテナの起動の入口（`deploy/entrypoint.sh`）が [Litestream](https://litestream.io/)（v0.5.17 に固定）を使い、2つの DB を **GCS バケットへ継続して複製**し、起動のたびに **GCS から復元**する。

- 起動の順序: 設定の確認 → 2つの DB の復元（複製がなければ新規作成） → 2つの DB を WAL モードにする → Litestream の複製とアプリ（gunicorn）の起動。復元より前に DB へ書き込む処理は動かない。
- 複製先は DB ごとに別（バケット内の `learning/`、`tutor/`）。片方の復元はもう片方に影響しない。
- **復元に失敗したとき（権限不足、通信失敗など）は、空の DB で起動せず、起動を失敗させる**（原因はログに残る）。空の状態が新しい複製として上書きされ、データを失うのを防ぐため。
- **`DB_REPLICA_BUCKET` が未設定または空なら、起動を失敗させる**（「複製先の設定がない」とログに残る）。
- ローカルで複製なしに動かすときだけ、`DB_REPLICA_DISABLED=1` を指定する（復元も複製もせず起動する）。Cloud Run では使わない。`uv run flask --app framework_drivers.platform.main run` での通常のローカル起動は、この入口を通らないので、この指定は要らない。
- GCS への認証は、Cloud Run の実行サービスアカウントの ADC。鍵ファイルは使わない。
- 停止の通知（SIGTERM）を受けると、gunicorn の終了猶予は約4秒（`--graceful-timeout 4`）、Litestream の最終同期の待ちの上限は約5秒（`shutdown-sync-timeout`）で、Cloud Run の停止の猶予（約10秒）に収める設計。実機で観察した順序は、SIGTERM → gunicorn の終了 → `litestream shut down` で、通知から `litestream shut down` まで約0.5〜0.6秒（3回観察）であり、猶予（約10秒）に収まった。**最終同期の完了を示す専用のログ行は出ない**（`litestream shut down` が終端）。また、AC11 の「停止直前の書き込みが複製される」ことは直接観察できておらず、PO が未検証として受け入れた（数秒分の書き込みの窓が残りうる）。

#### 許容する損失

| 場面 | 失われうるデータ |
|---|---|
| 計画外の再起動・クラッシュ | 直近の数秒〜数十秒 |
| 計画された再デプロイ（下記の手順で行う） | ほぼゼロ |
| 再デプロイ・停止の時点で処理中だった AI 応答 | 打ち切られ、その往復は**保存されない**（協力者の画面にはエラーが出る） |

再デプロイでリビジョンが切り替わる間、新旧のインスタンスが一時的に並ぶ可能性があり、実機では新旧のインスタンスが約8秒（再デプロイ）と約23秒（入れ替え）並び、その間のデータの損失は観察されなかった。ただしこれは並ぶことの確認であり、損失が起きない保証ではない（仕様 U6）。このため、下記のとおり協力者が使っていない時間帯に行う。

#### GCS バケットの準備（初回のみ）

バケット名は変数で書く。リージョンは `asia-northeast1`。バケットの**保持ポリシー（retention policy、ロック）は設定しない**（Litestream の複製と干渉するおそれがあるため。ライフサイクルの削除は使う）。

```powershell
$PROJECT_ID = "your-gcp-project-id"
$REPLICA_BUCKET = "your-replica-bucket"
$RUN_SA = "<Cloud Run の実行サービスアカウントのメールアドレス>"

# 1. バケットを asia-northeast1 に作る
gcloud storage buckets create "gs://${REPLICA_BUCKET}" `
  --project "${PROJECT_ID}" --location asia-northeast1 --uniform-bucket-level-access

# 2. オブジェクトのバージョニングを有効にする
gcloud storage buckets update "gs://${REPLICA_BUCKET}" --versioning

# 3. ライフサイクル: 最新でない古い世代を 30 日後に削除する
# （BOM なしの UTF-8 で書くこと。PowerShell 5.1 と 7 のどちらでも動く書き方）
$json = @'
{"rule": [{"action": {"type": "Delete"}, "condition": {"daysSinceNoncurrentTime": 30}}]}
'@
[System.IO.File]::WriteAllText("$PWD\lifecycle.json", $json, (New-Object System.Text.UTF8Encoding($false)))
gcloud storage buckets update "gs://${REPLICA_BUCKET}" --lifecycle-file=lifecycle.json

# 4. 実行サービスアカウントに、このバケットだけの roles/storage.objectAdmin を付ける
gcloud storage buckets add-iam-policy-binding "gs://${REPLICA_BUCKET}" `
  --member "serviceAccount:${RUN_SA}" --role roles/storage.objectAdmin

# 5. 設定を確認する（location、versioning、lifecycle があり、retention policy がないこと）
gcloud storage buckets describe "gs://${REPLICA_BUCKET}"
```

- **`lifecycle.json` は BOM なしの UTF-8 で書くことが必須**（gcloud は BOM 付きの JSON を読めない可能性がある）。上の `[System.IO.File]::WriteAllText(...)` は Windows PowerShell 5.1 でも PowerShell 7 でも使える（`$PWD` で絶対パスにするのは、5.1 では .NET のカレントが PowerShell のカレントと異なる場合があるため）。Windows PowerShell 5.1 の `Set-Content -Encoding utf8` は BOM を付けるので使わない。別法として、**PowerShell 7 以降**でのみ `$json | Set-Content -Encoding utf8NoBOM lifecycle.json` も使える（5.1 では `utf8NoBOM` は使えない）。この手順は PowerShell で実行して動作を確認した（AC12）。
- 権限は**対象のバケットだけ**に付ける（プロジェクト全体には付けない）。Litestream が古い複製ファイルを自分で削除するため、削除の権限を含む `roles/storage.objectAdmin` が要る。
- ライフサイクルが消すのは「最新でない世代」だけで、最新の版は消さない。Litestream の複製ファイルがライフサイクルで消えず、30 日を超えた後も最新の状態を復元できるかは**未確認**（仕様 U9）。
- 上の `gcloud` のフラグ名と JSON の書式は、AC12 で実際に動作し、`describe` の結果で条件（location、versioning、lifecycle があり、retention policy がない）を満たすことを確かめた。

#### 計画された再デプロイの手順

1. **協力者が使っていない時間帯**に行う（リビジョン切り替えの重なりを避けるため）。
2. **直前に**、研究者ダウンロード（上記「研究用の対話ログのダウンロード」）で対話ログを取得して保存する（対話ログの手動バックアップ）。
3. 上記「デプロイ」の `gcloud run deploy`（同じフラグ）を実行する。
4. 再デプロイ後、研究者ダウンロードや LAD で、再デプロイ前のデータが残っていることを確かめる。

#### インスタンスの入れ替え手順（AC10: 再起動後もデータが残ることの確認）

目的は、「古いインスタンスが止まり、新しいインスタンスが GCS の複製から復元して起動しても、データが残る」ことを確かめること。**方法A は実機で動作した**（AC10: 新リビジョンが作られ、新インスタンスが GCS の複製から復元して起動し、入れ替え前の対話データが残った）。実行前に、協力者が使っていない時間帯であること、直前に研究者ダウンロードで対話ログを保存したことを確かめる。

1. 現在のリビジョンとインスタンスの状態を控える。

   ```powershell
   gcloud run services describe "${SERVICE_NAME}" --region asia-northeast1 `
     --format="value(status.latestReadyRevisionName)"
   ```

2. 次のどちらかでインスタンスを入れ替える。

   - **方法A（新リビジョンを作る。確実に新しいインスタンスが起動する）**: 環境変数のダミー値を変えて更新する。コードは変わらない。

     ```powershell
     gcloud run services update "${SERVICE_NAME}" --region asia-northeast1 `
       --update-env-vars "SWAP_MARKER=$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
     ```

     この方法は**新しいリビジョンが作られる**ため、AC10 の「新しいリビジョンを作らずに」とは厳密には異なる（リビジョン切り替えの重なりは、上記の U6 の対象）。新リビジョンを作らない入れ替えの確実な手段（例: 実行中のインスタンスだけを止める操作）は、公式の根拠を確認できていないため、ここでは断定しない。PO 決定（2026-10-26）により、リビジョンを変えない厳密な手段は追わず、この方法Aで AC10 を実施した（実機で動作を確認済み）。
   - **方法B（リビジョンを変えない。手段未確定。必要なら今後調べる）**: AC10 は方法Aで実施するため、現時点では手順を定めない。Cloud Run がインスタンスを自動で入れ替える（再起動する）機会を待つ場合は、ログでインスタンスの起動を確かめる。

3. 入れ替わったことを、Cloud Run のログ（Cloud Console の「ログ」、または `gcloud run services logs read`）で確かめる。新しいインスタンスの起動ログと、litestream の復元のログがあること。方法Aでは、`gcloud run services describe`（手順1のコマンド）で `latestReadyRevisionName` が変わり、トラフィックが新リビジョンに 100% 向いていること（`gcloud run services describe` の traffic の表示）も確かめる。
4. 入れ替え後、研究者ダウンロードや LAD で、入れ替え前のデータ（AC9 と同じ）が残っていることを確かめる。

#### 手元への復元手順（バックアップから任意の環境へ）

手元の PC に [Litestream v0.5.17](https://github.com/benbjohnson/litestream/releases/tag/v0.5.17) を入れ、GCS を読める認証（例: `gcloud auth application-default login`）をしたうえで、DB ごとに復元する。出力先に既存のファイルがあると上書きされない（**この挙動は未確認**。念のため）ので、空のディレクトリに出す。

```powershell
New-Item -ItemType Directory -Force restored
litestream restore -o restored/learning.db "gs://${REPLICA_BUCKET}/learning"
litestream restore -o restored/tutor.db    "gs://${REPLICA_BUCKET}/tutor"
```

復元した2ファイルは、`LEARNING_DB_PATH` / `TUTOR_DB_PATH` を向けるか、SQLite のツールで直接開いて読める。`litestream restore` の書式（`-o`、複製先の URL）は、AC13 で Windows 版 v0.5.17 により2つの DB とも動作した（ファイルが作られ、`integrity_check` が ok、データが読めた）。出力先に既存ファイルがあるときの挙動は未確認。

**Windows での注意（既知の制限）**: Windows 版 Litestream v0.5.16 以降では、`litestream restore` が復元後のディレクトリ同期で `Access is denied` となり、**終了コード 1** で終わることがある。データ自体は復元される。upstream の issue は [#1542](https://github.com/benbjohnson/litestream/issues/1542)（closed）、修正は [PR #1548](https://github.com/benbjohnson/litestream/pull/1548)（main にマージ済みだが、v0.5.17 のリリースには未反映）。AC13 の実機確認でも、Windows 版 v0.5.17 で `Access is denied`・終了コード 1 になったが、ファイルは作られ、integrity ok でデータが読めた。終了コードではなく、復元されたファイルの内容で判断すること。

**往復の自動テスト**（`tests/test_deploy/test_litestream_roundtrip.py`）は、Linux（Docker/CI や WSL2）で実行する。環境変数 `LITESTREAM_BIN` に Litestream のバイナリのパスを指定すると実行される。未指定のときは skip（実行不能）になり、**合格の証跡にはならない**。

#### スキーマの変更について

- **実験開始後は、DB のスキーマを変更しない**（NFR-12 / NFR-16）。スキーマの確定そのものは本節の範囲外で、各機能の完了条件とデプロイ前の確認で扱う。
- やむなく変える場合は、変更の前に次を行う。
  1. GCS の複製（バージョニングによる世代）と、研究者ダウンロードの対話ログの両方で、バックアップを取る。
  2. 復元した古い DB に、スキーマが「なければ作る」方式（`CREATE ... IF NOT EXISTS`）で適用されることを確かめる。この方式は既存の行を消さないが、既存の表の列は変えない。列の追加・変更は、「なければ作る」では反映されない。
  3. 協力者が使っていない時間帯に、上記の再デプロイの手順で行う。

#### 実験終了後の複製の扱い

2026年12月末の実験終了後に、GCS の複製（と古い世代）をどう扱うか（削除するか、保管するか）は、**研究室が倫理審査の条件（#38）を見て手動で判断する**。削除・保管の仕組みは用意していない。判断するまでは、バケットのライフサイクル（最新でない世代を 30 日後に削除）だけが働き、最新の複製は残り続ける。
