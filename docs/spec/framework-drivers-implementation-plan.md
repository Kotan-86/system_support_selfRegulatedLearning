# Framework & Drivers 層 実装計画

## 変更理由（Why）

- [framework-drivers-layer.md](./framework-drivers-layer.md) で `framework_drivers/`（platform / db / external）構成と Port 対応を確定した。次は **Adapter 実装 → platform 配線 → フロント配信** を PR 分割可能な順序で実装する
- interfaces 層（Phase 0〜6）は完了済み。本計画は **Framework & Drivers のみ**を対象とする
- 各 Phase は **Use Case を Fake なしで実 DB / 実 API から駆動**できる状態を目指す

## スコープ

### 本計画に含める

| 要素 | 説明 |
|------|------|
| `framework_drivers/db` | Port 具象（SQLite Repository、Mapper、IdGenerator、LectureCatalog） |
| `framework_drivers/external` | YouTube・Vertex AI Adapter |
| `framework_drivers/platform` | Composition Root、Flask ルート、templates / static |
| テスト | `tests/test_framework_drivers/`・`tests/test_api/` 更新 |

### 本計画に含めない

- domain / application / interfaces 層の仕様変更（必要時は別 PR）
- Google Form GAS の変更（`API_BASE_URL` 設定のみ運用）
- Research Export

### スキーマ変更について

- 目標スキーマは [framework-drivers-persistence.md](./framework-drivers-persistence.md) で **確定済み**
- **Phase 0** で [db/schema_learning.sql](../../db/schema_learning.sql)・[db/schema.sql](../../db/schema.sql) を更新する
- **実験開始後**は ADR どおりスキーマを変更しない

## 前提・依存

- 仕様: [framework-drivers-layer.md](./framework-drivers-layer.md)
- interfaces: [interfaces-layer.md](./interfaces-layer.md)（Controller / ViewModel 完了）
- application: [application-usecase.md](./application-usecase.md)
- ADR: [ADR_SSSRL-backend_2026-02-23.md](../../Arcitecture/ADR_SSSRL-backend_2026-02-23.md)
- 既存 DB スキーマ: [db/schema_learning.sql](../../db/schema_learning.sql)、[db/schema.sql](../../db/schema.sql)
- テスト: `uv run pytest tests/ -v`

## 目標ディレクトリ構成

```
framework_drivers/
  platform/
    main.py                    # Phase 4: app/main.py から移行
    wiring.py                  # Composition Root
    templates/
      lecture.html
      reflect.html
    static/
      css/
        reflect.css
      js/
        common/
          participant_context.js
          api_client.js
        lecture/
          player.js
        reflect/
          lad_panel.js
          chat_panel.js
          reflect_app.js
  db/
    learning/
      sqlite_learning_session_repository.py
      sqlite_learning_session_mapper.py
      static_lecture_catalog.py
      id_generators.py
    tutoring/
      sqlite_tutor_session_repository.py
      id_generators.py
  external/
    youtube/                   # 既存
      youtube_video_duration_resolver.py
      youtube_duration_cache.py
      youtube_video_id.py
    vertex/                    # Phase 3
      vertex_llm_gateway.py

app/                           # 移行期間のみ。Phase 4 完了後に platform へ統合
  main.py

db/                            # 移行期間のみ。Phase 1〜4 で framework_drivers/db へ移行

tests/
  test_framework_drivers/
  test_api/
```

---

## Phase 一覧

| Phase | 内容 | 主なパス | 完了判定の要点 |
|-------|------|----------|----------------|
| 0 | 骨格・Mapper 設計 | `framework_drivers/db/` | 集約 ↔ テーブル mapping 確定・DDL 反映 |
| 1 | Learning Write | `framework_drivers/db/learning/` | 視聴・小テストが DB 経由で UC 駆動 |
| 2 | Learning Read | `db/learning` + platform 配線準備 | LAD API が新 ViewModel を返す |
| 3 | Tutoring | `db/tutoring` + `external/vertex` | `/chat` が UC + Vertex 駆動 |
| 4 | platform 配線 | `framework_drivers/platform/` | 全 API が Controller 経由 |
| 5 | 講義動画フロント | `platform/templates` + `static/js/lecture` | `/lecture` からログ POST |
| 6 | LAD+AI フロント | `platform/static/js/reflect` | `/reflect` ECharts + Chat |

---

## Phase 0: Mapper 設計・骨格

### 目的

[framework-drivers-persistence.md](./framework-drivers-persistence.md) の目標スキーマに沿い、`LearningSession` 集約と SQLite 行の対応を確定する。

### 成果物

- `framework_drivers/db/learning/sqlite_learning_session_mapper.py`（設計・テスト）
- [db/schema_learning.sql](../../db/schema_learning.sql)・[db/schema.sql](../../db/schema.sql) の更新（`learning_session_id` 列含む）

### 対応方針（What）

| 集約 | テーブル |
|------|----------|
| `LearningSession` | `learning_sessions` |
| `ViewingEvent` 列 | `viewing_logs`（`learning_session_id` FK） |
| `QuizAttempt` + `QuizAnswer` 列 | `quiz_attempts` + `quiz_attempt_answers` |

