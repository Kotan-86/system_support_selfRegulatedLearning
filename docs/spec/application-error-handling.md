# アプリケーション層エラー処理（Result 型）

## 変更理由（Why）

- [application-usecase.md](./application-usecase.md) の各 Interactor は、成功時 `Response`・失敗時例外という表現になっている。実装では **Request → UseCase → Result** とし、失敗を型で明示する
- エラー検出と `AppError` の生成は **アプリケーション層のみ** で行う。ドメインからデータを取得し、Application で検証してから `ok` / `err` を返す
- `except Exception` は使わず、想定されるビジネス失敗だけを `Result` の `Err` として表現する

## スコープ（What）

| 含める | 含めない |
|--------|----------|
| Learning / Tutoring / Research Export UC の手順ごと `ok` / `err` 表 | `ExportResearchData` の出力形式（TSV / JSON 等）の詳細 |
| `AppError` / `Result` の配置方針 | `Result` / `AppError` の Python 実装詳細 |
| interfaces 層への HTTP 委譲の参照 | Infrastructure の障害ハンドリング |
| Tutoring 将来 UC（`Classify` / `Invoke`）の概要 | Port の Infrastructure 実装 |

## 関連仕様

- ユースケース手順: [application-usecase.md](./application-usecase.md)
- 不変条件の根拠: [domain-model.md](./domain-model.md)

---

## 共通契約

### フロー

```
Request  →  UseCase.execute()  →  Result[Response, AppError]
                                      ├─ Ok(Response)   … 成功
                                      └─ Err(AppError)  … 失敗
```

### 配置（目標）

```
application/
  common/
    result.py      # Ok, Err, Result
    errors.py      # ErrorCode, AppError 階層
  learning/
    dto/           # Request / Response
    use_cases/
  tutoring/
    dto/
    use_cases/
  research_export/
    dto/
    use_cases/
    ports/           # Read 専用 Export Query
```

### Interactor シグネチャ

| 項目 | 規約 |
|------|------|
| 入口 | `execute(self, request: XxxRequest) -> Result[XxxResponse, AppError]` |
| 成功 | `return ok(XxxResponse(...))` |
| 失敗 | `return err(AppError の具象)` |
| compose | 内部 UC の `Err` はそのまま `return err(error)` で伝播 |

### AppError と HTTP（interfaces 層）

