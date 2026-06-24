# ドメイン層（エンティティ層）実装計画

## 変更理由（Why）

- 現行コードは Flask ルートと SQLite repository にドメイン知識が分散している
- [domain-model.md](./domain-model.md) で定義したモデルのうち、**エンティティ層のみ**を先にコード化し、不変条件と境界づけられたコンテキストを確立する
- Mapper・Repository・Use Case・API 接続は本計画の**スコープ外**とし、ドメイン層が単体テストで完結する状態を目指す
- 各フェーズは 1 PR 相当とし、AI が単独で実装・検証できる粒度に分割する

## スコープ

### 本計画に含める

| 要素 | 説明 |
|------|------|
| 境界づけられたコンテキスト | Learning / Tutoring / Research Export / Shared Kernel のパッケージ境界 |
| 値オブジェクト（VO） | ID 型、列挙型、`QuizDefinition` 等 |
| エンティティ | 集約ルート・子 Entity、`Learner`（Shared Kernel） |
| Read Model | `LearningSnapshot`（Entity ではないが Learning コンテキストが所有） |
| ドメインサービス | `LearningSnapshotBuilder`、`NearTermExperimentPolicy` |

### 本計画に含めない（別計画）

- Mapper（既存 DB ↔ ドメイン）
- Port / Repository / Use Case
- Flask ルート・Presenter・LLM 呼び出し
- DB スキーマ変更・マイグレーション
- Research Export の Export Use Case 本体

## 前提

- ドメイン定義: [domain-model.md](./domain-model.md)
- 既存 ADR: [Arcitecture/ADR_SSSRL-backend_2026-02-23.md](../../Arcitecture/ADR_SSSRL-backend_2026-02-23.md)
- テスト実行: `uv run pytest tests/ -v`
- 実装言語: Python 3.10+
- ドメイン層は **Flask / SQLite / vertexai を import しない**
- 既存 API テストは本計画の各フェーズ完了時も引き続きパスすること（ドメイン追加のみでは既存コードを変更しない）

## 目標ディレクトリ構成（ドメイン層完了時）

```
domain/
  __init__.py
  shared/                          # Shared Kernel
    ids.py                         # LearnerId, LectureId, LearningSessionId, ...
    learner.py                     # Learner
  learning/                        # Learning コンテキスト
    lecture.py                     # Lecture
    quiz_definition.py             # QuizDefinition, Question（VO）
    learning_session.py            # LearningSession（集約ルート）
    viewing_event.py               # ViewingEvent, ViewingAction（VO）
    quiz_attempt.py                # QuizAttempt, QuizAnswer
    learning_snapshot.py           # LearningSnapshot（Read Model）
    participant_program.py         # ParticipantProgram（任意・Phase 6）
    services/
      learning_snapshot_builder.py # Domain Service
  tutoring/                        # Tutoring コンテキスト
    tutor_session.py               # TutorSession（集約ルート）
    message.py                     # Message, MessageRole（VO）
    services/
      near_term_experiment_policy.py
  research_export/                 # Research Export コンテキスト（Entity なし）
    __init__.py                    # パッケージ境界のみ（Phase 0）
tests/
  test_domain/
    test_shared_kernel.py
    test_learning/
      test_value_objects.py
      test_entities.py
      test_viewing_event_invariants.py
      test_learning_session_aggregate.py
      test_learning_snapshot_builder.py
    test_tutoring/
      test_value_objects.py
      test_entities.py
      test_near_term_experiment_policy.py
    test_context_boundaries.py     # コンテキスト間 import ルール
```

## コンテキスト境界ルール（実装時の制約）

