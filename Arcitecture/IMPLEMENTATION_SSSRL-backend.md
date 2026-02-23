# SSSRL バックエンド実装手順（ステップバイステップ）

本資料は [ADR_SSSRL-backend_2026-02-23.md](ADR_SSSRL-backend_2026-02-23.md) に基づき、**何をどの順で実装するか**と**なぜその実装にするか**を説明する。各ステップで「なぜ」を明示し、ADR の決定と対応づける。

---

## 前提と全体の流れ

- **参照元は DB のみ**とする（Spreadsheet は読まない）。LAD と LLM が参照するデータはすべて自 app の DB に格納する。
- **DB は 2 本**：対話用（`tutor.db`）と学習データ用（`learningLog.db`）。責務を分け、LAD 用クエリで対話用 DB を開かないようにする（ADR §1）。
- **参加者 id（participant_id）**を全データの共通識別子とし、スキーマ・API で統一する（ADR §2）。

実装の流れは次の 4 フェーズに分ける。

1. **データ基盤**：DB の分離、スキーマ、パス設定
2. **学習データ用 API**：quiz / viewing-log の受信、LAD 用取得、最終更新時刻
3. **対話・LLM 統合**：セッションに participant_id、chat で学習データをプロンプトに含める
4. **GAS 連携**：Form・動画側から API を呼ぶ（実装は GAS 側が主となるため要点のみ）

---

## Phase 1: データ基盤の分離とスキーマ

### Step 1.1 対話用 DB と学習データ用 DB のファイルを分ける

**やること**

- 対話履歴用の SQLite ファイルを **1 本**に保ち、名前を **`db/data/tutor.db`** とする（既存の `db/data/tutor.db` があればそのまま利用）。
- 学習データ用に **別ファイル** を用意し、**`db/data/learningLog.db`** とする。視聴ログ・小テスト結果はここにだけ書き込む。

**なぜこの実装か**

- ADR では「学習データは LAD の表示に使われ、LAD 用クエリでは対話データは不要」としている。対話用と学習用で **接続先を分ける**ことで、LAD 用のコードが対話用 DB を開かず、誤って触るリスクを減らせる。
- 実験開始後は **学習データのスキーマを変更しない** 方針のため、学習データを独立した 1 ファイルにしておくと、マイグレーション・バックアップの対象が「実験条件に直結するデータ」に限定され、対話用 DB の変更と切り離して扱える。

---

### Step 1.2 対話用 DB のスキーマに participant_id を追加する

**やること**

- **sessions** に **`participant_id` (TEXT, NOT NULL)** を追加する。既存の `id`, `created_at` はそのまま。
- セッション作成時（POST /chat で session_id が無いとき）に、**participant_id を必須で受け取り**、sessions に保存する。
- 既存の `db/schema.sql` が対話用のみを定義している場合は、sessions の定義に `participant_id` を追加し、マイグレーションまたは初期化で反映する。

**なぜこの実装か**

- ADR では「sessions に participant_id 列を必ず持たせる」としている。**ログイン機能を将来入れるとき**、一つのアプリで多数の参加者を扱う際に、サーバが「ログイン済みユーザ id = participant_id」をセッションに保存する形にしておくと、ログイン設計と整合する。
- POST /chat では、**session_id からセッションを引いてその participant_id で学習データを取得**する。リクエストで participant_id を毎回渡す方式は採用しないため、DB に持っておく必要がある。

---

### Step 1.3 学習データ用 DB のスキーマを作成する

**やること**

- **learning.db** 用のスキーマを定義する（例: `db/schema_learning.sql` または `db/learningLog_schema.sql`）。
- **viewing_logs**：`id`, `participant_id`, `time_stamp`, `current_time`, `action`, `duration`。動画が複数ある場合は `video_id` を追加する。
- **quiz_attempts**：`id`, `participant_id`, `created_at`, `score_numerator`, `score_denominator`。
- **quiz_attempt_answers**：`id`, `attempt_id`, `question_index`, `selected_answer`, **`is_correct`**。SQLite では BOOLEAN を **INTEGER の 0/1** で保存する（CHECK で 0/1 に制限してもよい）。

**なぜこの実装か**

- **viewing_logs** は「1 イベント = 1 行」で、participant_id と time_stamp で誰の・いつのイベントかが分かる。LAD や LLM は「ある participant_id の最新 N 件」を時系列で取得する想定。
- **quiz_attempts** で「1 回の受験」を 1 行にし、**score_numerator / score_denominator** でスコアを数値で持つ。ADR で「など」をやめこの 2 列に固定しているため、集計・表示が一貫する。
- **quiz_attempt_answers** で各問の選択回答と **is_correct（BOOLEAN）** を保存する。ADR で「各問の正誤は GAS の FormApp で取得し API 経由で DB に保存する」としているため、app 側は正答キーを持たず、GAS から渡された正誤をそのまま保存すればよい。SQLite に BOOLEAN 型はないため、INTEGER 0/1 で保存する。

