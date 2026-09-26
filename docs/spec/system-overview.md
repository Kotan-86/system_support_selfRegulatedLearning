# システム概要仕様（アーキテクチャ構成図・データフロー図）

自己調整学習（SRL）支援システム。学習者が講義動画を視聴・小テストを受験し、その行動ログ（LAD）を見ながら AI チューターと振り返る。

本書は次の 2 要素のみを扱う。

- アーキテクチャ構成図
- データフロー図

## 1. アーキテクチャ構成図

クリーンアーキテクチャ 4 層 + 外部システム。依存は常に外側 → 内側（`domain` は何にも依存しない）。

```mermaid
flowchart TB
    subgraph Client["ブラウザ（Vanilla JS / HTML / ECharts）"]
        LP["/lecture<br/>player.js（YouTube IFrame）<br/>quiz.js"]
        RP["/reflect<br/>lad_panel.js（LAD）<br/>chat_panel.js（AI チャット）"]
    end

    subgraph FD["Framework & Drivers（framework_drivers/）"]
        direction TB
        PLAT["platform/<br/>main.py（Flask ルート）<br/>wiring.py（Composition Root）"]
        DBA["db/<br/>SqliteLearningSessionRepository<br/>SqliteTutorSessionRepository<br/>Mapper・StaticLectureCatalog"]
        EXT["external/<br/>vertex: VertexLlmGateway<br/>+ Student/Pedagogical/Interface Gateway<br/>youtube: VideoDurationResolver"]
    end

    subgraph IA["Interface Adapters（interfaces/）"]
        direction TB
        CTRL["Controllers<br/>RecordViewingEvent / RecordQuizAttempt<br/>GetLearningSnapshot / GetLastUpdated<br/>SendChatMessage"]
        PRES["Presenters → ViewModel<br/>LadDashboard / ChatResponse ほか"]
        PB["Prompt Builders<br/>Student / Pedagogical / Interface"]
        CLS["Learner Type Classifier<br/>（ルールベース）"]
    end

    subgraph APP["Application Business Rules（application/）"]
        direction TB
        UCL["Learning Use Cases<br/>StartOrGetLearningSession<br/>RecordViewingEvent<br/>RecordQuizAttempt<br/>GetLearningSnapshot"]
        UCT["Tutoring Use Cases<br/>StartOrGetTutorSession<br/>SendChatMessage<br/>RunTutoringPipeline<br/>（Student → Pedagogical → Interface）"]
        PORT["Ports<br/>Repository / LlmGateway<br/>Student・Pedagogical・InterfaceModelGateway<br/>LectureCatalog / LearningSnapshotQuery"]
    end

    subgraph DOM["Enterprise Business Rules（domain/）"]
        direction TB
        DL["learning: LearningSession / ViewingEvent<br/>QuizAttempt / Lecture / LearningSnapshot"]
        DT["tutoring: TutorSession / Message<br/>DialogueMove / DialogueMoveHistory<br/>InterpretationState / NearTermExperimentPolicy"]
        DS["shared: LearnerId / LectureId ほか ID"]
    end

    subgraph DATA["永続化（SQLite 2 ファイル）"]
        LDB[("learning.db<br/>learning_sessions<br/>viewing_logs<br/>quiz_attempts / answers")]
        TDB[("tutor.db<br/>sessions / messages<br/>（dialogue_move 等を保持）")]
    end

    subgraph CLOUD["外部サービス"]
        VTX["Vertex AI（Gemini）"]
        YT["YouTube Data API<br/>（動画長取得）"]
    end

    LP -- "HTTP JSON" --> PLAT
    RP -- "HTTP JSON" --> PLAT
    PLAT --> CTRL
    CTRL --> UCL
    CTRL --> UCT
    UCL --> DL
    UCT --> DL
    UCT --> DT
    CTRL --> PRES
    PRES --> CLS
    UCT -.Port.-> PORT
    UCL -.Port.-> PORT
    PORT -.実装.-> DBA
    PORT -.実装.-> EXT
    EXT --> PB
    DBA --> LDB
    DBA --> TDB
    EXT --> VTX
    EXT --> YT
    PLAT -. "DI 組み立て" .-> DBA
    PLAT -. "DI 組み立て" .-> EXT
```

### 構成要素の責務

| 層 | パス | 責務 |
| --- | --- | --- |
| Framework & Drivers | `framework_drivers/platform` | Flask ルート、HTML/静的 JS 配信、DI 組み立て（Flask を import してよい唯一の場所） |
| | `framework_drivers/db` | SQLite Repository・Mapper、講義カタログ・クイズ定義 |
| | `framework_drivers/external` | Vertex AI 呼び出し、YouTube 動画長取得 |
| Interface Adapters | `interfaces/` | 入力検証（ingress）、Controller、Presenter/ViewModel、LLM プロンプト構築、学習者タイプ分類 |
| Application | `application/` | Use Case と Port（抽象）定義。Result 型でエラーを返す |
| Domain | `domain/` | 集約・値オブジェクト・ドメインサービス（外部依存なし） |

### HTTP エンドポイント

| ルート | 種別 | 用途 |
| --- | --- | --- |
| `GET /lecture` | 画面 | 講義動画 + 小テスト |
| `GET /reflect` | 画面 | LAD + AI 振り返り |
| `POST /api/viewing-log` | Write | 視聴イベント記録 |
| `POST /api/quiz-attempts` | Write | 小テスト受験記録 |
| `GET /api/participants/<id>/lad` | Read | LAD ViewModel |
| `GET /api/last-updated` | Read | 学習データ最終更新時刻（ポーリング用） |
| `POST /chat` | Write/Read | AI チューター応答生成 |

## 2. データフロー図

