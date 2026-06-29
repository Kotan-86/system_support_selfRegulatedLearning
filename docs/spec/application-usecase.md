# アプリケーション層ユースケース

## 変更理由（Why）

- [domain-model.md](./domain-model.md) で Entity / 集約 / Domain Service を定義した。次に **アプリケーション層が担う手順（ユースケース）** を仕様化し、Interactor 実装と TDD の契約とする
- 現行 Flask ルート（`app/main.py`）と Repository（`db/`）に散在するオーケストレーションを、**Use Case + Port** に集約する
- 各ユースケース仕様は **コードに翻訳できる自然言語** とし、Request / Response / Port / `execute` 手順 / 受入基準を 1 見出しセットで記述する

## スコープ

### 本仕様に含める

| 要素 | 説明 |
|------|------|
| Learning コンテキストの Use Case | Session 確保・視聴記録・小テスト記録・**LAD と AI 共通の学習コンテキスト Read** |
| Port（インターフェース契約） | Repository / Catalog / Query / IdGenerator |
| Interactor 共通規約 | 命名・依存方向・層の責務分界 |

### 本仕様に含めない（別仕様・別 PR）

- Port の Infrastructure 実装（SQLite Mapper、外部 API Adapter）
- Flask ルート・Presenter・LLM 呼び出し（interfaces 層）。`GET /api/last-updated` は interfaces 層が `GetLearningSnapshot` の `content_updated_at` を返す薄い Adapter とする
- Tutoring / Research Export の Use Case 詳細（末尾に一覧のみ記載）
- DB スキーマ変更

## 関連仕様

- ドメインモデル: [domain-model.md](./domain-model.md)
- ドメイン層実装計画: [domain-implementation-plan.md](./domain-implementation-plan.md)
- アプリケーション層エラー処理（Result 型）: [application-error-handling.md](./application-error-handling.md)
- 学習データ永続化（子 Entity ID 方針）: [framework-drivers-persistence.md](./framework-drivers-persistence.md)

---

## 共通規約

### ディレクトリ構成（目標）

```
application/
  learning/
    ports/           # Protocol（Port 契約）
    dto/             # Request / Response（frozen dataclass）
    use_cases/       # Interactor
  tutoring/
    ports/
    dto/
    use_cases/
tests/
  test_application/
    test_learning/
    test_tutoring/
```

### Interactor

| 項目 | 規約 |
|------|------|
| クラス名 | `{UseCaseId}UseCase`（例: `StartOrGetLearningSessionUseCase`） |
| 入口 | `execute(self, request: XxxRequest) -> Result[XxxResponse, AppError]`（[application-error-handling.md](./application-error-handling.md)） |
| 依存 | コンストラクタ注入（Port / 他 Use Case） |
| import 禁止 | `flask`, `sqlite3`, `vertexai` |
| ドメイン | `domain/` の Entity / Domain Service を呼んでよい |
| Tutoring 境界 | Tutoring の Interactor は `domain.learning.learning_session` 等の Entity を import しない |

### DTO

- `@dataclass(frozen=True)` とする
- ID 型は Shared Kernel（`LearnerId`, `LectureId` 等）をそのまま使う
- Start-or-Get UC の結果種別は `StartOrGetOutcome`（`StrEnum`: `CREATED` / `RETRIEVED`）を Response の `outcome` フィールドに載せる
- HTTP / JSON のフィールド名変換（`participant_id` → `learner_id`）は **interfaces 層** が行う

### 例外（AppError / Result）

ユースケースの失敗は `Result` の `Err(AppError)` として返す（[application-error-handling.md](./application-error-handling.md)）。interfaces 層が HTTP ステータスへ変換する。

| AppError | ErrorCode | 意味 | HTTP（interfaces） |
|----------|-----------|------|-------------------|
| `LectureNotFoundError` | `LECTURE_NOT_FOUND` | 講義カタログに `lecture_id` が無い | 404 |
| `LearningSessionNotFoundError` | `LEARNING_SESSION_NOT_FOUND` | 指定 `learning_session_id` の Session が無い | 404 |
| `TutorSessionNotFoundError` | `TUTOR_SESSION_NOT_FOUND` | 指定 `tutor_session_id` が無い | 404 |
| `ConflictError` | `DUPLICATE_LEARNING_SESSION` | 同一 `(learner_id, lecture_id)` の Learning Session 重複 | 409 |
| `ConflictError` | `TUTOR_SESSION_POLICY_VIOLATION` | 同一 `learning_session_id` の TutorSession 2 本目 | 409 |
| `ValidationError` | （サブコード各種） | 入力・不変条件違反 | 400 |
| `LlmGatewayError` | `LLM_GATEWAY_ERROR` | LLM 呼び出し失敗 | 502 等 |

