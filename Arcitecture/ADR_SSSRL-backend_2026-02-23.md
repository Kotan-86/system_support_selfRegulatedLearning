# 【ADR】 SSSRL バックエンド（学習振り返り支援システム）

**ADR_SSSRL-backend_2026-02-23**（2026-02-23）

## Status

**承認（accepted）**

- 提案中（proposed）: まだ承認されておらず、議論・レビュー中の状態
- 承認（accepted）: 承認され、現在有効な決定
- 却下（rejected）: 提案されたが採用されなかった決定
- 廃止/非推奨（deprecated/superseded）: 以前は有効だったが、後に新たな決定に置き換えられた決定

## Context

本システムは、自学習環境で**学習分析ダッシュボード（LAD）**と**LLM チューター**を用いて学習者の振り返りを支援する。LAD は視聴ログ・小テスト結果を可視化し、LLM チューターはそれらに基づいて対話で振り返りを促す。

- **データの種類**: (1) **視聴ログ**（動画の再生・シーク等のイベント）、(2) **小テスト結果**（参加者 id・スコア・各問の回答と正誤）、(3) **対話履歴**（LLM とのやり取り）。これらを**参加者 id** で紐づけ、実験では「誰の・どの試行の・どのデータか」を一意に扱う必要がある。
- **入力の現状**: 小テストは **Google Form**、視聴ログは **Google Apps Script（GAS）** 付きの動画ページで収集され、これまで Spreadsheet に記録されていた。手動アップロードや更新遅延を避け、**学習直後に** LAD と LLM に反映させたい。
- **制約**: 実験開始後は**学習データのスキーマを変更しない**（条件の一貫性のため）。LAD 用のクエリでは視聴ログ・小テストだけを参照し、対話データは不要である。

そこで、**入力は Google のままにしつつ、参照用の一次ソースを自アプリの DB に置く**構成とし、かつ**対話用 DB と学習データ用 DB を分ける**ことを決める。

## Decision

**バックエンドは次のようにする。(1) 入力は Google Form と GAS（講義動画プラットフォーム）のまま、送信・イベント時に GAS から自アプリの API を呼び、受け取ったデータを自アプリの DB に保存する。(2) 参照はすべて自アプリの DB のみとし、Spreadsheet は読まない。(3) DB は 2 つに分ける：対話履歴用（LLM チューターの会話）と学習データ用（LAD 表示・LLM プロンプト用の視聴ログ・小テスト）。参加者 id（participant_id）を全データの共通識別子とする。**

### 1. DB を 2 つに分ける理由

- **学習データ**（視聴ログ・小テスト）は **LAD の表示専用**でもあり、LAD 用の API が叩くのはこのデータだけである。対話履歴（sessions, messages）は不要である。
- **実験開始後は学習スキーマを変更しない**方針のため、学習データは独立した DB にしておくと、マイグレーション・バックアップの対象が「実験条件に直結するデータ」に限定され、対話用 DB を誤って触るリスクを避けられる。
- **LAD 用にクエリをかけるときに、対話用 DB を開く必要がない**。接続・バックアップ・権限の範囲を「対話」と「学習」で分けられる。

したがって、**対話用 SQLite 1 ファイル** と **学習データ用 SQLite 1 ファイル** の 2 本とする。

### 2. 参加者 id（participant_id）の扱い

- **定義**: 学習者を一意に識別する値。Google Form の「idを入力してください」および視聴ログの `participant_id` と同一とする。実験では参加者に事前に id を付与し、動画視聴・小テスト・LLM チューター利用の際に同じ id を入力してもらう。
- **役割**:
  - **小テスト**: 1 試行 = participant_id + 送信日時（または attempt_id）。同一 participant_id の複数試行を「再受験」として保存する。
  - **視聴ログ**: 1 イベント = participant_id + time_stamp + action 等。同一 participant_id の複数イベントを時系列で保持する。
  - **対話**: セッションを participant_id と紐づける。**sessions に participant_id 列を必ず持たせる**。将来的に LLM チューターや LAD にログイン機能を付ける場合、一つのアプリで多数の参加者を扱う際、サーバがログイン済みユーザの id（= participant_id）を把握し、セッション作成時に sessions.participant_id に保存する形にしておくと、ログイン設計と整合する。LLM のプロンプトには、そのセッションの participant_id に紐づく最新の小テスト・視聴ログを載せる。
- スキーマと API のパラメータ名は **participant_id** で統一する。

### 3. データの流れ（全体）