### 2.1 全体データフロー（`participant_id` を共通キーとした Write / Read）

```mermaid
flowchart LR
    L(["学習者"])

    subgraph W["Write 経路（学習ログ記録）"]
        V["/lecture<br/>動画視聴・操作"]
        Q["小テスト回答"]
    end

    LDB[("learning.db")]
    TDB[("tutor.db")]
    SNAP["LearningSnapshot<br/>（GetLearningSnapshot）<br/>視聴イベント + 小テスト結果 + 講義情報"]

    subgraph R["Read 経路（振り返り）"]
        LAD["LAD 表示<br/>（円グラフ・区間別棒グラフ・<br/>クイズ結果・学習者タイプ）"]
        AI["AI チューター<br/>（3 段 LLM パイプライン）"]
    end

    L --> V
    L --> Q
    V -- "POST /api/viewing-log" --> LDB
    Q -- "POST /api/quiz-attempts" --> LDB
    LDB --> SNAP
    SNAP -- "GET /api/participants/id/lad" --> LAD
    SNAP -- "プロンプト文脈" --> AI
    LAD --> L
    L -- "POST /chat（発言）" --> AI
    AI -- "応答" --> L
    AI -- "発言・応答・Move・State Card 保存" --> TDB
    TDB -- "対話履歴・Move 履歴" --> AI
    YT["YouTube Data API"] -- "動画長（区間集計）" --> LAD
```

同一の `LearningSnapshot` を LAD と AI の双方が参照するため、学習直後に両者が同じ学習コンテキストを見る。

### 2.2 視聴ログ・小テスト記録（Write）

```mermaid
sequenceDiagram
    autonumber
    participant B as ブラウザ（player.js / quiz.js）
    participant F as Flask（main.py）
    participant C as Controller
    participant U as Use Case
    participant R as SqliteLearningSessionRepository
    participant D as learning.db

    B->>F: POST /api/viewing-log または /api/quiz-attempts（JSON）
    F->>C: execute(payload)
    C->>C: ingress 検証（participant_id → lecture_id 解決）
    C->>U: RecordViewingEvent / RecordQuizAttempt
    U->>U: StartOrGetLearningSession（無ければ新規作成）
    U->>R: save(LearningSession + 追記イベント/受験)
    R->>D: INSERT viewing_logs / quiz_attempts / answers
    U-->>C: Result
    C-->>F: Presenter → ViewModel
    F-->>B: JSON レスポンス
```

### 2.3 LAD 表示（Read・ポーリング）

```mermaid
sequenceDiagram
    autonumber
    participant B as ブラウザ（reflect_app.js / lad_panel.js）
    participant F as Flask
    participant C as GetLearningSnapshotController
    participant U as GetLearningSnapshotUseCase
    participant D as learning.db
    participant Y as YouTube Data API

    loop 定期ポーリング
        B->>F: GET /api/last-updated
        F-->>B: last_updated
    end
    Note over B: 更新検知時のみ再取得
    B->>F: GET /api/participants/{id}/lad
    F->>C: execute(participant_id)
    C->>U: 実行
    U->>D: LearningSession 取得
    U-->>C: LearningSnapshot
    C->>Y: 動画長を解決（キャッシュあり）
    C->>C: LadDashboardPresenter（区間集計・学習者タイプ分類）
    C-->>F: LadDashboardViewModel
    F-->>B: JSON → ECharts 描画
```

### 2.4 AI チューター応答生成（`POST /chat`）

```mermaid
sequenceDiagram
    autonumber
    participant B as ブラウザ（chat_panel.js）
    participant F as Flask
    participant S as SendChatMessageUseCase
    participant LD as learning.db
    participant TD as tutor.db
    participant P as RunTutoringPipeline
    participant G as Vertex AI（Gemini）

    B->>F: POST /chat（participant_id, message）
    F->>S: SendChatMessageController.execute
    S->>LD: StartOrGetLearningSession
    S->>TD: StartOrGetTutorSession（1 学習セッション = 1 対話セッション）
    S->>LD: LearningSnapshot 取得
    alt 初回かつ数字のみの発話
        S->>S: 定型応答（LLM 呼び出しなし）
    else 通常発話
        S->>P: snapshot + 対話履歴 + 発話 + 講義 + 前回 State Card
        P->>P: TurnContext 構築（ターン数・Move 履歴・LAD 提示済みか）
        P->>G: ① Student Model：学習者発話の解釈（発話タイプ・State Card）
        G-->>P: LearnerInterpretation
        P->>G: ② Pedagogical Model：Dialogue Move を選択
        G-->>P: DialogueMoveDecision
        P->>G: ③ Interface Model：応答文を生成
        G-->>P: assistant_text
        P-->>S: 応答 + interpretation + decision
    end
    S->>TD: save（user / assistant メッセージ + utterance_type・dialogue_move・state を追記）
    S-->>F: assistant_content
    F-->>B: JSON（ChatResponsePresenter）
```

## 3. データストア構成

| DB | 主なテーブル | 書き込み元 | 読み取り先 |
| --- | --- | --- | --- |
| `learning.db` | `learning_sessions`（learner × lecture で一意）、`viewing_logs`、`quiz_attempts`、`quiz_attempt_answers` | 視聴ログ API・小テスト API | LAD API、`/chat`（Snapshot 経由） |
| `tutor.db` | `sessions`（`learning_session_id` で紐づけ）、`messages`（`utterance_type` / `dialogue_move` / `interpretation_state` 付き） | `/chat` | `/chat`（対話履歴・Move 履歴・前回 State Card） |

パスは環境変数 `LEARNING_DB_PATH` / `TUTOR_DB_PATH` で上書き可能（既定は `db/data/`）。