| ルール | 検証方法 |
|--------|----------|
| Tutoring は Learning の Entity（`LearningSession` 等）を **直接 import しない** | `test_context_boundaries.py` |
| Tutoring が参照する学習データは `LearningSnapshot`（Read Model）のみ | Builder の出力型を Tutoring テストで使用 |
| Shared Kernel の ID 型は全コンテキストで同一モジュール（`domain.shared.ids`）を import | 型の同一性テスト |
| Research Export は Entity を持たない（Phase 6 までパッケージ stub のみ） | ディレクトリ存在確認 |
| ドメインサービスは状態を持たない（純関数または static メソッド相当） | 実装レビュー + テスト |

---

## Phase 0: パッケージ骨格と Shared Kernel（ID 型）

### What

- `domain/` パッケージと境界づけられたコンテキスト用サブパッケージを作成
- Shared Kernel の全 ID 型（Value Object）を実装
- 空文字拒否等の共通不変条件を VO 生成時に enforce

### 成果物

- `domain/shared/ids.py`
- `domain/learning/__init__.py`, `domain/tutoring/__init__.py`, `domain/research_export/__init__.py`
- `tests/test_domain/test_shared_kernel.py`

### ID 型一覧

| 型 | 所属 |
|----|------|
| `LearnerId` | Shared Kernel |
| `LectureId` | Shared Kernel |
| `LearningSessionId` | Shared Kernel |
| `ViewingEventId` | Learning |
| `QuizAttemptId` | Learning |
| `ParticipantProgramId`, `ProgramId` | Learning（Phase 6 で使用） |
| `TutorSessionId` | Tutoring |
| `MessageId` | Tutoring |

### 受入基準

- [ ] `LearnerId("")` が ValueError 等で拒否される
- [ ] 上記 ID 型がすべて実装されている
- [ ] `domain/`, `domain/learning/`, `domain/tutoring/`, `domain/research_export/` が import 可能
- [ ] 既存 `uv run pytest tests/ -v` がすべてパスする

### スコープ外

- Entity 本体、列挙型（ViewingAction 等）、ドメインサービス

---

## Phase 1: Shared Kernel Entity と Learning 値オブジェクト

### What

- Shared Kernel の `Learner` Entity を実装
- Learning コンテキストの VO: `ViewingAction`, `QuizDefinition`, `Question` を実装

### 成果物

- `domain/shared/learner.py`
- `domain/learning/quiz_definition.py`
- `domain/learning/viewing_event.py`（`ViewingAction` のみでも可）
- `tests/test_domain/test_learning/test_value_objects.py`

### 受入基準

- [ ] `ViewingAction` に 6 種類（play / pause / forward_skip / backward_skip / forward_seek / backward_seek）が定義されている
- [ ] `QuizDefinition` は questions が 1 件未満のとき拒否される
- [ ] `Question` の index が同一 QuizDefinition 内で重複すると拒否される
- [ ] `Learner` は `LearnerId` のみを持つ最小 Entity である
- [ ] 既存 pytest 全パス

### スコープ外

- LearningSession 等の Entity、Tutoring 側 VO

---

## Phase 2: Learning エンティティと集約不変条件

### What

- Learning コンテキストの Entity を [domain-model.md](./domain-model.md) どおり実装
- `LearningSession` を集約ルートとし、子 Entity の追加は集約ルート経由に限定
- 不変条件を factory メソッドまたは `__post_init__` で enforce

### 成果物

- `domain/learning/lecture.py`
- `domain/learning/learning_session.py`
- `domain/learning/viewing_event.py`（ViewingEvent 本体）
- `domain/learning/quiz_attempt.py`
- `tests/test_domain/test_learning/test_entities.py`
- `tests/test_domain/test_learning/test_viewing_event_invariants.py`
- `tests/test_domain/test_learning/test_learning_session_aggregate.py`

### 受入基準