```
[学習者]
    │
    ├─ 動画視聴 (GAS + HTML)
    │       └─ 視聴イベント発生 ──► GAS ──► POST /api/viewing-log(s) ──► 自 app ──► 学習データ用 DB (viewing_logs)
    │
    ├─ 小テスト (Google Form)
    │       └─ 送信 ──► GAS（FormApp で各問の正誤を取得）──► POST /api/quiz-attempts ──► 自 app ──► 学習データ用 DB (quiz_attempts, quiz_attempt_answers)
    │
    └─ 振り返り
            ├─ LAD 表示   ◄── 自 app ◄── 学習データ用 DB のみ参照
            └─ LLM チューター ◄── 自 app ◄── 対話用 DB（履歴）＋ 学習データ用 DB（最新の視聴ログ・小テスト）
```

- **入力側**: GAS に「送信時／イベント時に自 app の API を呼ぶ」処理を追加する。**GAS は Spreadsheet に書き込まない。** データは API に送るのみ。自 app が参照するのは DB のみとする。
- **小テストの各問正誤**: Google Form を「クイズ」にしている場合、GAS の FormApp で `response.getGradableResponseForItem(question)` と `getScore()` / 設問の `getPoints()` により正誤を判定できる（Multiple Choice / Dropdown / Checkbox が対象）。正誤を API の payload（JSON）に含めて自 app に送り、学習データ用 DB に保存する。**GAS で CSV は出力しない**。データは API に JSON で渡すだけで十分であり、一次ソースは DB なので CSV は不要とする。
- **参照側**: LAD は学習データ用 DB のみから取得。LLM は対話用 DB から履歴、学習データ用 DB からその participant_id の最新の視聴ログ・小テストを取得してプロンプトに載せる。

### 4. コンポーネントと責務

| コンポーネント | 責務 |
|----------------|------|
| **Google Form** | 小テストの入力 UI。参加者が id・各問の回答を送信する。設問は Multiple Choice / Dropdown / Checkbox にすると、GAS から各問の正誤を取得できる。 |
| **GAS（フォーム送信トリガー）** | Form 送信時に、FormApp で各問の正誤を取得し、自 app の `POST /api/quiz-attempts` に JSON で participant_id・タイムスタンプ・回答・正誤を送る。Spreadsheet には書き込まない。CSV は出力しない。 |
| **GAS（動画視聴）** | 視聴イベント（play, seek 等）を検知し、自 app の `POST /api/viewing-log`（または一括 `POST /api/viewing-logs`）に participant_id・time_stamp・current_time・action・duration を送る。Spreadsheet には書き込まない。 |
| **自 app（Flask）** | API で受け取った小テスト・視聴ログを**学習データ用 DB** に保存。対話は**対話用 DB** に保存。LAD 用の取得は学習データ用 DB のみ。LLM 用は対話用 DB（履歴）と学習データ用 DB（その参加者の最新学習データ）を参照。最終更新時刻を返す API を提供する。 |
| **対話用 DB（SQLite）** | 対話履歴のみ。sessions, messages。LLM のプロンプト組み立て時に直近 N ターンを取得する。ファイル名は名前で用途が分かるようにする（例: tutor.db）。 |
| **学習データ用 DB（SQLite）** | 視聴ログ・小テスト結果のみ。viewing_logs, quiz_attempts, quiz_attempt_answers。LAD と LLM の「学習データ」参照はここだけを使う。実験開始後はスキーマを変更しない。ファイル名は名前で用途が分かるようにする（例: learning.db）。 |

### 5. スキーマ

#### 5.1 対話用 DB（`tutor.db`）

- **sessions**: 1 対話セッション = 1 行。  
  - `id` (TEXT, PK), `created_at` (DATETIME), **`participant_id` (TEXT, NOT NULL)**。どの参加者のセッションかを必ず持つ（ログイン機能導入時に、ログイン済みユーザ id をここに保存する想定）。
- **messages**: 各発言（user / assistant）。  
  - `id` (INTEGER, PK), `session_id` (TEXT, FK), `role` (TEXT), `content` (TEXT), `created_at` (DATETIME).  
  - 履歴取得用に `(session_id, created_at)` のインデックスを張る。

#### 5.2 学習データ用 DB（`learning.db`）

- **viewing_logs**: 視聴イベント 1 件 = 1 行。  
  - `id` (INTEGER, PK), `participant_id` (TEXT), `time_stamp` (DATETIME), `current_time` (INTEGER, 秒), `action` (TEXT), `duration` (REAL). 動画が複数ある場合は `video_id` (TEXT) を追加する。
- **quiz_attempts**: 小テスト 1 回の受験 = 1 行。  
  - `id` (INTEGER, PK), `participant_id` (TEXT), `created_at` (DATETIME), `score_numerator` (INTEGER), `score_denominator` (INTEGER).