`ErrorCode`・`AppError` クラス・HTTP ステータス・返却 UC の網羅的一覧は [エラーステータス一覧](#エラーステータス一覧) を参照する。interfaces 層は `AppError.code` から HTTP ステータスへ変換する。

### 検証の原則

- Port から取得したドメインデータ（`Lecture`, `LearningSession` 等）を材料に、**永続化・ドメイン操作の前** に Application で検証する
- 検証に通過した場合のみ `LearningSession.start` / `record_viewing_event` 等を呼ぶ
- `repository.save` は、直前の手順がすべて成功した場合にのみ実行する

---

## エラーステータス一覧

「エラーステータス」= アプリケーション層の **`ErrorCode`（機械可読）** + **`AppError` 具象クラス（型）**。HTTP ステータスは interfaces 層の変換結果であり、本一覧の副属性として記載する。

### NotFound 系（HTTP 404）

| ErrorCode | AppError クラス | 意味 | 返す UC |
|-----------|----------------|------|---------|
| `LECTURE_NOT_FOUND` | `LectureNotFoundError` | 講義カタログに `lecture_id` が無い | `RecordQuizAttempt`, `GetLearningSnapshot`, `SendChatMessage`, `ExportResearchData` |
| `LEARNING_SESSION_NOT_FOUND` | `LearningSessionNotFoundError` | `learning_session_id` 指定で Session が無い（Export の明示スコープのみ） | `ExportResearchData` |
| `TUTOR_SESSION_NOT_FOUND` | `TutorSessionNotFoundError` | 指定 `tutor_session_id` が無い | `SendChatMessage`（継続時） |

### Conflict 系（HTTP 409）

| ErrorCode | AppError クラス | 意味 | 返す UC |
|-----------|----------------|------|---------|
| `DUPLICATE_LEARNING_SESSION` | `ConflictError` | 同一 `(learner_id, lecture_id)` の Learning Session 重複 | `StartOrGetLearningSession` |
| `TUTOR_SESSION_POLICY_VIOLATION` | `ConflictError` | 同一 `learning_session_id` の TutorSession 2 本目（`NearTermExperimentPolicy` 違反） | `StartOrGetTutorSession` |

### Validation 系（HTTP 400）

`ValidationError` は共通基底。`ErrorCode` でサブ種別を区別する（[ValidationError の code 規約](#validationerror-の-code-規約) 参照）。

| ErrorCode | 意味 | 返す UC / 条件 |
|-----------|------|----------------|
| `VALIDATION_ERROR` | 汎用（VO 空文字、必須フィールド欠落など） | 全 UC の Request 検証（手順 0） |
| `INVALID_VIEWING_EVENT` | 視聴不変条件違反 | `RecordViewingEvent` |
| `UNKNOWN_QUESTION_INDEX` | 講義に存在しない `question_index` | `RecordQuizAttempt` |
| `INVALID_QUIZ_ATTEMPT` | 小テスト不変条件違反 | `RecordQuizAttempt` |
| `EMPTY_USER_MESSAGE` | `user_message` が空 | `SendChatMessage` |
| `EXPORT_DATA_INTEGRITY` | Export Read データの結合不整合 | `ExportResearchData` |
| `EXPORT_FILTER_REQUIRED` | フィルタ未指定（`learner_id` / `lecture_id` / `learning_session_id` がすべて `None`） | `ExportResearchData` |

### 外部依存障害（HTTP 502 等）

| ErrorCode | AppError クラス | 意味 | 返す UC |
|-----------|----------------|------|---------|
| `LLM_GATEWAY_ERROR` | `LlmGatewayError` | LLM 呼び出し失敗・空応答 | `SendChatMessage`（将来: `Classify` / `Invoke`） |

### AppError に含めないもの

| 種別 | 扱い |
|------|------|
| `repository.save` 等のインフラ障害 | `Err` にせず例外送出 → interfaces で 500（本仕様スコープ外） |
| ドメインの `ValueError` / `TypeError` | Application 層で捕捉し `ValidationError` に変換してから `err` を返す（UC 内で変換） |

### ValidationError の code 規約

| 使い分け | `ErrorCode` | 例 |
|----------|-------------|-----|
| 汎用入力不正 | `VALIDATION_ERROR` | `learner_id` 空文字、必須フィールド欠落、VO 不変条件違反 |
| ドメイン固有の検証失敗 | 上記 Validation 系サブコード | `INVALID_VIEWING_EVENT`, `UNKNOWN_QUESTION_INDEX` 等 |

- 各具象 `ValidationError` は `code` フィールドに対応する `ErrorCode` を固定する
- interfaces 層は `error_code`（`ErrorCode` 値）と `error`（`message`）の両方をクライアントへ返却する（interfaces 契約は別仕様）

### UC × ErrorCode マトリクス

各 UC が直接または compose 経由で返しうる `ErrorCode`。`-` は返さない。

| ErrorCode | StartOrGetLearningSession | RecordViewingEvent | RecordQuizAttempt | GetLearningSnapshot | StartOrGetTutorSession | SendChatMessage | ExportResearchData |
|-----------|:-------------------------:|:------------------:|:-----------------:|:-------------------:|:----------------------:|:---------------:|:------------------:|
| `VALIDATION_ERROR` | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| `DUPLICATE_LEARNING_SESSION` | ○ | ○¹ | ○¹ | - | - | ○¹ | - |
| `INVALID_VIEWING_EVENT` | - | ○ | - | - | - | - | - |
| `UNKNOWN_QUESTION_INDEX` | - | - | ○ | - | - | - | - |
| `INVALID_QUIZ_ATTEMPT` | - | - | ○ | - | - | - | - |
| `LECTURE_NOT_FOUND` | - | - | ○ | ○ | - | ○ | ○ |
| `TUTOR_SESSION_POLICY_VIOLATION` | - | - | - | - | ○ | ○² | - |
| `TUTOR_SESSION_NOT_FOUND` | - | - | - | - | - | ○ | - |
| `EMPTY_USER_MESSAGE` | - | - | - | - | - | ○ | - |
| `LLM_GATEWAY_ERROR` | - | - | - | - | - | ○ | - |
| `LEARNING_SESSION_NOT_FOUND` | - | - | - | - | - | - | ○ |
| `EXPORT_DATA_INTEGRITY` | - | - | - | - | - | - | ○ |
| `EXPORT_FILTER_REQUIRED` | - | - | - | - | - | - | ○ |

¹ `StartOrGetLearningSession` を compose した場合に伝播  
² `StartOrGetTutorSession` を compose した場合に伝播

### エラーにしない正常系

404 や 400 に変換せず、`Ok` として扱うケース。

| UC | 状況 | 扱い |
|----|------|------|
| `GetLearningSnapshot` | Learning Session 未作成 | `Ok`（空 Snapshot、`content_updated_at=None`） |
| `SendChatMessage` | Snapshot 取得結果が空（Learning Session 未作成） | 正常継続。空 Snapshot をプロンプト入力に使う |
| `SendChatMessage` | 初回メッセージが半角数字のみ | 正常継続。定型文を返し LLM を呼ばない |
| `ExportResearchData` | フィルタ指定済み（手順 0 通過）かつ `learning_session_id` 未指定で該当 Session 0 件 | `Ok`（空 Export DTO） |
| `ExportResearchData` | Learning Session はあるが TutorSession が無い | 正常。`messages` は空配列 |
| `ExportResearchData` | 視聴ログ・小テストが 0 件の Session | 正常。該当配列は空 |
| `ExportResearchData` | `learner_id` 指定で該当 Session 0 件（`learning_session_id` 未指定） | 正常。空の `Ok` |

---

## Learning UC: 手順ごとの `ok` / `err` 表

### StartOrGetLearningSession

**シグネチャ**: `execute(StartOrGetLearningSessionRequest) -> Result[StartOrGetLearningSessionResponse, AppError]`

| 手順 | 処理 | 成功時 | 失敗時（`err`） | 備考 |
|------|------|--------|-----------------|------|
| 0 | Request 検証: `learner_id`, `lecture_id` が空でない | 続行 | `ValidationError` | Shared Kernel 不変条件。DTO 構築前に interfaces で弾いてもよい |
| 1 | `existing = repository.find_by_learner_and_lecture(learner_id, lecture_id)` | 続行 | — | |
| 2 | `existing is not None` | **`ok(Response(..., outcome=RETRIEVED))`** で終了 | — | `save` は呼ばない |
| 3 | `existing_sessions = repository.list_by_learner(learner_id)` | 続行 | — | |
| 4 | `(learner_id, lecture_id)` の重複が `existing_sessions` に無いことを検証 | 続行 | `ConflictError`（`DUPLICATE_LEARNING_SESSION`） | 手順 2 をすり抜けた競合の防御 |
| 5 | `new_id = id_generator.next_id()` | 続行 | — | |
| 6 | `session = LearningSession.start(...)` | 続行 | — | 手順 4 通過後のみ呼ぶ |
| 7 | `repository.save(session)` | 続行 | — | インフラ障害は送出（`err` にしない） |
| 8 | — | **`ok(Response(..., outcome=CREATED))`** で終了 | — | |

**本 UC で返さないもの**: `LectureNotFoundError`（講義カタログ確認は行わない）

---

### RecordViewingEvent

**シグネチャ**: `execute(RecordViewingEventRequest) -> Result[RecordViewingEventResponse, AppError]`

| 手順 | 処理 | 成功時 | 失敗時（`err`） | 備考 |
|------|------|--------|-----------------|------|
| 0 | Request 検証: `learner_id`, `lecture_id` が空でない | 続行 | `ValidationError` | |
| 1 | 視聴不変条件検証（[domain-model.md#ViewingEvent](./domain-model.md)） | 続行 | `ValidationError`（`INVALID_VIEWING_EVENT`） | 下表「視聴検証」参照 |
| 2 | `session_result = start_or_get.execute(StartOrGetLearningSessionRequest(...))` | 続行 | 内部 UC の `Err` をそのまま伝播 | `Ok` のみ次へ |
| 3 | `event_id = viewing_event_id_generator.next_id()` | 続行 | — | |
| 4 | `updated = session.record_viewing_event(...)` | 続行 | — | 手順 1 通過後のみ呼ぶ |
| 5 | `repository.save(updated)` | 続行 | — | 手順 1〜4 成功後のみ |
| 6 | — | **`ok(RecordViewingEventResponse(...))`** で終了 | — | |

#### 視聴検証（手順 1 の詳細）

| 条件 | `err` |
|------|-------|
| `video_position < 0` | `ValidationError`（`INVALID_VIEWING_EVENT`） |
| `action` が `play` / `pause` かつ `position_delta != 0` | 同上 |
| `action` が `forward_skip` / `forward_seek` かつ `position_delta < 0` | 同上 |
| `action` が `backward_skip` / `backward_seek` かつ `position_delta > 0` | 同上 |

**受入基準との対応**: 不変条件違反時は手順 5 の `save` まで到達しない。

---

### RecordQuizAttempt

**シグネチャ**: `execute(RecordQuizAttemptRequest) -> Result[RecordQuizAttemptResponse, AppError]`

| 手順 | 処理 | 成功時 | 失敗時（`err`） | 備考 |
|------|------|--------|-----------------|------|
| 0 | Request 検証: `learner_id`, `lecture_id` が空でない | 続行 | `ValidationError` | |
| 1 | `lecture = lecture_catalog.find_by_id(request.lecture_id)` | 続行 | — | |
| 2 | `lecture is not None` | 続行 | **`err(LectureNotFoundError)`** で終了 | HTTP 404 |
| 3 | 各 `answer.question_index` が `lecture.quiz_definition` に存在 | 続行 | `ValidationError`（`UNKNOWN_QUESTION_INDEX`） | `Question.index` と照合 |
| 4 | 小テスト不変条件検証 | 続行 | `ValidationError`（`INVALID_QUIZ_ATTEMPT`） | 下表「小テスト検証」参照 |
| 5 | `session_result = start_or_get.execute(...)` | 続行 | 内部 UC の `Err` をそのまま伝播 | |
| 6 | `attempt_id = quiz_attempt_id_generator.next_id()` | 続行 | — | |
| 7 | `updated = session.record_quiz_attempt(...)` | 続行 | — | 手順 3〜4 通過後のみ |
| 8 | `repository.save(updated)` | 続行 | — | 手順 3〜7 成功後のみ |
| 9 | — | **`ok(RecordQuizAttemptResponse(...))`** で終了 | — | |

#### 小テスト検証（手順 4 の詳細）

| 条件 | `err` |
|------|-------|
| `score_denominator <= 0` | `ValidationError`（`INVALID_QUIZ_ATTEMPT`） |
| `score_numerator < 0` または `score_numerator > score_denominator` | 同上 |
| `answers` が 0 件 | 同上 |
| `answers` 内で `question_index` が重複 | 同上 |

---

### GetLearningSnapshot

**シグネチャ**: `execute(GetLearningSnapshotRequest) -> Result[GetLearningSnapshotResponse, AppError]`

| 手順 | 処理 | 成功時 | 失敗時（`err`） | 備考 |
|------|------|--------|-----------------|------|
| 0 | Request 検証: `learner_id`, `lecture_id` が空でない | 続行 | `ValidationError` | |
| 1 | `lecture = lecture_catalog.find_by_id(request.lecture_id)` | 続行 | — | |
| 2 | `lecture is not None` | 続行 | **`err(LectureNotFoundError)`** で終了 | HTTP 404 |
| 3 | `session = repository.find_by_learner_and_lecture(learner_id, lecture_id)` | 続行 | — | |
| 4 | `session is None` | **`ok(Response(snapshot=空, content_updated_at=None))`** で終了 | — | **正常系**。404 にしない |
| 5 | `snapshot = LearningSnapshotBuilder.build(session, lecture)` | 続行 | — | |
| 6 | `content_updated_at = max(視聴・小テストの最終時刻)` | 続行 | — | Session 内イベントから算出 |
| 7 | — | **`ok(GetLearningSnapshotResponse(...))`** で終了 | — | |

**本 UC で返す `err` は `LectureNotFoundError` のみ**（Session 未作成は `ok`）。

---

## Tutoring UC: 手順ごとの `ok` / `err` 表

Tutoring の Interactor は **Learning Entity を import しない**（[application-usecase.md](./application-usecase.md)）。Learning との連携は **Learning UC の compose** または **`LearningSnapshotQuery` Port**（実体は `GetLearningSnapshotUseCase`）経由とする。

### StartOrGetTutorSession

**シグネチャ**: `execute(StartOrGetTutorSessionRequest) -> Result[StartOrGetTutorSessionResponse, AppError]`

| 手順 | 処理 | 成功時 | 失敗時（`err`） | 備考 |
|------|------|--------|-----------------|------|
| 0 | Request 検証: `learning_session_id` が空でない | 続行 | `ValidationError` | Shared Kernel 不変条件 |
| 1 | `existing = repository.find_by_learning_session_id(learning_session_id)` | 続行 | — | |
| 2 | `existing is not None` | **`ok(Response(..., outcome=RETRIEVED))`** で終了 | — | `save` は呼ばない |
| 3 | `all_sessions = repository.list_all()` | 続行 | — | Policy 判定用 |
| 4 | `new_id = id_generator.next_id()` | 続行 | — | Policy 入力に必要 |
| 5 | `NearTermExperimentPolicy.can_start_tutor_session(existing_sessions=all_sessions, request=...)` | 続行 | `ConflictError`（`TUTOR_SESSION_POLICY_VIOLATION`） | 同一 `learning_session_id` の 2 本目を拒否 |
| 6 | 同一 `learning_session_id` が `all_sessions` に無いことを再確認 | 続行 | `ConflictError`（`TUTOR_SESSION_POLICY_VIOLATION`） | 手順 2 をすり抜けた競合の防御 |
| 7 | `session = TutorSession.start(...)` | 続行 | — | 手順 5〜6 通過後のみ |
| 8 | `repository.save(session)` | 続行 | — | 手順 5〜7 成功後のみ |
| 9 | — | **`ok(Response(..., outcome=CREATED))`** で終了 | — | |

**本 UC で返さないもの**: `LectureNotFoundError`, `TutorSessionNotFoundError`（`LearningSession` の作成は呼び出し元の責務）

**Policy 判定（手順 5）**: [domain-model.md#Domain Service（Tutoring）](./domain-model.md) の `NearTermExperimentPolicy`。Application は `can_start_tutor_session` の戻り値 `False` を `ConflictError` に変換する（`assert_*` は呼ばない）。

---

### SendChatMessage

**シグネチャ**: `execute(SendChatMessageRequest) -> Result[SendChatMessageResponse, AppError]`

| 手順 | 処理 | 成功時 | 失敗時（`err`） | 備考 |
|------|------|--------|-----------------|------|
| 0 | Request 検証（下表「Request 検証」） | 続行 | `ValidationError` | |
| 1 | **TutorSession 解決**（下表「TutorSession 解決」） | 続行 | 表参照 | `save` 前の失敗では永続化しない |
| 2 | Snapshot 取得: `GetLearningSnapshotUseCase` 相当（`LearningSnapshotQuery` 経由可） | 続行 | `Err` を伝播 | `LectureNotFoundError` 等。空 Snapshot は **正常系** |
| 3 | `lecture = lecture_catalog.find_by_id(lecture_id)` | 続行 | — | プロンプト組み立て用 |
| 4 | `lecture is not None` | 続行 | **`err(LectureNotFoundError)`** で終了 | HTTP 404 |
| 5 | **応答生成**（下表「応答生成」） | 続行 | `LlmGatewayError` 等 | 半角数字のみ特例は LLM 未呼び出しの **正常系** |
| 6 | `assistant_content` が空でないことを検証 | 続行 | `LlmGatewayError` | 定型文・LLM 応答のいずれも空なら失敗 |
| 7 | `user_msg_id`, `asst_msg_id = message_id_generator.next_id()` × 2 | 続行 | — | |
| 8 | `updated = tutor_session.append_message(user)` → `.append_message(assistant)` | 続行 | — | 手順 0・6 通過後のみ（`user_message` 非空保証） |
| 9 | `repository.save(updated)` | 続行 | — | 手順 1〜8 成功後のみ |
| 10 | — | **`ok(SendChatMessageResponse(...))`** で終了 | — | |

#### Request 検証（手順 0 の詳細）

| 条件 | `err` |
|------|-------|
| `user_message` が空文字 | `ValidationError`（`EMPTY_USER_MESSAGE`） |
| 初回（`tutor_session_id` 未指定）で `learner_id` または `lecture_id` が無い / 空 | `ValidationError` |
| 継続（`tutor_session_id` 指定）で `tutor_session_id` が無効 | 手順 1 で `TutorSessionNotFoundError` |
| Snapshot 取得に必要な `learner_id` / `lecture_id` が空（継続時も未指定の場合） | `ValidationError` |

#### TutorSession 解決（手順 1 の詳細）

| パターン | 処理 | 成功時 | 失敗時（`err`） |
|---------|------|--------|-----------------|
| **継続**（`tutor_session_id` あり） | `repository.find_by_id(tutor_session_id)` | `tutor_session` を得て続行 | `TutorSessionNotFoundError` |
| **初回**（`tutor_session_id` なし） | `start_or_get_learning.execute(...)` → `start_or_get_tutor.execute(learning_session_id=...)` | 両方 `Ok` なら `tutor_session` を得て続行 | 内部 UC の `Err` をそのまま伝播 |

内部 UC から伝播しうる例: `ValidationError`, `ConflictError`（Learning / Tutoring の Session 確保）

#### 応答生成（手順 5 の詳細）

| 条件 | 処理 | 結果 |
|------|------|------|
| `tutor_session.messages` が空 **かつ** `user_message` が `^[0-9]+$` | 定型文を `assistant_content` に設定。**LLM を呼ばない** | 続行（正常系） |
| 上記以外 | `prompt = chat_prompt_builder.build(snapshot, messages, user_message, lecture)` → `llm_gateway.generate(prompt)` | 成功 → 続行 / 失敗 → **`err(LlmGatewayError)`** |

**手順 5 の失敗時**: `repository.save` は呼ばれない（user / assistant Message は未永続化）。

#### Snapshot 取得（手順 2 の補足）

`LearningSnapshotQuery` の実体が `GetLearningSnapshotUseCase` の場合、戻り値は `Result[GetLearningSnapshotResponse, AppError]` とする。`Ok` 時は `response.snapshot` を手順 5 へ渡す。Learning Session 未作成でも `Ok`（空 Snapshot）であり、`SendChatMessage` はエラーにしない。

---

### SendChatMessage（将来拡張: Classify → Invoke）

近い実験の手順 5（`LlmGateway` 直呼び出し）を、将来は次の compose に差し替える。**手順 0〜4・7〜10 の `ok` / `err` 表は変えない**。

| 手順 | 処理 | 成功時 | 失敗時（`err`） |
|------|------|--------|-----------------|
| 5a | `ClassifyInterpretationSupportType.execute(...)` | 続行 | `LlmGatewayError` 等（分類 Port 失敗時） |
| 5b | `InvokeTutoringAgent.execute(support_type, ...)` | `assistant_content` を得て続行 | `LlmGatewayError` 等 |

---

## Research Export UC: 手順ごとの `ok` / `err` 表

Research Export は **Read 専用**（[application-usecase.md#Research Export UC 一覧](./application-usecase.md)）。`repository.save` は呼ばない。Learning / Tutoring の **Read Port** からデータを取得し、Export 用 DTO を組み立てる。

### ExportResearchData

**シグネチャ**: `execute(ExportResearchDataRequest) -> Result[ExportResearchDataResponse, AppError]`

#### 入出力（本仕様で固定する範囲）

**Request**（フィルタはすべて任意。複数指定時は AND）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `learner_id` | `LearnerId \| None` | 参加者で絞り込み |
| `lecture_id` | `LectureId \| None` | 講義で絞り込み |
| `learning_session_id` | `LearningSessionId \| None` | 1 Session 単位で絞り込み |

**Response**（3 種別を 1 DTO にまとめる）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `rows` | `tuple[ResearchExportRow, ...]` | 結合キー `(learner_id, learning_session_id, lecture_id)` ごとの 1 行 |
| `viewing_event_count` | `int` | 出力に含まれる視聴イベント総数 |
| `quiz_attempt_count` | `int` | 出力に含まれる小テスト受験総数 |
| `message_count` | `int` | 出力に含まれる対話メッセージ総数 |

`ResearchExportRow` は行ごとに `viewing_events` / `quiz_attempts` / `messages` を保持する（出力形式へのシリアライズは interfaces 層）。

#### 依存 Port（Read 専用）

| Port | 責務 |
|------|------|
| `LearningSessionExportQuery` | 条件に合う `LearningSession` と配下の `ViewingEvent` / `QuizAttempt` を Read |
| `TutorSessionExportQuery` | `learning_session_id` 群に紐づく `TutorSession` と `Message[]` を Read |
| `LectureCatalog` | 行に `lecture_id` を付与・設問メタデータ解決（Learning と同一契約） |

Tutoring / Learning の **Write Repository は注入しない**。

#### 手順 `execute`

| 手順 | 処理 | 成功時 | 失敗時（`err`） | 備考 |
|------|------|--------|-----------------|------|
| 0 | Request 検証（下表「Request 検証」） | 続行 | `ValidationError` | |
| 1 | `lecture_id` 指定時: `lecture_catalog.find_by_id(lecture_id)` | 続行 | — | |
| 2 | `lecture_id` 指定かつ `lecture is None` | — | **`err(LectureNotFoundError)`** で終了 | HTTP 404 |
| 3 | `learning_sessions = learning_export_query.list_filtered(learner_id, lecture_id, learning_session_id)` | 続行 | — | |
| 4 | `learning_session_id` 指定かつ `learning_sessions` が空 | — | **`err(LearningSessionNotFoundError)`** で終了 | 明示スコープの 404 |
| 5 | `learning_session_id` 未指定かつ結果 0 件 | **`ok(Response(rows=(), counts=0))`** で終了 | — | **正常系**（該当データなし）。手順 0 通過済み（いずれかの ID が指定されている）場合に限る |
| 6 | `tutor_sessions = tutor_export_query.list_by_learning_session_ids(...)` | 続行 | — | Learning 結果の ID 群で取得 |
| 7 | 結合整合性検証（下表「結合検証」） | 続行 | `ValidationError`（`EXPORT_DATA_INTEGRITY`） | Read データの不整合 |
| 8 | 各行を `ResearchExportRow` に組み立て（`lecture_id` は Session から取得） | 続行 | — | TutorSession 無し行は `messages=()` |
| 9 | — | **`ok(ExportResearchDataResponse(...))`** で終了 | — | |

#### Request 検証（手順 0 の詳細）

| 条件 | `err` |
|------|-------|
| 指定された `learner_id` / `lecture_id` / `learning_session_id` が空文字（VO 不変条件違反） | `ValidationError` |
| フィルタ未指定（すべて `None`） | `ValidationError`（`EXPORT_FILTER_REQUIRED`）。メッセージ例: 「`learner_id`、`lecture_id`、`learning_session_id` のいずれかを指定してください」 |

#### 結合検証（手順 7 の詳細）

| 条件 | `err` |
|------|-------|
| `TutorSession.learning_session_id` が、手順 3 の Learning 結果に存在しない | `ValidationError`（`EXPORT_DATA_INTEGRITY`） |
| 同一 `learning_session_id` に `TutorSession` が 2 本以上 | `ValidationError`（`EXPORT_DATA_INTEGRITY`） |

**エラーにしないもの**:

| 状況 | 扱い |
|------|------|
| Learning Session はあるが TutorSession が無い | 正常。`messages` は空 |
| 視聴ログ・小テストが 0 件の Session | 正常。該当配列は空 |
| `learner_id` 指定で該当 Session 0 件（`learning_session_id` 未指定） | 正常。空の `Ok` |

#### 本 UC で返さないもの

| AppError | 理由 |
|----------|------|
| `TutorSessionNotFoundError` | Export は TutorSession を **ID 指定で引かない**。無ければ空配列 |
| `LlmGatewayError` | LLM を呼ばない |
| `ConflictError` | 書き込みを行わない |

---

## compose 時の `Err` 伝播

| 呼び出し元 UC | 内部 UC / Port | 伝播する `AppError` の例 |
|--------------|----------------|-------------------------|
| `RecordViewingEvent` | `StartOrGetLearningSession` | `ValidationError`, `ConflictError` |
| `RecordQuizAttempt` | `StartOrGetLearningSession` | 同上 |
| `SendChatMessage`（初回） | `StartOrGetLearningSession` | `ValidationError`, `ConflictError` |
| `SendChatMessage`（初回） | `StartOrGetTutorSession` | `ValidationError`, `ConflictError`（`TUTOR_SESSION_POLICY_VIOLATION`） |
| `SendChatMessage` | `GetLearningSnapshot`（`LearningSnapshotQuery`） | `LectureNotFoundError`, `ValidationError` |

内部 UC が `Ok` を返した場合のみ、呼び出し元の後続手順（ID 生成・追記・`save`）に進む。

---

## 受入基準（本仕様）

- [ ] Learning 4 UC すべての `execute` が `Result[..., AppError]` を返す
- [ ] Tutoring 2 UC（`StartOrGetTutorSession`, `SendChatMessage`）の `execute` が `Result[..., AppError]` を返す
- [ ] `ExportResearchData` の `execute` が `Result[..., AppError]` を返し、**Write Port を呼ばない**
- [ ] `ExportResearchData` でフィルタ指定ありのデータ 0 件・TutorSession 未作成を正常系（`Ok`）として扱う
- [ ] `ExportResearchData` でフィルタ未指定時に `EXPORT_FILTER_REQUIRED`（HTTP 400）を返す
- [ ] 上表の失敗手順で `repository.save` が呼ばれない（Write 系 UC の新規作成・追記）
- [ ] `GetLearningSnapshot` / `SendChatMessage` で Learning Session 未作成時に空 Snapshot を正常系として扱う
- [ ] `SendChatMessage` で LLM 失敗時に Message が永続化されない
- [ ] Tutoring コードが `domain.learning.learning_session` 等を import しない
- [ ] `except Exception` によるビジネスエラー捕捉を行わない