---

### Step 1.4 DB パスを環境変数で切り替え可能にする

**やること**

- 対話用 DB のパスを **`TUTOR_DB_PATH`**、学習データ用 DB のパスを **`LEARNING-LOG_DB_PATH`** で指定できるようにする。
- 未設定時は **`db/data/tutor.db`** と **`db/data/learningLog.db`** をデフォルトとする。ファイル名で何の DB か分かるようにする（ADR で決定済み）。

**なぜこの実装か**

- テスト時や本番で別ディレクトリを指したい場合に、コードを変えずに環境変数だけで切り替えられる。デフォルトを「名前で分かる」ファイル名にしておくことで、どのファイルが対話用・学習用かが一目で分かる。

---

## Phase 2: 学習データ用 API

### Step 2.1 POST /api/quiz-attempts を実装する

**やること**

- リクエスト body を **JSON** で受け取る。必須項目の例：`participant_id`, `timestamp`（または `created_at`）, `score_numerator`, `score_denominator`, `answers`（各問の `question_index`, `selected_answer`, `is_correct`）。
- **学習データ用 DB（learning.db）のみ**に、quiz_attempts に 1 行、quiz_attempt_answers に各問 1 行ずつ INSERT する。
- 認証は **必須にしない**。ADR で「誰でも認証なしでログイン情報（participant_id）だけで使えるようにする」としている。

**なぜこの実装か**

- GAS は **UrlFetchApp** で HTTP POST し、body に JSON を載せて送る。一次ソースは DB であり、CSV は出力しないため、データは API に JSON で渡すだけでよい。
- 正誤は **GAS の FormApp** で取得し、payload に含めて送る。app 側で正答キーと照合する必要はない（Grid 等のフォールバックが必要な場合を除く）。
- **学習データ用 DB のみ**に書くことで、LAD 用の参照はこの DB だけを読めばよく、対話用 DB と責務が分かれる。

---

### Step 2.2 POST /api/viewing-log または /api/viewing-logs を実装する

**やること**

- **1 件用**: `POST /api/viewing-log` で body に `participant_id`, `time_stamp`, `current_time`, `action`, `duration` を受け取り、viewing_logs に 1 行 INSERT する。
- **一括用**（任意）: `POST /api/viewing-logs` で body に配列で複数件受け取り、学習データ用 DB にまとめて INSERT する。
- どちらか、または両方を用意する。呼び出し元は GAS（動画視聴）。GAS は Spreadsheet に書き込まない。

**なぜこの実装か**

- 視聴イベントは「再生」「シーク」など都度発生する。1 件ずつ送るか、一定数まとめて送るかは GAS の実装と相談だが、API は「1 件」または「複数件」のどちらか（または両方）を受理できる形にすればよい。一次ソースは DB であり、GAS は API に送るのみとする（ADR：Spreadsheet 廃止）。

---

### Step 2.3 GET /api/last-updated を実装する

**やること**

- 学習データ用 DB の **視聴ログ・小テスト** の「最終更新時刻」を返す。例：`viewing_logs` と `quiz_attempts` の `created_at`（または `updated_at` があればそれ）の **max** を取り、JSON で返す。
- フロントは、LAD 表示のロード時や一定間隔でこの API を呼び、「前回知っている時刻」より新しければ「データ更新あり」と表示し、LAD 用データを再取得する。

**なぜこの実装か**

- ADR では「学習直後に LAD に反映させる」ことを重視している。手動アップロードは廃止し、**学習データ用 DB が更新されたら、フロントがその「時刻」を知って再取得する**形にすることで、リアルタイムに近い体験を実現する。

---

### Step 2.4 GET /api/participants/{participant_id}/lad を実装する

**やること**

- パスは **`GET /api/participants/{participant_id}/lad`** とする。名前を読んで「参加者の LAD 用データ」と分かるようにする（ADR で決定済み）。
- **学習データ用 DB のみ**を参照し、その participant_id の **最新の** 視聴ログ・小テスト結果（直近 1 試行など）を返す。対話用 DB は読まない。

**なぜこの実装か**

- LAD が表示するのは「この参加者の視聴ログと小テスト結果」だけである。対話履歴は不要なので、**学習データ用 DB だけを開く**。ADR で「LAD 用にクエリをかけるときに、対話用 DB を開く必要がない」としているため、この API は learning.db のみを参照する。

---

## Phase 3: 対話・LLM との統合

### Step 3.1 セッション作成時に participant_id を渡し、sessions に保存する

**やること**