ID 方針は [framework-drivers-persistence.md#決定事項](./framework-drivers-persistence.md#決定事項) を参照。

### 受入基準

- [x] [framework-drivers-persistence.md](./framework-drivers-persistence.md) の決定事項 #1〜#7 が記載されている
- [ ] `db/schema_learning.sql` が目標スキーマで `tests/test_data_foundation/test_learning_schema.py` が通る
- [ ] 既存 `viewing_logs` 1 行が `ViewingEvent` に変換できる
- [ ] `RecordViewingEventUseCase` + Fake なし IT の骨格テストが存在する

---

## Phase 1: Learning Write（`framework_drivers/db`）

### 目的

`POST /api/viewing-log`・`POST /api/quiz-attempts` を Use Case 経由で永続化する。

### 成果物

- `SqliteLearningSessionRepository`
- `LearningSessionIdGenerator`（UUID）。`ViewingEventId` / `QuizAttemptId` は INSERT 後 `str(lastrowid)`（[persistence 仕様](./framework-drivers-persistence.md#id-生成mapper--repository)）
- `StaticLectureCatalog`（近い実験 1 講義）
- `db/schema.sql` の `sessions.learning_session_id` を Repository 書き込みで利用（Tutor Phase 3 まで待たない）

### 受入基準

- [ ] `RecordViewingEventUseCase` が SQLite Repository で緑
- [ ] `RecordQuizAttemptUseCase` が SQLite Repository で緑
- [ ] GAS 契約テスト（`test_viewing_log_gas_contract.py`）が通る
- [ ] 小テスト GAS 契約テストが通る

---

## Phase 2: Learning Read

### 目的

`GET /api/participants/{id}/lad` が `LadDashboardViewModel` を返す。

### 成果物

- `GetLearningSnapshotController` + Presenter の IT（Repository 実装使用）
- `VideoDurationResolver` 本番配線（`framework_drivers/external/youtube`）
- `test_lad_api.py` を **新 ViewModel キー**に更新

### 受入基準

- [ ] 空 Snapshot で 200 + 空 ViewModel（404 にしない）
- [ ] `action_counts` / `video_segments` / `quiz_results` / `learner_profile` / `content_updated_at` が JSON に含まれる
- [ ] 旧 `viewing_logs` 生 dict は返さない

---

## Phase 3: Tutoring（`db/tutoring` + `external/vertex`）

### 目的

`POST /chat` を `SendChatMessageUseCase` + Vertex で駆動する。

### 成果物

- `SqliteTutorSessionRepository`（旧 `db/repository.py` から移行）
- `VertexLlmGateway`（`app/main.py` の `_call_llm` 移行）

### 受入基準

- [ ] `SendChatMessageUseCase` + SQLite + Fake LLM で緑
- [ ] 応答生成前に `LearningSnapshotQuery` が呼ばれる
- [ ] `tests/test_chat_lad/` が新 Repository 経路で通る

---

## Phase 4: platform 配線

### 目的

`app/main.py` を `framework_drivers/platform/` に移行し、Controller 呼び出しに置換する。

### 成果物

- `framework_drivers/platform/wiring.py`
- `framework_drivers/platform/main.py`（Flask app factory またはエントリ）
- 全 JSON API ルート
- `ErrorViewModel` → HTTP ステータス変換
- ViewModel の `datetime` JSON シリアライズ

### 受入基準

- [ ] `app/main.py` およびルート `db/` を import しない（または thin re-export のみ）
- [ ] 全 API 契約テスト（`tests/test_api/`）が通る
- [ ] interfaces 層テストは引き続き Flask 非依存

---

## Phase 5: 講義動画フロント（`platform`）

### 目的

GAS ホスティングを Flask `/lecture` に置き換える。

### 成果物

- `framework_drivers/platform/templates/lecture.html` + `static/js/lecture/player.js`
- `participant_id` URL 必須
- 同一オリジン `POST /api/viewing-log`

### 受入基準

- [ ] `?participant_id=` なしでエラーまたは入力促し
- [ ] play / pause / skip / seek で 201 が返る
- [ ] payload 形状が GAS 契約と同一

---

## Phase 6: LAD + AI 統合フロント（`platform`）

### 目的

Looker 代替の `/reflect` を提供する。

### 成果物

- `reflect.html`（2 カラム: LAD | Chat）
- `lad_panel.js`（ECharts 円・棒 + 表 + 固定文）
- `chat_panel.js`（旧 `index.html` 移植、`participant_id` URL 前提）
- `reflect_app.js`（`content_updated_at` ポーリング）

### 受入基準

- [ ] LAD 4 表示ブロックが ViewModel と 1:1
- [ ] チャット初回 ID 入力プロンプトなし
- [ ] 小テスト Write 後、ポーリングで LAD が更新される
- [ ] `/` が `/reflect` または統合画面に到達できる

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| ルート `db/` と `framework_drivers/db/` 二重保守 | Phase 4 完了をもって旧 import 削除 |
| SQLite 書き込み競合 | gunicorn ワーカー数制限 |
| YouTube API 障害 | `external/youtube` キャッシュ + 設定値 fallback |
| LAD 旧 JSON 依存 | Phase 2 で契約テストを新 ViewModel に切替 |

---

## 受入基準（本計画全体）

- [ ] Phase 0〜6 が順に完了し、各 Phase の受入基準を満たす
- [ ] Looker 手動 CSV なしで LAD 表示が `/reflect` から可能
- [ ] 視聴ログ・小テスト・LAD・AI が同一 `participant_id` で連携する
- [ ] [framework-drivers-layer.md](./framework-drivers-layer.md) の Port 対応表がすべて `framework_drivers/` 配下に実装されている