- [ ] `Lecture` は `quizDefinition` を 1 つ持ち、`videoUrl` が空のとき拒否される
- [ ] `LearningSession` は `(learnerId, lectureId)` 作成後に変更不可
- [ ] 同一 `(learnerId, lectureId)` の Session 重複は集約ルートまたは factory で拒否される（repository 導入前は in-memory テストで検証）
- [ ] `ViewingEvent`: `backward_skip` + `positionDelta=-5` が受理される
- [ ] `ViewingEvent`: `play` + `positionDelta != 0` が拒否される
- [ ] `QuizAnswer` に問題文フィールドが**ない**（Lecture 定義参照のみ）
- [ ] `0 <= scoreNumerator <= scoreDenominator` かつ `scoreDenominator > 0`
- [ ] 子 Entity を Session 外から直接作成する API が公開されていない
- [ ] 既存 pytest 全パス

### テスト例（ViewingEvent）

```python
# backward_skip: positionDelta < 0 を許容
ViewingEvent.create(
    action=ViewingAction.BACKWARD_SKIP,
    video_position=55,
    position_delta=-5,
    occurred_at=...,
)

# play: positionDelta == 0 のみ
with pytest.raises(ValueError):
    ViewingEvent.create(action=ViewingAction.PLAY, position_delta=-1, ...)
```

### スコープ外

- `LearningSnapshot`、Domain Service、Tutoring 側

---

## Phase 3: Learning Read Model と Domain Service

### What

- Read Model `LearningSnapshot` を実装（Entity ではない）
- Domain Service `LearningSnapshotBuilder` を実装
- 入力: `LearningSession` + `Lecture`、出力: `LearningSnapshot`
- Builder は LLM プロンプト文字列を**生成しない**

### 成果物

- `domain/learning/learning_snapshot.py`
- `domain/learning/services/learning_snapshot_builder.py`
- `tests/test_domain/test_learning/test_learning_snapshot_builder.py`

### 受入基準

- [ ] `LearningSnapshot` のスコープは 1 `LearningSession` のみ（型または docstring で明示）
- [ ] Builder 出力に `viewingEvents`, `latestQuizAttempt`, `quizAnswers` 相当が含まれる
- [ ] 複数 `QuizAttempt` があるとき `latestQuizAttempt` は最新（`attemptedAt` 基準）を返す
- [ ] 他 learner / 他 lecture のデータが混ざらないテストがある
- [ ] Builder はプロンプト文字列・JSON シリアライズを行わない
- [ ] 既存 pytest 全パス

### スコープ外

- 既存 `get_lad_data_for_participant` との接続（Mapper / Use Case 側）
- 字幕抜粋（`lectureTranscriptExcerpts`）の組み立て（SRT パースは interfaces / application 層）

---

## Phase 4: Tutoring 値オブジェクトとエンティティ

### What

- Tutoring コンテキストの VO `MessageRole` と Entity `TutorSession`, `Message` を実装
- `TutorSession.learningSessionId` は Shared Kernel の `LearningSessionId` を参照（Learning Entity は import しない）

### 成果物

- `domain/tutoring/message.py`
- `domain/tutoring/tutor_session.py`
- `tests/test_domain/test_tutoring/test_value_objects.py`
- `tests/test_domain/test_tutoring/test_entities.py`

### 受入基準

- [ ] `MessageRole` が `user` / `assistant` のみ
- [ ] `Message` は role + content の 1 発言モデル（user/assistant を 1 行にペアリングしない）
- [ ] `content` が空文字のとき拒否される
- [ ] `TutorSession` は `learningSessionId` のみで Learning を参照する（`LearningSession` Entity を import しない）
- [ ] `TutorSession` への `Message` 追記は集約ルート経由
- [ ] 既存 pytest 全パス

### スコープ外

- `NearTermExperimentPolicy`、LearningSnapshot との結合テスト（Phase 5）

---

## Phase 5: Tutoring Domain Service とコンテキスト境界テスト

### What

- Domain Service `NearTermExperimentPolicy` を実装（近い実験: 1 LearningSession に TutorSession 1 本まで）
- コンテキスト間 import ルールの自動テストを追加

### 成果物

- `domain/tutoring/services/near_term_experiment_policy.py`
- `tests/test_domain/test_tutoring/test_near_term_experiment_policy.py`
- `tests/test_domain/test_context_boundaries.py`