**エラーにしない正常系**（`Ok` として扱う）: `GetLearningSnapshot` の Session 未作成 → 空 Snapshot（HTTP 200）。詳細は [application-error-handling.md#エラーにしない正常系](./application-error-handling.md#エラーにしない正常系)。

全 ErrorCode と UC マトリクス: [application-error-handling.md#エラーステータス一覧](./application-error-handling.md#エラーステータス一覧)

### テスト

- `tests/test_application/` に Interactor 単体テストを置く
- Port は Fake / InMemory 実装で注入する（DB 不要）
- 各 Use Case の **受入基準** セクションを executable spec とする

### 講義動画と Lecture の関係

| 概念 | 責務 | 備考 |
|------|------|------|
| 動画再生 | 講義動画プラットフォーム（GAS + YouTube IFrame API） | バックエンドは動画バイナリを保持しない |
| `Lecture`（ドメイン） | 講義**メタデータ**（title, videoUrl, srtPath, quizDefinition） | 動画 URL は参照用。実体は YouTube |
| `LectureCatalog`（Port） | `lectureId` から `Lecture` メタデータを解決 | 実装は設定ファイル / DB / 外部 API のいずれか |

**Session 確保・視聴記録**では `LectureCatalog` は不要。**小テスト記録・LAD・AI プロンプト**で必要。

---

## Port 一覧（Learning コンテキスト）

### `LearningSessionRepository`

| メソッド | 入力 | 出力 | 備考 |
|---------|------|------|------|
| `find_by_learner_and_lecture` | `LearnerId`, `LectureId` | `LearningSession \| None` | |
| `list_by_learner` | `LearnerId` | `tuple[LearningSession, ...]` | Session 開始時の重複チェック用 |
| `save` | `LearningSession` | `LearningSession` | 集約全体を永続化（upsert）し、**DB 確定後の集約**を返す（下記 [save 戻り値と子 Entity ID の確定](#learningsessionrepositorysave-戻り値と子-entity-id-の確定)） |

#### `LearningSessionRepository.save` 戻り値と子 Entity ID の確定

##### 変更理由（Why）

- [framework-drivers-persistence.md#決定事項](./framework-drivers-persistence.md#決定事項) では、`ViewingEventId` / `QuizAttemptId` は SQLite の INTEGER `AUTOINCREMENT` 行を INSERT した **後** に `str(lastrowid)` で確定する
- 現行の Use Case 手順は `ViewingEventIdGenerator` / `QuizAttemptIdGenerator` で **save 前** に ID を付与し、その値を API Response に載せている — SQLite Adapter の ID 方針と不整合になる
- `POST /api/viewing-log` / `POST /api/quiz-attempts` の Response に返す `event_id` / `attempt_id` は、**永続化後の DB 上の ID と一致** しなければならない

##### 仕様（What）

| 項目 | 内容 |
|------|------|
| `save` 戻り値 | **`LearningSession`** — Adapter が永続化を完了した時点の集約（子 Entity ID を含む） |
| `RecordViewingEvent` の `event_id` | **`save` 戻り値**の集約から、当該 `execute` で追記した `ViewingEvent` の ID を取得して Response に載せる |
| `RecordQuizAttempt` の `attempt_id` | **`save` 戻り値**の集約から、当該 `execute` で追記した `QuizAttempt` の ID を取得して Response に載せる |
| 子 ID の同定 | 当該 `execute` は子 Entity を **1 件のみ** 追記する。追記後の `viewing_events` / `quiz_attempts` の **末尾 1 件** を今回追記分とみなす |
| `ViewingEventIdGenerator` / `QuizAttemptIdGenerator` | Port 契約は維持する。**SQLite 本番配線では Use Case に注入しない**（[framework-drivers-persistence.md#ID 生成（Mapper / Repository）](./framework-drivers-persistence.md#id-生成mapper--repository)）。Fake / InMemory 単体テストでは従来どおり Generator を差し替えてよい |

##### 受入基準

- [ ] `LearningSessionRepository.save` の戻り値型が `LearningSession` である
- [ ] `RecordViewingEvent` / `RecordQuizAttempt` が Response の子 ID を **Generator の戻り値ではなく `save` 戻り値の集約** から取得する
- [ ] SQLite 配線で `ViewingEventIdGenerator` / `QuizAttemptIdGenerator` が Use Case に注入されない
- [ ] Fake / InMemory テストは Generator 差し替え可能なまま維持できる

### `LectureCatalog`

| メソッド | 入力 | 出力 | 備考 |
|---------|------|------|------|
| `find_by_id` | `LectureId` | `Lecture \| None` | メタデータ参照。動画本体は返さない |

### `LearningSessionIdGenerator`

| メソッド | 入力 | 出力 |
|---------|------|------|
| `next_id` | なし | `LearningSessionId` |

### `ViewingEventIdGenerator`

| メソッド | 入力 | 出力 |
|---------|------|------|
| `next_id` | なし | `ViewingEventId` |

**配線**: SQLite 本番 Adapter では Use Case に **注入しない**（ID は `save` 戻り値で確定）。Fake / InMemory テスト用。

### `QuizAttemptIdGenerator`

| メソッド | 入力 | 出力 |
|---------|------|------|
| `next_id` | なし | `QuizAttemptId` |

**配線**: SQLite 本番 Adapter では Use Case に **注入しない**（ID は `save` 戻り値で確定）。Fake / InMemory テスト用。

### `LearningSnapshotQuery`（Tutoring → Learning ACL）

| メソッド | 入力 | 出力 | 備考 |
|---------|------|------|------|
| `get_by_learner_and_lecture` | `LearnerId`, `LectureId` | `LearningSnapshot` | 実体は `GetLearningSnapshotUseCase` と同一 Read 契約 |

Tutoring は Learning Entity を import せず、この Port 経由で **LAD と同じ `LearningSnapshot`** を参照する。

更新時刻の軽量取得用 Port（`LearningDataChangeCursorQuery` 等）は **Application 層に設けない**。`GetLearningSnapshotResponse.content_updated_at` を用いる。

---

## ユースケース一覧

| 優先 | ID | コンテキスト | 公開 / 内部 | 既存 API 対応 |
|------|-----|-------------|------------|--------------|
| 1 | `StartOrGetLearningSession` | Learning | 内部（compose 可） | — |
| 2 | `RecordViewingEvent` | Learning | 公開 | `POST /api/viewing-log` |
| 3 | `RecordQuizAttempt` | Learning | 公開 | `POST /api/quiz-attempts` |
| 4 | `GetLearningSnapshot` | Learning | 公開 | `GET /api/participants/{id}/lad`、Tutoring（ACL 経由）、`GET /api/last-updated`（interfaces 層 Adapter） |
| — | `StartOrGetTutorSession` | Tutoring | 内部（compose 可） | `POST /chat`（初回） |
| — | `SendChatMessage` | Tutoring | 公開 | `POST /chat` |
| — | `ExportResearchData` | Research Export | 公開 | 未実装（視聴ログ + 小テスト + 対話ログ） |

---

## StartOrGetLearningSession

### 変更理由（Why）

- 1 学習者 × 1 講義につき `LearningSession` は 1 本（[domain-model.md#LearningSession](./domain-model.md)）
- `RecordViewingEvent` / `RecordQuizAttempt` 等が共通で「Session を確保してから追記」するため、手順を 1 ユースケースに集約する

### 仕様

| 項目 | 値 |
|------|-----|
| ID | `StartOrGetLearningSession` |
| コンテキスト | Learning |
| アクター | 学習者（`learnerId` はログイン等で確定済み） |
| トリガー | 学習記録ユースケースの内部から呼ばれる（単体 API として公開してもよい） |
| Interactor | `StartOrGetLearningSessionUseCase` |

### 前提条件

- `learnerId` は空でない（Shared Kernel 不変条件）
- `lectureId` は空でない
- **`Lecture` メタデータの存在確認は行わない**（`lectureId` は Session への参照キーとして受理する）

### 本ユースケースが行わないこと

- ログイン / 認証
- 講義選択 UI
- 動画の取得・再生（講義動画プラットフォームの責務）
- `ViewingEvent` / `QuizAttempt` の追記

### 入力 `StartOrGetLearningSessionRequest`

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `learner_id` | `LearnerId` | yes | |
| `lecture_id` | `LectureId` | yes | |
| `started_at` | `datetime` | yes | 新規 start 時に `LearningSession.started_at` へ設定。get 時は未使用 |

### 出力 `StartOrGetLearningSessionResponse`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `session_id` | `LearningSessionId` | |
| `session` | `LearningSession` | 呼び出し元が追記処理を続けるため、集約を返す |
| `outcome` | `StartOrGetOutcome` | `CREATED` = 新規 start、`RETRIEVED` = 既存 get |

### 依存 Port

- `LearningSessionRepository`
- `LearningSessionIdGenerator`

### 手順 `execute`

1. `existing = repository.find_by_learner_and_lecture(request.learner_id, request.lecture_id)`
2. `existing is not None` なら `Response(session_id=existing.id, session=existing, outcome=RETRIEVED)` を return
3. `new_id = id_generator.next_id()`
4. `session = LearningSession.start(id=new_id, learner_id=request.learner_id, lecture_id=request.lecture_id, started_at=request.started_at, existing_sessions=repository.list_by_learner(request.learner_id))`
5. `persisted = repository.save(session)`
6. `Response(session_id=persisted.id, session=persisted, outcome=CREATED)` を return

### 例外

[application-error-handling.md#StartOrGetLearningSession](./application-error-handling.md#startorgetlearningsession)

| 条件 | AppError | ErrorCode |
|------|----------|-----------|
| 同一 `(learnerId, lectureId)` が既に存在（競合） | `ConflictError` | `DUPLICATE_LEARNING_SESSION` |

### 受入基準

- [ ] 未作成の `(learnerId, lectureId)` → `outcome=CREATED` で 1 件 `save` される
- [ ] 既存 Session がある → `outcome=RETRIEVED`、`save` は呼ばれない
- [ ] 同一 `(learnerId, lectureId)` で 2 回呼び出し → 2 回目は get（Session は 1 本）
- [ ] 異なる `lectureId` なら同一 `learnerId` で複数 Session を持てる

---

## RecordViewingEvent

### 変更理由（Why）

- 動画操作 1 回を `LearningSession` 集約に追記する。追記された視聴ログは、小テスト結果・字幕抜粋等とともに `GetLearningSnapshot` 経由で LAD / AI に渡る **共有学習コンテキストの構成要素の一つ** となる
- 既存 `POST /api/viewing-log` のドメイン駆動版

### 仕様

| 項目 | 値 |
|------|-----|
| ID | `RecordViewingEvent` |
| コンテキスト | Learning |
| アクター | 学習者（講義動画プラットフォーム経由） |
| トリガー | 動画操作 1 回（play / pause / skip / seek） |
| Interactor | `RecordViewingEventUseCase` |

### 前提条件

- `learnerId`, `lectureId` が確定している
- `action` は `ViewingAction` のいずれか
- `action` と `position_delta` は [domain-model.md#ViewingEvent](./domain-model.md) の不変条件を満たす

### 入力 `RecordViewingEventRequest`

| フィールド | 型 | 必須 | 既存 API フィールド |
|-----------|-----|------|-------------------|
| `learner_id` | `LearnerId` | yes | `participant_id` |
| `lecture_id` | `LectureId` | yes | （未導入。近い実験では固定値可） |
| `occurred_at` | `datetime` | yes | `time_stamp` |
| `video_position` | `int` | yes | `current_time`（ingress で小数切り捨て） |
| `action` | `ViewingAction` | yes | `action` |
| `position_delta` | `int` | yes | `duration`（ingress で小数切り捨て） |

**ingress 正規化**: interfaces 層（現状は `POST /api/viewing-log`）は `application.common.viewing_seconds` で `current_time` / `duration` を整数秒へ変換する。小数は Python `int()` と同様に 0 方向へ切り捨てる。`NaN` / `Infinity` / 非数値文字列は `ValidationError`。

### 出力 `RecordViewingEventResponse`

| フィールド | 型 |
|-----------|-----|
| `event_id` | `ViewingEventId` |
| `session_id` | `LearningSessionId` |

### 依存

- `StartOrGetLearningSessionUseCase`（compose）
- `LearningSessionRepository`

（`ViewingEventIdGenerator` は SQLite 本番配線では注入しない。[save 戻り値と子 Entity ID の確定](#learningsessionrepositorysave-戻り値と子-entity-id-の確定) 参照）

### 手順 `execute`

1. `session_response = start_or_get.execute(StartOrGetLearningSessionRequest(learner_id=..., lecture_id=..., started_at=request.occurred_at))`
2. `updated = session_response.session.record_viewing_event(...)`（当該 UC 内で 1 件追記）
3. `persisted = repository.save(updated)`
4. `event_id = persisted.viewing_events` の **末尾 1 件**の ID
5. `Response(event_id=event_id, session_id=persisted.id)` を return

### 例外

[application-error-handling.md#RecordViewingEvent](./application-error-handling.md#recordviewingevent)

| 条件 | AppError | ErrorCode |
|------|----------|-----------|
| `play` / `pause` で `position_delta != 0` | `ValidationError` | `INVALID_VIEWING_EVENT` |
| skip / seek で符号が action と不一致 | `ValidationError` | `INVALID_VIEWING_EVENT` |

### 受入基準

- [ ] 初回イベント → Session も新規作成される（`StartOrGet` 経由）
- [ ] 2 件目以降 → 同一 Session に追記、`viewing_events` が 1 件増える
- [ ] 不変条件違反 → `err(ValidationError)` を返し、`repository.save` は呼ばれない
- [ ] `backward_skip` + 負の `position_delta` が受理される
- [ ] Response の `event_id` が `save` 戻り値の集約に含まれる ID と一致する（Generator 戻り値に依存しない）

---

## RecordQuizAttempt

### 変更理由（Why）

- 小テスト 1 受験（再試行含む）を `LearningSession` に追記する。追記された結果は、視聴ログ・字幕抜粋等とともに `GetLearningSnapshot` 経由で LAD / AI に渡る **共有学習コンテキストの構成要素の一つ** となる
- 設問定義（問題文・選択肢・正解）は `Lecture.quizDefinition` に置き、Attempt には **回答結果のみ** 記録する（[domain-model.md#QuizAnswer](./domain-model.md)）
- 既存 `POST /api/quiz-attempts` のドメイン駆動版

### 仕様

| 項目 | 値 |
|------|-----|
| ID | `RecordQuizAttempt` |
| コンテキスト | Learning |
| アクター | 学習者（Google Form 経由） |
| トリガー | 小テスト送信 1 回 |
| Interactor | `RecordQuizAttemptUseCase` |

### 前提条件

- `learnerId`, `lectureId` が確定している
- `LectureCatalog.find_by_id(lectureId)` が `Lecture` を返す（存在しない場合は `err(LectureNotFoundError)` / `LECTURE_NOT_FOUND`）
- 各 `QuizAnswer.question_index` が `Lecture.quizDefinition` に存在する

### 入力 `RecordQuizAttemptRequest`

| フィールド | 型 | 必須 | 既存 API フィールド |
|-----------|-----|------|-------------------|
| `learner_id` | `LearnerId` | yes | `participant_id` |
| `lecture_id` | `LectureId` | yes | （未導入。近い実験では固定値可） |
| `attempted_at` | `datetime` | yes | `timestamp` / `created_at` |
| `score_numerator` | `int` | yes | `score_numerator` |
| `score_denominator` | `int` | yes | `score_denominator` |
| `answers` | `tuple[QuizAnswer, ...]` | yes | `answers`（下表） |

#### `answers` の各要素（`QuizAnswer`）

| フィールド | 型 | 必須 | 既存 API | 説明 |
|-----------|-----|------|---------|------|
| `question_index` | `int` | yes | `question_index` | 設問番号。**`Lecture.quizDefinition` の `Question.index` への参照 ID**（近い実験では 1 始まり・5 問想定） |
| `selected_answer` | `str` | yes | `selected_answer` | 学習者が選んだ選択肢 |
| `is_correct` | `bool` | yes | `is_correct` | 正誤 |

**Request に含めないもの**: 問題文・選択肢一覧・正解の定義。これらは `lecture_id` 経由で `LectureCatalog` の `QuizDefinition` から解決する。

**近い実験（5 問）の例**:

- `score_denominator = 5`
- `answers` は 5 件、`question_index` は 1〜5 で **Attempt 内一意**
- 第 3 問不正解の例: `{ question_index: 3, selected_answer: "...", is_correct: false }`

**AI が「第3問が間違えています」と応答するためのデータ流れ**:

1. **記録**: 上記 `question_index` + `is_correct` を Session に保存（本 UC）
2. **Read**: `GetLearningSnapshot` が `quiz_answers`（+ `latest_quiz_attempt`）を返す
3. **表示 / プロンプト**: interfaces 層 Presenter が `question_index` で `Lecture.quizDefinition` の設問文と結合（「問3: 不正解」または問題内容付き）

問題文を AI に渡す処理は **Record UC ではなく Read + Presenter** の責務とする。

### 出力 `RecordQuizAttemptResponse`

| フィールド | 型 |
|-----------|-----|
| `attempt_id` | `QuizAttemptId` |
| `session_id` | `LearningSessionId` |

### 依存

- `StartOrGetLearningSessionUseCase`（compose）
- `LectureCatalog`
- `LearningSessionRepository`

（`QuizAttemptIdGenerator` は SQLite 本番配線では注入しない。[save 戻り値と子 Entity ID の確定](#learningsessionrepositorysave-戻り値と子-entity-id-の確定) 参照）

### 手順 `execute`

1. `lecture = lecture_catalog.find_by_id(request.lecture_id)`
2. `lecture is None` なら **`err(LectureNotFoundError)`**（`LECTURE_NOT_FOUND`）で終了
3. 各 `answer.question_index` が `lecture.quiz_definition` に存在することを検証（不存在なら **`err(ValidationError)`** / `UNKNOWN_QUESTION_INDEX`）
4. `session_response = start_or_get.execute(...)`
5. `updated = session_response.session.record_quiz_attempt(...)`（当該 UC 内で 1 件追記）
6. `persisted = repository.save(updated)`
7. `attempt_id = persisted.quiz_attempts` の **末尾 1 件**の ID
8. `Response(attempt_id=attempt_id, session_id=persisted.id)` を return

### 例外

[application-error-handling.md#RecordQuizAttempt](./application-error-handling.md#recordquizattempt)

| 条件 | AppError | ErrorCode |
|------|----------|-----------|
| 講義カタログに `lectureId` が無い | `LectureNotFoundError` | `LECTURE_NOT_FOUND` |
| スコア不変条件違反 | `ValidationError` | `INVALID_QUIZ_ATTEMPT` |
| 未知の `question_index` | `ValidationError` | `UNKNOWN_QUESTION_INDEX` |

### 受入基準

- [ ] 初回受験 → Session も新規作成されうる
- [ ] 再受験 → 同一 Session に 2 件目の `QuizAttempt` が追加される
- [ ] 存在しない `lectureId` → `err(LectureNotFoundError)` / `LECTURE_NOT_FOUND`
- [ ] カタログに無い `question_index` → 拒否
- [ ] 5 問形式: `answers` 5 件・`question_index` 1〜5 で保存できる
- [ ] `question_index=3`, `is_correct=false` が Snapshot の `quiz_answers` に含まれ、AI が第 3 問の不正解を特定できる
- [ ] Response の `attempt_id` が `save` 戻り値の集約に含まれる ID と一致する（Generator 戻り値に依存しない）

---

## 共有学習コンテキスト（Read）

### 変更理由（Why）

- 学習者の **視聴ログ** または **小テスト（再試行含む）** が記録されると、LAD と AI 振り返りは **同じ学習過程** を参照する必要がある
- Application 層は、1 `LearningSession` スコープの Read Model **`LearningSnapshot`** を **LAD と AI の双方** に渡す責務を持つ（[domain-model.md#Read Model: LearningSnapshot](./domain-model.md)）
- **学習コンテキスト**とは Snapshot が表す 1 Session スコープのデータ束: **視聴ログ**（`viewing_events`）、**小テスト結果**（`latest_quiz_attempt` + `quiz_answers`）、**字幕抜粋**（`lecture_transcript_excerpts`）等。小テストはその構成要素の一つ
- LAD 専用 Read と AI 専用 Read を分けない。Consumer 別の Port 名（`LadDataQuery` 等）も設けない
- 文字列プロンプトへの変換は interfaces 層 Presenter が担う。本 UC は **構造化された `LearningSnapshot`** を返す

### Write → Read の関係

```
RecordViewingEvent / RecordQuizAttempt  （共有コンテキストの更新源）
        ↓
GetLearningSnapshot                     （LAD と AI が参照する唯一の Read UC）
        ↓
  ┌─────┴─────┐
LAD UI    SendChatMessage（LearningSnapshotQuery Port 経由）
```

### Consumer とトリガー

| Consumer | いつ `GetLearningSnapshot` を呼ぶか |
|----------|-----------------------------------|
| LAD UI | 画面表示時、`RecordViewingEvent` / `RecordQuizAttempt` 後の再表示時 |
| Tutoring（`SendChatMessage`） | ユーザー発話のたび（応答生成前に最新 Snapshot を取得） |

**更新のきっかけ**は視聴ログ・小テスト記録。LAD も AI も、その後 **同じ UC・同じ `LearningSnapshot`** で中身を取り直す。

---

## GetLearningSnapshot

Learning コンテキストにおける **共有 Read の唯一の主 UC**。

### 仕様

| 項目 | 値 |
|------|-----|
| ID | `GetLearningSnapshot` |
| コンテキスト | Learning |
| アクター | LAD UI、Tutoring（`SendChatMessage` 内部） |
| トリガー | 上表「Consumer とトリガー」参照 |
| Interactor | `GetLearningSnapshotUseCase` |
| Tutoring からの参照 | `LearningSnapshotQuery` Port（実体は本 UC と同一契約） |

### 前提条件

- `learnerId`, `lectureId` は空でない
- `LectureCatalog.find_by_id(lectureId)` が `Lecture` を返す（無い場合は `err(LectureNotFoundError)` / `LECTURE_NOT_FOUND` → interfaces 層で 404）
- `LearningSession` が未作成の場合は **200 + 空 Snapshot** を返す（視聴・小テスト前の LAD / 初回チャットは正常系）

### 本 UC が行わないこと

- 視聴ログ・小テストの**記録**（`RecordViewingEvent` / `RecordQuizAttempt`）
- LLM プロンプト文字列の組み立て（interfaces Presenter）
- LAD / AI **向けの別データ**を返すこと

### 入力 `GetLearningSnapshotRequest`

| フィールド | 型 | 必須 |
|-----------|-----|------|
| `learner_id` | `LearnerId` | yes |
| `lecture_id` | `LectureId` | yes |

### 出力 `GetLearningSnapshotResponse`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `snapshot` | `LearningSnapshot` | LAD 表示・AI プロンプト入力の共通 Read Model |
| `content_updated_at` | `datetime \| None` | 当該 Session 内の視聴・小テストの最終更新時刻。データ無しなら `None` |

`content_updated_at` は Snapshot 内イベントの `max(occurred_at, attempted_at)` から算出する。Consumer はこの値で **Snapshot 再取得要否** を判定する（Application 層に別 Port / UC は設けない）。

### HTTP 応答（interfaces 層への委譲）

| 状況 | Application 層 | HTTP |
|------|----------------|------|
| 講義カタログに `lectureId` 無し | `LectureNotFoundError`（`LECTURE_NOT_FOUND`） | 404 |
| Session 未作成（視聴・小テスト前） | 空 Snapshot + `content_updated_at=None` | **200** |
| Session あり | Snapshot + `content_updated_at` | 200 |

### 依存

- `LearningSessionRepository`
- `LectureCatalog`
- `LearningSnapshotBuilder`（domain service）

### 手順 `execute`

1. `lecture = lecture_catalog.find_by_id(request.lecture_id)`
2. `lecture is None` なら **`err(LectureNotFoundError)`**（`LECTURE_NOT_FOUND`）で終了
3. `session = repository.find_by_learner_and_lecture(request.learner_id, request.lecture_id)`
4. `session is None` なら空の `LearningSnapshot` と `content_updated_at=None` を return
5. `snapshot = LearningSnapshotBuilder.build(session=session, lecture=lecture)`
6. `content_updated_at = _max_event_time(session)` を算出
7. `Response(snapshot=snapshot, content_updated_at=content_updated_at)` を return

### 例外

[application-error-handling.md#GetLearningSnapshot](./application-error-handling.md#getlearningsnapshot)

| 条件 | AppError | ErrorCode |
|------|----------|-----------|
| 講義カタログに `lectureId` が無い | `LectureNotFoundError` | `LECTURE_NOT_FOUND` |

### 受入基準

- [ ] 同一 `(learnerId, lectureId)` で LAD 用・Tutoring 用に呼び出しても **同じ `snapshot`** が返る
- [ ] `RecordViewingEvent` 後に呼び出すと、新イベントが `snapshot.viewing_events` に含まれる
- [ ] `RecordQuizAttempt`（再試行）後に呼び出すと、`latest_quiz_attempt` が最新 Attempt に更新される
- [ ] `quiz_answers` の `question_index` + `is_correct` により、Presenter 経由で「第 N 問が不正解」を AI が参照できる
- [ ] 複数 Attempt → `attempted_at` 最大が `latest_quiz_attempt`
- [ ] スコープは 1 `LearningSession` のみ（他 learner / lecture の混入なし）
- [ ] Builder / Interactor はプロンプト文字列を生成しない
- [ ] Session 未作成 → 空 Snapshot、`content_updated_at=None`（**404 にしない**）
- [ ] 存在しない `lectureId` → `err(LectureNotFoundError)` / `LECTURE_NOT_FOUND`（interfaces 層で 404）
- [ ] `SendChatMessage` が `LearningSnapshotQuery` 経由で本 UC と同契約の Snapshot を取得できる

### 既存 API 互換（interfaces 層・Application Port なし）

| 既存 API | 移行方針 |
|---------|---------|
| `GET /api/participants/{id}/lad` | Presenter が `GetLearningSnapshotResponse.snapshot` を JSON 化 |
| `GET /api/last-updated` | `GetLearningSnapshotUseCase` を呼び **`content_updated_at` のみ** JSON で返す薄い Adapter。Application 層に独立 Port / UC は設けない |

`last-updated` のスコープは **`(learnerId, lectureId)` = 1 LearningSession** とする（現行の DB 全体 MAX とは異なる）。

---

## Tutoring / Research Export（後続）

`StartOrGetTutorSession` と `SendChatMessage` は本節に詳細仕様案を記載する。Research Export と Tutoring 将来拡張は概要のみ。

### Port 一覧（Tutoring コンテキスト）

#### `TutorSessionRepository`

| メソッド | 入力 | 出力 | 備考 |
|---------|------|------|------|
| `find_by_id` | `TutorSessionId` | `TutorSession \| None` | |
| `find_by_learning_session_id` | `LearningSessionId` | `TutorSession \| None` | StartOrGet の get |
| `list_all` | なし | `tuple[TutorSession, ...]` | `NearTermExperimentPolicy` 用（近い実験は件数少） |
| `save` | `TutorSession` | `None` | 集約全体を upsert |

#### `TutorSessionIdGenerator` / `MessageIdGenerator`

| Port | メソッド | 出力 |
|------|---------|------|
| `TutorSessionIdGenerator` | `next_id()` | `TutorSessionId` |
| `MessageIdGenerator` | `next_id()` | `MessageId` |

#### `LearningSnapshotQuery`（Learning → Tutoring ACL）

Learning コンテキストの **`LearningSnapshotQuery`**（上記 Port 一覧）と同一契約。Tutoring は **`GetLearningSnapshotUseCase` と同じ Read Model** を取得する。

#### `ChatPromptBuilder`（interfaces 層 ACL・Port）

| メソッド | 入力 | 出力 | 備考 |
|---------|------|------|------|
| `build` | `LearningSnapshot`, `Message[]`, `user_message`, `Lecture`（設問文結合用） | `str` | LLM へ渡すプロンプト文字列。domain-model の Presenter 責務 |

#### `LlmGateway`

| メソッド | 入力 | 出力 | 備考 |
|---------|------|------|------|
| `generate` | `prompt: str` | `str` | インフラ（Vertex 等）。近い実験は 1 モデル固定 |

---

### Tutoring UC 一覧

| 優先 | ID | 公開 / 内部 | 概要 |
|------|-----|------------|------|
| 1 | `StartOrGetTutorSession` | 内部（compose 可） | `LearningSessionId` に TutorSession を 1 本確保。`NearTermExperimentPolicy` を適用 |
| 2 | `SendChatMessage` | 公開 | user 発話追記 → 応答生成 → assistant 追記（[将来拡張](#tutoring-将来拡張複数エージェント) 参照） |
| — | `ClassifyInterpretationSupportType` | 内部 | **将来**。解釈支援種類を判定 |
| — | `InvokeTutoringAgent` | 内部 | **将来**。種類に応じたエージェントを実行 |

Tutoring は `LearningSnapshotQuery` Port 経由でのみ Learning を参照する（[domain-model.md#コンテキストマップ](./domain-model.md)）。Learning **Entity** は import しない。

---

## StartOrGetTutorSession

### 変更理由（Why）

- 1 `LearningSession` に `TutorSession` は 1 本まで（[domain-model.md#TutorSession](./domain-model.md)）
- LAD / 小テスト / 動画と**自由に往復**しても TutorSession は新規作成せず Message を追記する。初回 AI 利用時に Session を 1 本確保する
- `SendChatMessage` 等が共通で「TutorSession を確保してから Message 追記」するため、手順を 1 UC に集約する

### 仕様

| 項目 | 値 |
|------|-----|
| ID | `StartOrGetTutorSession` |
| コンテキスト | Tutoring |
| アクター | 学習者（`LearningSession` は Learning 側で確保済み、または同リクエスト内で compose） |
| トリガー | `SendChatMessage` の内部、または単体 API（任意） |
| Interactor | `StartOrGetTutorSessionUseCase` |

### 前提条件

- `learningSessionId` は空でない（Shared Kernel）
- 新規 start 時、`NearTermExperimentPolicy` が 2 本目作成を拒否しないこと

### 本ユースケースが行わないこと

- `LearningSession` の作成（Learning コンテキストの `StartOrGetLearningSession`）
- `Message` の追記
- 学習データ（Snapshot）の取得
- LLM 呼び出し

### 入力 `StartOrGetTutorSessionRequest`

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `learning_session_id` | `LearningSessionId` | yes | 紐づく学習セッション |
| `started_at` | `datetime` | yes | 新規 start 時の `TutorSession.started_at`。get 時は未使用 |

### 出力 `StartOrGetTutorSessionResponse`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `tutor_session_id` | `TutorSessionId` | |
| `session` | `TutorSession` | 呼び出し元が Message 追記を続けるため、集約を返す |
| `outcome` | `StartOrGetOutcome` | `CREATED` = 新規 start、`RETRIEVED` = 既存 get |

### 依存

- `TutorSessionRepository`
- `TutorSessionIdGenerator`
- `NearTermExperimentPolicy`（domain service）

### 手順 `execute`

1. `existing = repository.find_by_learning_session_id(request.learning_session_id)`
2. `existing is not None` なら `Response(tutor_session_id=existing.id, session=existing, outcome=RETRIEVED)` を return
3. `NearTermExperimentPolicy.assert_can_start_tutor_session(existing_sessions=repository.list_all(), request=TutorSessionStartRequest(id=新ID, learning_session_id=...))`
4. `new_id = id_generator.next_id()`
5. `session = TutorSession.start(id=new_id, learning_session_id=request.learning_session_id, started_at=request.started_at)`
6. `repository.save(session)`
7. `Response(tutor_session_id=session.id, session=session, outcome=CREATED)` を return

### 例外

[application-error-handling.md#StartOrGetTutorSession](./application-error-handling.md#startorgettutorsession)

| 条件 | AppError | ErrorCode | HTTP（interfaces） |
|------|----------|-----------|-------------------|
| 同一 `learningSessionId` に 2 本目を start（近い実験） | `ConflictError` | `TUTOR_SESSION_POLICY_VIOLATION` | 409 |
| 同一 `learningSessionId` が既に存在（競合） | 手順 1 で get するため通常発生しない | — | — |

### 受入基準

- [ ] 未作成の `learningSessionId` → `outcome=CREATED` で 1 件 `save` される
- [ ] 既存 TutorSession がある → `outcome=RETRIEVED`、`save` は呼ばれない
- [ ] 同一 `learningSessionId` で 2 回呼び出し → 2 回目は get（TutorSession は 1 本）
- [ ] 近い実験: 異なる `learningSessionId` なら複数 TutorSession を持てる
- [ ] Policy により 2 本目 start が拒否される

---

## SendChatMessage

### 変更理由（Why）

- 学習者の発話 1 回に対し AI 振り返り応答を返し、**user / assistant の Message を TutorSession に追記**する
- 応答生成前に **LAD と同じ `LearningSnapshot`** を参照し、視聴ログ・小テスト結果・字幕抜粋等を含む共有学習コンテキストを AI に渡す
- 既存 `POST /chat` のドメイン駆動版。近い実験では単一 LLM；将来は [Classify → Invoke](#tutoring-将来拡張複数エージェント) に差し替え可能な compose 構造とする

### 仕様

| 項目 | 値 |
|------|-----|
| ID | `SendChatMessage` |
| コンテキスト | Tutoring |
| アクター | 学習者 |
| トリガー | チャット UI から 1 発話送信 |
| Interactor | `SendChatMessageUseCase` |
| 既存 API | `POST /chat` |

### 前提条件

- `user_message` は空文字でない
- 初回（`tutor_session_id` 未指定）: `learnerId` と `lectureId` が確定している
- `LearningSnapshotQuery` が Snapshot を返せる（Session 未作成時は空 Snapshot 可）

### 本ユースケースが行わないこと

- 視聴ログ・小テストの記録（Learning UC）
- プロンプト文字列の組み立て詳細（`ChatPromptBuilder` Port / interfaces Presenter）
- LLM SDK の直接 import

### 入力 `SendChatMessageRequest`

| フィールド | 型 | 必須 | 既存 API | 説明 |
|-----------|-----|------|---------|------|
| `user_message` | `str` | yes | `message` | 学習者の発話 |
| `tutor_session_id` | `TutorSessionId \| None` | no | `session_id` | 継続対話時。未指定なら初回 |
| `learner_id` | `LearnerId` | 初回 yes | `participant_id` | |
| `lecture_id` | `LectureId` | 初回 yes | （未導入・固定値可） | Snapshot 取得用 |
| `sent_at` | `datetime` | yes | — | user / assistant Message の `created_at` |

**初回 vs 継続**:

| パターン | 必須フィールド |
|---------|---------------|
| 初回（`tutor_session_id` なし） | `learner_id`, `lecture_id`, `user_message` |
| 継続（`tutor_session_id` あり） | `tutor_session_id`, `user_message`（`learner_id` / `lecture_id` は Snapshot 用に引き続き渡してよい） |

### 出力 `SendChatMessageResponse`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `tutor_session_id` | `TutorSessionId` | クライアントが次回以降に指定 |
| `assistant_content` | `str` | AI 応答本文 |
| `user_message_id` | `MessageId` | 追記した user Message |
| `assistant_message_id` | `MessageId` | 追記した assistant Message |

### 依存

- `StartOrGetLearningSessionUseCase`（Learning・初回 compose）
- `StartOrGetTutorSessionUseCase`（compose）
- `LearningSnapshotQuery`
- `ChatPromptBuilder`
- `LlmGateway`（近い実験。将来は `InvokeTutoringAgent` に置換）
- `TutorSessionRepository`
- `MessageIdGenerator`
- `LectureCatalog`（設問文をプロンプトに載せるため。`ChatPromptBuilder` 入力用）

### 手順 `execute`（近い実験）

1. `user_message` が空なら **`err(ValidationError)`**（`EMPTY_USER_MESSAGE`）で終了
2. **TutorSession 解決**
   - `tutor_session_id` 指定時: `tutor_session = repository.find_by_id(...)`。無ければ **`err(TutorSessionNotFoundError)`**（`TUTOR_SESSION_NOT_FOUND`）
   - 未指定時: `learning = start_or_get_learning_session.execute(learner_id, lecture_id, ...)` → `start_or_get_tutor_session.execute(learning_session_id=learning.session_id, ...)`
3. `snapshot = learning_snapshot_query.get_by_learner_and_lecture(learner_id, lecture_id)`
4. `lecture = lecture_catalog.find_by_id(lecture_id)`（プロンプト用。無ければ **`err(LectureNotFoundError)`** / `LECTURE_NOT_FOUND`）
5. **初回・半角数字のみ特例**（既存挙動）: `messages` が空かつ `user_message` が `^[0-9]+$` のとき、定型文を `assistant_content` とし **LLM を呼ばない**（`FirstMessagePolicy` 相当）
6. 上記以外: `prompt = chat_prompt_builder.build(snapshot, tutor_session.messages, user_message, lecture)` → `assistant_content = llm_gateway.generate(prompt)`
7. `user_msg_id`, `asst_msg_id = message_id_generator.next_id()` × 2
8. `updated = tutor_session.append_message(user)` → `.append_message(assistant)`
9. `repository.save(updated)`
10. `Response(...)` を return

### 例外

[application-error-handling.md#SendChatMessage](./application-error-handling.md#sendchatmessage)

| 条件 | AppError | ErrorCode | HTTP |
|------|----------|-----------|------|
| `user_message` 空 | `ValidationError` | `EMPTY_USER_MESSAGE` | 400 |
| 未知の `tutor_session_id` | `TutorSessionNotFoundError` | `TUTOR_SESSION_NOT_FOUND` | 404 |
| 講義カタログ不在 | `LectureNotFoundError` | `LECTURE_NOT_FOUND` | 404 |
| LLM 障害 | `LlmGatewayError` | `LLM_GATEWAY_ERROR` | 502 等 |

### HTTP 応答（interfaces 層）

| 状況 | HTTP |
|------|------|
| 成功 | 200 + `{ response, session_id }`（既存 JSON 形状。`response` = `assistant_content`、`session_id` = `tutor_session_id`） |
| メッセージなし | 400 |

### 受入基準

- [ ] 初回送信 → `LearningSession` / `TutorSession` が compose され、`tutor_session_id` が返る
- [ ] 2 回目以降 → 同一 TutorSession に user / assistant が 2 件追加される
- [ ] 応答生成前に `LearningSnapshotQuery` が呼ばれ、LAD と同契約の Snapshot が入力になる
- [ ] Snapshot 上の `quiz_answers`（`question_index` + `is_correct`）がプロンプトに載り、第 N 問の正誤を AI が参照できる
- [ ] 初回・半角数字のみ → 定型文応答、LLM 未呼び出し、Message は 2 件永続化
- [ ] Tutoring コードが `domain.learning.learning_session` 等を import しない
- [ ] 将来: 手順 6 を `Classify` → `Invoke` に差し替えても compose 構造は維持できる

### 既存 API 互換（interfaces 層）

| 既存 | 移行方針 |
|------|---------|
| `POST /chat` | `participant_id` → `learner_id`、`lecture_id` は近い実験では定数。`session_id` → `tutor_session_id` |

---

### Tutoring 将来拡張（複数エージェント）

**変更理由（Why・将来）**

- 研究 RQ は「暫定的な解釈」の外化支援（[domain-model.md#研究コンテキスト](./domain-model.md)）。支援の仕方は **解釈支援種類** ごとに異なりうる
- 見通し: **解釈支援種類ごとに命題単位のエージェント** を定義し、種類に応じたエージェントを動かす
- 前提: 解釈支援種類は **人間同士の対話に即したもの** かつ **学習科学の裏付け** があること
- システム論: **まず解釈支援種類を判定** → **該当エージェントを呼ぶ**（2 段）

**近い実験（現行）**: 種類判定は固定（単一種）、エージェント 1 体。`SendChatMessage` が直接 `LlmGateway` を呼ぶ。

**将来**: `SendChatMessage` はオーケストレータのまま、内部で `Classify` → `Invoke` を compose する。

```
SendChatMessage
  1. LearningSnapshotQuery（LAD と同じ Read Model）
  2. ClassifyInterpretationSupportType  → InterpretationSupportType
  3. InvokeTutoringAgent(support_type)  → assistant テキスト
  4. Message 永続化
```

#### 将来ユビキタス言語（Tutoring）

| 用語 | 意味 |
|------|------|
| 解釈支援種類 | 学習科学・対話研究に裏付けられた支援の型（`InterpretationSupportType`） |
| チューターエージェント | 1 解釈支援種類（命題単位）に対応する LLM 対話戦略 |
| エージェント ID | 実行時に呼んだエージェントの識別子（`TutoringAgentId`）。研究・Export 用 |

種類の定義と研究根拠は **domain-model.md**（What）。判定・呼び出し手順は **本仕様**（How）。プロンプト文言・モデル名は interfaces / infrastructure。

#### 将来 UC 概要（詳細仕様は後続 PR）

**`ClassifyInterpretationSupportType`（内部）**

| 項目 | 内容 |
|------|------|
| 入力 | user 発話、`LearningSnapshot`、直近 `Message[]` |
| 出力 | `InterpretationSupportType` |
| 依存 Port | `InterpretationSupportClassifier` |
| 近い実験 | 常に `default`（または列挙 1 値）を返す stub |

**`InvokeTutoringAgent`（内部）**

| 項目 | 内容 |
|------|------|
| 入力 | `InterpretationSupportType`、`LearningSnapshot`、履歴、user 発話 |
| 出力 | assistant テキスト、`TutoringAgentId`（どのエージェントを呼んだか） |
| 依存 Port | `TutoringAgentRegistry`（種類 → エージェント）、`TutoringAgentGateway`（1 エージェント実行） |
| 近い実験 | Registry に 1 エントリのみ |

**`SendChatMessage`（公開・compose 先）**

- 近い実験: Snapshot 取得 → `LlmGateway` → Message 追記
- 将来: Snapshot 取得 → `Classify` → `Invoke` → Message 追記（**assistant に `agent_id` / `support_type` をメタデータとして残せる設計**）

#### 拡張の不変条件

- エージェント追加 = **カタログ（Registry）+ エージェント実装の追加**。`SendChatMessage` の compose 手順は変えない
- **判定（Classify）と実行（Invoke）を UC / Port で分離**し、`SendChatMessage` に種類別 if 文を直書きしない
- 解釈支援種類をカタログに載せるときは、学習科学・対話研究の根拠を domain-model 側に記録する

#### 将来 Port（Tutoring）

| Port | 責務 |
|------|------|
| `InterpretationSupportClassifier` | 発話 + Snapshot + 履歴 → `InterpretationSupportType` |
| `TutoringAgentRegistry` | `InterpretationSupportType` → エージェント定義（命題単位） |
| `TutoringAgentGateway` | 1 エージェント実行（プロンプト in → 応答 out）。現行 `LlmGateway` の拡張先 |
| `LearningSnapshotQuery` | 変更なし（LAD と AI 共通 Read） |

### Research Export UC 一覧

| ID | 概要 |
|----|------|
| `ExportResearchData` | 分析用に **視聴ログ**・**小テスト結果**・**対話ログ** を Read 専用 Port から取得し、DTO として出力する |

手順ごとの `ok` / `err`: [application-error-handling.md#Research Export UC: 手順ごとの ok / err 表](./application-error-handling.md#research-export-uc-手順ごとの-ok--err-表)

#### 出力対象（合意）

研究分析向けエクスポートは、次の **3 種類** を想定する。

| 種別 | ソースコンテキスト | ドメイン上のデータ | 備考 |
|------|-------------------|-----------------|------|
| **視聴ログ** | Learning | `LearningSession` 配下の `ViewingEvent[]` | 動画操作の時系列 |
| **小テスト結果** | Learning | `LearningSession` 配下の `QuizAttempt[]` と `QuizAnswer[]` | 再試行含む全 Attempt。設問定義は `Lecture.quizDefinition` 参照 |
| **対話ログ** | Tutoring | `TutorSession` 配下の `Message[]` | user / assistant の発話時系列。将来は `support_type` / `agent_id` メタデータを含めうる（[Tutoring 将来拡張](#tutoring-将来拡張複数エージェント)） |

**結合キー**: `(learnerId, learningSessionId)`（必要に応じて `lectureId` を付与）。視聴・小テスト・対話を同一 Session 単位で対応づけ可能であること（[domain-model.md#Research Export](./domain-model.md)）。

**スコープ外（現時点）**: リアルタイム LAD / LLM 生成。出力形式（1 ファイル vs 種別ごと CSV 等）は詳細仕様で決定。

**不変条件**: Export は **書き込みを行わない**（Read 中心）。Learning / Tutoring の Entity を直接変更しない。

---

## 実装優先順位

1. Port 契約（Protocol）+ Fake 実装
2. `StartOrGetLearningSessionUseCase` + テスト
3. `RecordViewingEventUseCase` + テスト
4. `RecordQuizAttemptUseCase` + テスト
5. `GetLearningSnapshotUseCase` + テスト
6. Infrastructure Adapter 接続（既存 API テスト GREEN を維持）
7. `StartOrGetTutorSessionUseCase` + `SendChatMessageUseCase` + テスト（Tutoring）