- セッションを新規作成するとき（例: POST /chat で session_id が無いとき）、リクエストから **participant_id** を必須で受け取る。
- **sessions** に INSERT する際に、`id`, `created_at` に加えて **participant_id** を保存する。既存の対話用 DB の repository（create_session）のシグネチャを、`participant_id` を受け取る形に変更する。

**なぜこの実装か**

- ADR で「sessions に participant_id 列を必ず持たせる」とし、**ログイン機能に合わせる**形にしている。現状はログインがなくても、フロントが participant_id を渡してセッションを作成し、DB に持っておく。将来ログインを入れたときは、サーバがログイン済みユーザの id を participant_id としてセッションに保存するだけでよい。

---

### Step 3.2 POST /chat でセッションの participant_id から学習データを取得し、プロンプトに含める

**やること**

- POST /chat では、**session_id** でセッションを取得し、その **participant_id** を読む。リクエストで participant_id を毎回送る必要はない。
- **学習データ用 DB** から、その participant_id の **最新の** 視聴ログ・小テスト結果（および各問の正誤）を取得する。
- 既存のプロンプト組み立て（SYSTEM_PROMPT の `lecture_log`, `quiz_result` など）に、取得した学習データを埋め込んで LLM に渡す。対話履歴は **対話用 DB** から従来どおり取得する。

**なぜこの実装か**

- ADR では「セッションの participant_id を使って、学習データ用 DB からその参加者の最新の視聴ログ・小テストを取得しプロンプトに含める」としている。**session に participant_id を持たせている**ので、chat 時には session_id から participant_id を引けばよく、クライアントが毎回 participant_id を送る必要がない。
- 参照元は **学習データ用 DB のみ**。Spreadsheet は読まない。

---

## Phase 4: GAS 連携（要点）

### Step 4.1 GAS から自 app の API を呼ぶ

**やること**

- **小テスト**: Form の「フォーム送信時」トリガーで GAS を実行する。FormApp で `getGradableResponseForItem` と `getScore()` / `getPoints()` により各問の正誤を判定し、**UrlFetchApp** で `POST /api/quiz-attempts` に **JSON** を送る。Content-Type は `application/json`、payload は `JSON.stringify(...)` する。
- **視聴ログ**: 動画視聴側の GAS で、イベント発生時に UrlFetchApp で `POST /api/viewing-log`（または `/api/viewing-logs`）に JSON を送る。
- **Spreadsheet には書き込まない**。データは API に送るのみ（ADR：Spreadsheet 廃止）。CSV は出力しない。

**なぜこの実装か**

- 一次ソースは自 app の DB とするため、GAS は「データを API に送る」役割だけ持つ。Spreadsheet に二重に書くと、参照元が曖昧になり、リアルタイム性も保ちにくい。ADR で「GAS は Spreadsheet に書き込まない」と明示している。
- データは **JSON** で送る。CSV を GAS で生成して Drive に置く方式は採用しない。正誤は FormApp で取得し、API の payload に含める（[ADR_Quiz_GAS_Grading.md](ADR_Quiz_GAS_Grading.md) に従う）。

---

### Step 4.2 認証について

**やること**

- API の認証は **必須にしない**。利用者は participant_id の入力（および将来のログイン）で識別し、誰でも認証なしで使えるようにする。
- 公開 URL で運用する場合は、GAS から API を叩く際に **API キーやトークンをヘッダに付ける**ことを **推奨** とするが、必須にはしない（ADR：安全性とのバランス）。

**なぜこの実装か**

- ADR で「みんなが認証なしでログイン情報だけで使えるようにしたい」とし、「認証は必須としない」としている。そのうえで、公開環境では同一システムであることを示す手段を「推奨」として残し、必須にしないことで実装コストと利便性のバランスを取る。

---

## 実装順序の目安

| 順序 | 内容 | 依存 |
|------|------|------|
| 1 | 学習データ用 DB のスキーマ定義と初期化（learning.db） | なし |
| 2 | 対話用 DB のスキーマ更新（sessions に participant_id）とマイグレーション | 既存 tutor.db |
| 3 | DB パスを環境変数で切り替え（TUTOR_DB_PATH, LEARNING_DB_PATH） | 1, 2 |
| 4 | POST /api/quiz-attempts, POST /api/viewing-log(s) の実装 | 1, 3 |
| 5 | GET /api/last-updated, GET /api/participants/{participant_id}/lad の実装 | 1, 3 |
| 6 | セッション作成時の participant_id 受け取り・保存（create_session の変更） | 2, 3 |
| 7 | POST /chat で session の participant_id から学習データ取得・プロンプトに含める | 4, 5, 6 |
| 8 | GAS 側で Form 送信トリガー・視聴イベントから API を呼ぶ（UrlFetchApp, JSON） | 4 |

---