### 受入基準

- [ ] 既存 TutorSession がある状態で 2 本目の作成を `NearTermExperimentPolicy` が拒否する
- [ ] Policy は状態を持たない（入力: 既存 Session 一覧 + 新規要求 → 許可/拒否）
- [ ] `domain/tutoring/` から `domain/learning/` の Entity モジュール（`learning_session`, `viewing_event` 等）を import していないことをテストで検証
- [ ] Tutoring テストで `LearningSnapshot` の import のみが許可されていることを確認
- [ ] 既存 pytest 全パス

### スコープ外

- Repository 永続化、Flask `/chat` 接続

---

## Phase 6（任意）: ParticipantProgram と Research Export 境界

### What

- 長期研究向け Entity `ParticipantProgram` を Learning コンテキストに追加
- Research Export は引き続き Entity なし。パッケージ docstring で責務を明文化

### 成果物

- `domain/learning/participant_program.py`
- `domain/research_export/__init__.py`（docstring 更新）
- `tests/test_domain/test_learning/test_participant_program.py`

### 受入基準

- [ ] 同一 `(learnerId, programId)` の参加が 2 つ目で拒否される
- [ ] `LearningSession.participantProgramId` が optional で設定可能
- [ ] Research Export パッケージに Entity ファイルが存在しない
- [ ] 既存 pytest 全パス

### 備考

- 近い実験（1 講義のみ）では `ParticipantProgram` 未使用でよい

---

## AI への実装依頼テンプレート

各 Phase を依頼するときは以下をコピーして使用する。

```markdown
## 依頼

Phase N（ドメイン層）を実装してください。

### 参照仕様
- docs/spec/domain-model.md
- docs/spec/domain-implementation-plan.md の Phase N

### 制約
- ドメイン層のみ変更（Flask / db / application / infrastructure は触らない）
- 既存 pytest をすべてパスさせる
- Phase のスコープ外に手を伸ばさない
- コードに `# 仕様: docs/spec/domain-model.md#...` を付ける
- Tutoring が Learning Entity を直接 import しない

### 完了条件
- domain-implementation-plan.md Phase N の受入基準チェックリストをすべて満たす
```

---

## リスクと対策（ドメイン層）

| リスク | 対策 |
|--------|------|
| Tutoring と Learning の結合度が高くなる | `LearningSnapshot` のみを Published Language とし、import テストで強制 |
| ViewingEvent.positionDelta の符号ルール漏れ | Phase 2 専用テストファイルで action 別に網羅 |
| 集約ルートを迂回する API 公開 | Phase 2 で aggregate テストを必須化 |
| ドメイン層にインフラ依存が混入 | `test_context_boundaries.py` で禁止 import を検査（任意: import-linter 導入） |

---

## ドメイン層完了の受入基準

- [ ] [domain-model.md](./domain-model.md) の Entity / VO / 不変条件がコードとテストでカバーされている
- [ ] Learning / Tutoring / Shared Kernel / Research Export のパッケージ境界が識別できる
- [ ] `LearningSnapshotBuilder` が 1 Session スコープの Read Model を生成できる
- [ ] `NearTermExperimentPolicy` が TutorSession 1 本制約を表現できる
- [ ] ViewingEvent.positionDelta の負値が domain テストで検証されている
- [ ] ドメイン層に Flask / SQLite / vertexai の import がない
- [ ] `uv run pytest tests/ -v` が全パス

---

## 本計画完了後の次ステップ（参考・別計画）

ドメイン層完了後、以下は**別ドキュメント / 別 PR 系列**で進める。

1. Mapper（既存 DB ↔ ドメイン Entity）
2. Port / Repository 実装
3. Use Case（RecordViewingEvent, GetLearningSnapshot 等）
4. Flask ルート・Presenter 接続
5. DB スキーマ拡張（`learning_session_id`, `lecture_id`）