- **quiz_attempt_answers**: 1 問 = 1 行。  
  - `id` (INTEGER, PK), `attempt_id` (INTEGER, FK), `question_index` (INTEGER), `selected_answer` (TEXT), **`is_correct` (BOOLEAN)**。SQLite では BOOLEAN は INTEGER の 0/1 で保存する。

**パス**: 環境変数 `TUTOR_DB_PATH` / `LEARNING_DB_PATH` で上書き可能。**デフォルトは `db/data/tutor.db`（対話用）と `db/data/learning.db`（学習データ用）。**

### 6. API の役割（概要）

| エンドポイント | 役割 | 呼び出し元 |
|---------------|------|-------------|
| POST /api/quiz-attempts | 小テスト 1 試行（participant_id・回答・各問正誤）を受け取り、学習データ用 DB に保存する。 | GAS（フォーム送信トリガー） |
| POST /api/viewing-log または /api/viewing-logs | 視聴ログ 1 件または複数件を受け取り、学習データ用 DB に保存する。 | GAS（動画視聴） |
| GET /api/last-updated | 学習データ（視聴ログ・小テスト）の最終更新時刻を返す。学習データ用 DB の max(updated_at) 等。 | フロント（LAD の「更新あり」判定） |
| GET /api/participants/{participant_id}/lad | 指定した participant_id の最新の視聴ログ・小テスト結果を返す。学習データ用 DB のみ参照。 | フロント（LAD 表示） |
| POST /chat | メッセージと session_id を受け取り、対話用 DB に保存し LLM で応答。セッションの participant_id を使って、学習データ用 DB からその参加者の最新の視聴ログ・小テストを取得しプロンプトに含める。 | フロント（LLM チューター） |

- **認証**: **認証は必須としない。** 利用者は participant_id の入力（および将来のログイン機能）で識別し、誰でも認証なしで利用できるようにする。公開 URL で運用する場合は、同一システムであることを示す API キーやトークンの利用を**推奨**するが、必須にはしない。

### 7. データ構造の参照

- **小テスト（API 受信）**: タイムスタンプ、スコア、participant_id、各問の選択回答・正誤。Form の列順と question_index を対応させる（例: 列4 → question_index 1）。
- **視聴ログ（API 受信）**: timeStamp, participant_id, currentTime, action, duration。そのまま viewing_logs に写す。

## Consequences

### メリット

- **リアルタイム性**: Form 送信・視聴イベント発生と同時に学習データ用 DB に書き込むため、LAD と LLM が直近のデータを参照できる。手動アップロードは不要。
- **参加者・試行の一貫性**: participant_id を共通にし、試行・時系列で管理できる。実験の分析や個人ごとの検証がしやすい。
- **責務の分離**: LAD 用クエリは学習データ用 DB のみを開く。対話用 DB を誤って触るリスクを減らせる。実験開始後は学習データ用 DB のスキーマを固定する、という運用がしやすい。
- **バックアップ・マイグレーション**: 対話と学習でファイルが分かれているため、対象範囲が明確になる。

### 受け入れるべき負債・リスク

- **GAS の保守**: Form の設問変更・視聴ログの項目変更時に、GAS の送信 payload と学習データ用 DB のスキーマを一致させる必要がある。
- **参加者 id の入力品質**: participant_id は学習者が入力する前提のため、誤入力・未入力の扱いを運用で決める必要がある。
- **2 ファイルの運用**: バックアップ・デプロイ時に対話用と学習データ用の 2 ファイルを扱う必要がある。接続先を環境変数で明示する。

## Compliance

- **参照元**: LAD と LLM が参照する視聴ログ・小テスト結果は、**学習データ用 DB のみ**から取得する。対話履歴は**対話用 DB のみ**から取得する。Spreadsheet は参照しない。
- **入力経路**: 小テストは Form → GAS → 自 app API → 学習データ用 DB。視聴ログは GAS → 自 app API → 学習データ用 DB。**GAS は Spreadsheet に書き込まない。** GAS は送信時／イベント時に API を呼ぶことを必須とする。
- **参加者 id**: 小テスト・視聴ログ・対話で **同一の participant_id** を用い、スキーマと API のパラメータ名を `participant_id` で統一する。
- **正誤**: 小テストの各問正誤は GAS の FormApp で取得し、API（JSON）経由で学習データ用 DB に保存する。GAS で CSV は出力しない。
- **学習データ用 DB のスキーマ**: 実験開始後は変更しない。変更が必要な場合は実験条件の見直しとして扱う。
