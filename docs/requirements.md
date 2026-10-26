# システム要件(機能要件・非機能要件)

自己調整学習支援システム(SSSRL)の要件を、機能要件と非機能要件に分けて整理する。

- 作成日: 2026-10-21
- 位置づけ: 既存の仕様・README・プロダクトゴールから**要件を横断的に整理した一覧**。個々の受入基準(AC)は各仕様が正であり、本書は新しい決定を含まない。
- 状態: **PO未承認の整理案**。`(要確認)` は、既存の記述から読み取れない、または推測を含む項目。
- 2026-10-21 追記: PO から、本番運用(2026-10-27 実験開始)に向けた追加要件を受領した(§6)。該当する要件には「【追加】」を付けた。

## 1. 目的とスコープ

[プロダクトゴール](./product-goal.md): 講義を受ける学習者が、自分の学習行動(LAD)を見ながらAIチューターと対話することで、自分の学習を振り返り、次の行動を計画できるようになる。その効果を、研究協力者を通じて検証できる状態にする。

| 項目 | 内容 |
|---|---|
| 主な利用者 | 研究協力者(学習者) |
| 副次的な利用者 | 研究者(対話ログの取得) |
| 実験の規模 | 3講義 × 1学習者(`participant_id` 1/2/3 が `lecture-1/2/3` に対応)。2026-10-26 時点で、ログイン ID は `P01`〜`P31`(協力者は30人以下、登録は研究者確認用 `P01` を含め31件以下)で、講義割当は固定マップのまま(`P01`〜`P31` は `lecture-1`。講義を選ぶ仕組みは別 Issue)([participant-login](./spec/participant-login.md)) |
| 実験の開始 | 2026-10-27(予定)。デプロイ作業は 10/26(月)9:00-10:00 |
| スコープ外 | 管理画面 |
| 2026-10-21 時点で変更 | 参加者ログイン、DB の永続化は、スコープに入った(§6) |

## 2. 機能要件

IDは本書内の通し番号。根拠欄は、詳細を定める既存ドキュメント。

### 2.1 講義視聴・学習ログ記録(`/lecture`)

| ID | 要件 | 根拠 |
|---|---|---|
| FR-01 | 学習者は、講義動画(YouTube)を視聴できる | [system-overview](./spec/system-overview.md) |
| FR-02 | 視聴中の操作(再生・停止・シークなど)を、視聴イベントとして記録する(`POST /api/viewing-log`) | [system-overview](./spec/system-overview.md) |
| FR-03 | 学習者は、講義に紐づく小テストを受験でき、回答を受験記録として保存する(`POST /api/quiz-attempts`) | [system-overview](./spec/system-overview.md) |
| FR-04 | 学習データは、学習者 × 講義 を単位とする学習セッションに集約する(無ければ新規作成) | [domain-model](./spec/domain-model.md) |
| FR-05 | `participant_id` から講義を自動解決する(1/2/3 → `lecture-1/2/3`、それ以外は `lecture-1`)。**【追加】FR-60 で、協力者が自分で選ぶ方式に置き換える** | [interfaces-layer](./spec/interfaces-layer.md) |

### 2.2 学習行動の可視化(LAD。`/reflect`)

| ID | 要件 | 根拠 |
|---|---|---|
| FR-10 | 視聴イベントと小テスト結果から LAD(学習行動ダッシュボード)を表示する。表示ブロックは4つ(操作集計・動画2分区間集計・小テスト結果(問題文付き)・学習者プロファイル) | [interfaces-layer](./spec/interfaces-layer.md) |
| FR-11 | 動画を2分の区間に分けて、区間別の視聴状況をグラフで表示する(動画長はYouTube Data APIで解決) | [interfaces-layer](./spec/interfaces-layer.md) |
| FR-12 | 視聴行動の指標から、ルールベースで学習者タイプを判定して表示する | [interfaces-layer](./spec/interfaces-layer.md) |
| FR-13 | 学習データの更新を検知して、LAD を再取得する(`GET /api/last-updated` のポーリング) | [system-overview](./spec/system-overview.md) |
| FR-14 | 10分を超える動画の区間集計が正しく行われる | [bugs/lad-video-segments-over-10min](./spec/bugs/lad-video-segments-over-10min.md) |
| FR-15 | シークによる視聴時間の重複計上をしない | [bugs/seek-duplicate-count](./spec/bugs/seek-duplicate-count.md) |

### 2.3 AIチューターとの対話(`/reflect`)

| ID | 要件 | 根拠 |
|---|---|---|
| FR-20 | 学習者はチャットでAIチューターに発言し、応答を受け取れる(`POST /chat`) | [system-overview](./spec/system-overview.md) |
| FR-21 | 応答は、同じ `LearningSnapshot`(LADと同一の学習コンテキスト)・対話履歴・直前の状態をもとに生成する | [system-overview](./spec/system-overview.md) |
| FR-22 | 応答生成は3段のLLMパイプライン(学習者の発話の解釈 → 対話方針(Dialogue Move)の選択 → 応答文の生成)で行う | [system-overview](./spec/system-overview.md) |
| FR-23 | 1学習セッション = 1対話セッション。再訪時は既存の対話セッションに追記する | [dialog-log-save](./spec/dialog-log-save.md) |
| FR-24 | 初回かつ数字のみの発話には、LLMを呼ばず定型応答を返す | [system-overview](./spec/system-overview.md) |
| FR-25 | 1往復ごとに、発言と応答(発話タイプ・Move・解釈状態・応答時刻を含む)を保存する | [system-overview](./spec/system-overview.md) |
| FR-26 | チャット欄で複数行の入力ができる | [reflect-chat-multiline-input](./spec/reflect-chat-multiline-input.md) |

### 2.4 対話ログの保存

| ID | 要件 | 根拠 |
|---|---|---|
| FR-30 | 「対話ログを送信して終了する」操作で、対話ログ(JSON。AI/ユーザーのロール別、時系列)を DB に保存する(`POST /api/dialog-log`) | [dialog-log-save](./spec/dialog-log-save.md) |
| FR-31 | 保存の成功・失敗を画面に表示し、失敗時は再試行できる | [dialog-log-save](./spec/dialog-log-save.md) |
| FR-32 | 終了操作をせずにブラウザを閉じようとしたとき、確認ダイアログで引き留める(文言はブラウザ標準) | [dialog-log-save](./spec/dialog-log-save.md) |
| FR-33 | 発言済みで離脱が確定したとき、保存を試みる(完了はブラウザの制約により保証しない) | [dialog-log-save](./spec/dialog-log-save.md) |

### 2.5 研究者向けの対話ログ取得

| ID | 要件 | 根拠 |
|---|---|---|
| FR-40 | 研究者は、参加者別に対話ログを JSON でダウンロードできる(`GET /research/participants/<参加者ID>/dialog-logs`) | [research-dialog-download](./spec/research-dialog-download.md) |
| FR-41 | 研究者は、全参加者分を一括でダウンロードできる(`GET /research/dialog-logs`) | 同上 |
| FR-42 | JSON は対話セッション1回 = 1まとまり。参加者ID・セッションID・講義ID・各発話の時刻/ロール/本文を時系列で含む。並び順は 参加者ID昇順 → セッション作成時刻昇順 → セッションID昇順 | 同上 |
| FR-43 | 対象データがないときは、空のリストで 200 を返す | 同上 |
| FR-44 | 専用の管理画面は作らず、URL を開くだけで取得できる(ブラウザ標準の認証入力欄、curl) | 同上 |

### 2.6 【追加】認証・アクセス制御

| ID | 要件 | 根拠 |
|---|---|---|
| FR-50 | 研究協力者は、研究者が発行した ID/パスワードでログインできる(PO決定、2026-10-21)。ログアウトもできる。ログイン済みの `/` とログイン画面は `/lecture` へ移る | [participant-login](./spec/participant-login.md) 「1. ログインとログアウト」(AC1〜6、24、27。PO承認 2026-10-26。実装済み・統合検証合格) |
| FR-51 | ログインしていない要求は、画面も API も拒否する(画面は 302 でログイン画面へ、API は 401)。URL を直接叩いても、他人の学習ログ・対話を読み書きできない | [participant-login](./spec/participant-login.md) 「2. 未ログインの要求の拒否」(AC7〜10。同上) |
| FR-52 | 参加者は、ログインしたセッションから特定する。URL のクエリ・要求本文の `participant_id` は信用しない(省略可。ログイン ID と異なれば 403、型が不正なら 400。画面のクエリは無視。他人の対話セッションは 404) | [participant-login](./spec/participant-login.md) 「3. 参加者の特定」(AC11〜16、25、30。PO決定 論点2・10=案B、2026-10-26。同上) |
| FR-53 | 研究者用ダウンロード(FR-40、41)の認証(Basic 認証)は現状維持。参加者のログインとは別系統(`/research/*` は参加者のログインを要求せず、受け付けもしない) | [participant-login](./spec/participant-login.md) 「範囲外」(AC10)、[research-dialog-download](./spec/research-dialog-download.md)(PO決定 2026-10-26) |
| FR-54 | 研究者が、協力者用の ID/パスワードを発行する手段として、作成スクリプトを用意する。ID は `P01`〜`P31` を順に払い出す(登録は31件まで。協力者30人以下+研究者確認用 `P01`)。再発行・停止ができ、資格情報の正はハッシュ入りの設定ファイル(Secret Manager で本番へ渡し、再デプロイで反映)。講義割当は設定ファイルに持たない(協力者が講義を選ぶ仕組みは別 Issue) | [participant-login](./spec/participant-login.md) 「5. ID/パスワードの登録」(AC17〜19、26、28、29。PO決定 論点1・3・4・11・12・14、2026-10-26。同上) |

### 2.7 【追加】コンテンツ選択

| ID | 要件 | 根拠 |
|---|---|---|
| FR-60 | 協力者は、6本(理系レベル3 + 文系レベル3)の学習コンテンツから、自分で選べる(PO決定、2026-10-21) | PO |
| FR-61 | 文系レベルの動画・小テスト・講義情報(・SRT)は、PO が用意する。理系レベル3本は準備済み | PO |
| FR-62 | 選んだコンテンツに応じて、LAD・AIチューター・対話ログの講義IDが一貫する | PO(意図の読み取り) |
| FR-63 | 協力者が選べる回数・変更の可否`(要確認)` | — |

### 2.8 【追加】字幕

| ID | 要件 | 根拠 |
|---|---|---|
| FR-70 | 動画の下に、修正済みの SRT を再生位置に同期して表示する | PO決定(2026-10-21) |
| FR-71 | 字幕の表示/非表示を切り替えられる。切替操作はログに記録せず、LAD に影響させない | PO決定 |
| FR-72 | SRT の誤字脱字を修正する。AI が全文の修正案を作り、PO が前後の差分を確認して確定する。SRT は AI チューターのプロンプトにも使われるため、AI 応答の質にも効く | PO決定 |
| FR-73 | 自動字幕の時刻の重なり(行の二重表示)を、表示前に整理する方針を決める `(要確認)` | 観測(`lectures/*/subtitles.srt`) |

## 3. 非機能要件

### 3.1 セキュリティ・プライバシー

| ID | 要件 | 根拠 |
|---|---|---|
| NFR-01 | 研究用ダウンロードは、研究者共有の1組の資格情報による HTTP Basic 認証でのみ許可する。資格情報が無い・誤り・サーバー未設定のときは、すべて 401 とし、対話内容を返さない(設定の有無を外から区別させない) | [research-dialog-download](./spec/research-dialog-download.md) |
| NFR-02 | 資格情報は環境変数で与え、リポジトリ・イメージに含めない。Vertex認証情報(`secrets/`)もイメージに含めない | README |
| NFR-03 | 研究用ダウンロードの応答をキャッシュさせない。本文をサーバーのログに出さない。取得の記録は残さず、DBに何も書かない | [research-dialog-download](./spec/research-dialog-download.md) |
| NFR-04 | 対話の本文は研究協力者の発言であり、研究者以外が取得できないこと | 同上 |
| NFR-05 | ~~参加者の画面とAPIは、現状どおり認証なしで使える~~ → **【変更】FR-50、51 のとおり、ログインを必須にする**(基本的なセキュリティを搭載する、PO意図)。セッション Cookie は `HttpOnly`・`SameSite=Lax`・既定で `Secure`、ログインの有効期限は12時間、`SECRET_KEY` 必須 | [participant-login](./spec/participant-login.md) 「6. セッションの安全性の設定」(AC20〜22。PO承認 2026-10-26) |
| NFR-08 | 【追加】他人の学習ログ・対話ログの閲覧・書き込みを防ぐ(情報漏洩の防止)。パスワードは平文で保存しない(ハッシュで設定ファイルに保存。設定ファイル・DB・Cookie に平文を含めない) | PO、[participant-login](./spec/participant-login.md)(AC12、13、15、17、21。PO承認 2026-10-26。実装済み・統合検証合格) |
| NFR-06 | 平文のHTTPでは資格情報が暗号化されない。本番ではHTTPSを前提とする(Cloud Runは標準でHTTPS) | README |
| NFR-07 | 研究協力者の同意・個人情報の取り扱いは、倫理審査に提出済み(PO、2026-10-21)。システムは、審査で承認された内容に従う。審査の結果・条件のうち、システムに影響するもの(同意の取得方法、収集項目、保存期間、削除対応など)は、承認後に要件へ反映する `(審査結果を待つ)` | PO |

### 3.2 データの信頼性・保全

| ID | 要件 | 根拠 |
|---|---|---|
| NFR-10 | 対話ログは研究データであり、保存の取りこぼしを最小化する(ボタン、離脱時の確認、離脱時の保存の三重化) | [dialog-log-save](./spec/dialog-log-save.md) |
| NFR-11 | 保存先は SQLite 2ファイル(`learning.db`、`tutor.db`)。パスは `LEARNING_DB_PATH` / `TUTOR_DB_PATH` で変更可能 | [system-overview](./spec/system-overview.md) |
| NFR-12 | 実験開始後は、学習データ用DBのスキーマを変更しない | ADR |
| NFR-13 | 既存DBに対して、「なければ作る」方式のスキーマ適用で動作を壊さない(変更前DBへの対応) | [dialog-log-save](./spec/dialog-log-save.md) |
| NFR-14 | **【変更】** Cloud Run のコンテナ内SQLiteは、再デプロイ・再起動で消える。**本スコープで永続化する**(PO決定、2026-10-21)。**方式は決定済み**(#28、2026-10-26): Litestream で2つのSQLiteをGCSへ継続複製し、起動時に復元する(Cloud Run は `--max-instances=1`)。README と framework-drivers-layer の食い違いは #29 で解消した | [db-persistence](./spec/db-persistence.md), README, [dialog-log-save](./spec/dialog-log-save.md) |
| NFR-16 | 【追加】スキーマの変更(ユーザー、コンテンツ選択ほか)は、実験開始(10/27)の前に確定する(ADR: 実験開始後は学習データ用DBのスキーマを変更しない) | ADR |
| NFR-15 | 全参加者の学習セッション・対話セッションは、`participant_id` を共通キーとして一貫してたどれる | [system-overview](./spec/system-overview.md) |

### 3.3 保守性・設計

| ID | 要件 | 根拠 |
|---|---|---|
| NFR-20 | クリーンアーキテクチャ4層(domain / application / interfaces / framework_drivers)を守る。依存は外側から内側へ。`domain` は外部に依存しない | [system-overview](./spec/system-overview.md) |
| NFR-21 | Flask を import してよいのは `framework_drivers/platform` のみ | 同上 |
| NFR-22 | Use Case はエラーを `Result` / `AppError` で返し、HTTPステータスへの変換は外側が担う | [application-error-handling](./spec/application-error-handling.md) |
| NFR-23 | LLM・DB・YouTube は Port を介して差し替え可能にする | [application-usecase](./spec/application-usecase.md) |
| NFR-24 | AIによる段階的実装を可能にするため、仕様・実装計画をドキュメントとして維持する | [README](./README.md) |
| NFR-25 | 用語対応(Learner = participant 等)を統一する | [README](./README.md) |

### 3.4 テスト容易性・品質

| ID | 要件 | 根拠 |
|---|---|---|
| NFR-30 | 自動テストは `uv run pytest tests/ -v`。通常のテストは外部サービスに接続しない(偽のLLM等) | CLAUDE.md |
| NFR-31 | 実際のLLM呼び出しを伴うテストは `-m real_llm` で分離し、認証が必要 | CLAUDE.md |
| NFR-32 | UI操作を含む受入は、PO(人間)が確認する | CLAUDE.md |

### 3.5 外部サービス・可用性

| ID | 要件 | 根拠 |
|---|---|---|
| NFR-40 | AI応答は Vertex AI(Gemini)に依存する。応答生成が失敗した場合は、エラーを画面に表示する(失敗した往復は保存されない) | [dialog-log-save](./spec/dialog-log-save.md) |
| NFR-41 | LAD の動画長取得は YouTube Data API(`YOUTUBE_API_KEY`)に依存する。結果はキャッシュする | [interfaces-layer](./spec/interfaces-layer.md) |
| NFR-42 | LAD 更新はポーリング方式で検知し、更新があったときだけ再取得する(通信量の抑制) | [system-overview](./spec/system-overview.md) |
| NFR-43 | 【変更】協力者は30人以下(募集の上限、PO決定 2026-10-21。登録は研究者確認用1件を含め31件以下、PO決定 2026-10-26)。同時利用はさらに少数。高負荷・高可用性は要件としない。Gemini API の料金は研究室が負担し、設計の制約にしない | [product-goal](./product-goal.md) |
| NFR-45 | 【追加】成功指標(有効10人以上を12月末までに確認)を判定できること。有効の条件(視聴・小テスト・1往復以上の対話)を、データから人ごとに集計できる | [product-goal](./product-goal.md) |
| NFR-44 | AI応答の許容時間(応答遅延の目標値)`(要確認)` | — |

### 3.6 運用・可搬性

| ID | 要件 | 根拠 |
|---|---|---|
| NFR-50 | ローカルは `uv` と Flask で起動できる。Cloud Run へコンテナでデプロイできる。**【追加】デプロイ先は、研究室(watalab)の Google アカウントの Google Cloud Run。Gemini API の料金請求も、そのアカウント宛にする(認証情報の連携が必要。10/26(月)9:00-10:00 に作業)** | README, PO |
| NFR-51 | 設定は環境変数で与える(`VERTEX_PROJECT_ID`、`VERTEX_LOCATION`、`VERTEX_MODEL_NAME`、`YOUTUBE_API_KEY`、`GOOGLE_APPLICATION_CREDENTIALS`、DBパス、複製先バケット `DB_REPLICA_BUCKET`、複製しない指定 `DB_REPLICA_DISABLED`(ローカル用。`1` のときだけ有効)) | README, [db-persistence](./spec/db-persistence.md) |
| NFR-52 | 対応ブラウザ・画面サイズ`(要確認)`。ブラウザの離脱イベントの挙動差(Safariの戻る/進むでの復元など)に留意する | [dialog-log-save](./spec/dialog-log-save.md) |
| NFR-53 | 画面は Vanilla JS / HTML / ECharts で構成する(フレームワークを増やさない) | [system-overview](./spec/system-overview.md) |

## 4. 未確定・要確認の項目

| # | 論点 | 関連 |
|---|---|---|
| 1 | ~~成功指標が未定~~ → 2026-10-21 に決定(有効10人以上を12月末までに確認、上限30人)。「視聴した」は、1回の再生から有効(PO決定、2026-10-21) | [product-goal](./product-goal.md) |
| 2 | ~~実験の実施環境~~ → Cloud Run(研究室アカウント)、開始 10/27 に決定。協力者の人数・同時利用・実験期間は未確認 | NFR-14, 50 |
| 3 | ~~永続ストレージの方式~~ → 2026-10-26 に決定(#28): Litestream による GCS への継続複製。仕様は #29 | NFR-14, [db-persistence](./spec/db-persistence.md) |
| 4 | ~~ID/パスワードの発行・配布の方法、研究者用 Basic 認証との関係~~ → 2026-10-26 に決定(作成スクリプト+設定ファイル方式、ID は `P01`〜`P31`(登録31件=協力者30+研究者確認用1。#31 で変更)、Basic 認証は現状維持。パスワードはスクリプトが生成して1回だけ端末に表示し、研究者が協力者へ配布する) | FR-53, 54、[participant-login](./spec/participant-login.md) |
| 7 | 10/26 までの範囲。入りきらないものの暫定運用(例: 字幕UI・文系3本は後追い) | §6 |
| 8 | 字幕の時刻重なりの整理方針 | FR-73 |
| 5 | 倫理審査は提出済み。審査の結果・条件(同意取得の方法、収集項目、保存期間など)で、システムに影響するものがないか。10/27 の開始前に承認が下りるか | NFR-07 |
| 6 | 性能目標(AI応答時間、同時利用者数)と対応ブラウザ | NFR-43, 44, 52 |

## 6. 【追加】2026-10-21 の追加要件の背景(PO との対話から)

- **目的**: 2026-10-27 から、研究協力者に実験を始めてもらえる本番の状態にする。
- **背景**: 現状はプロトタイプで、(1) データが再デプロイで消える、(2) `participant_id` を知っていれば誰でも API を叩ける、(3) 学習内容が固定、の3点が本番に足りない。情報漏洩のニュースを受け、基本的なセキュリティも搭載したい。
- **理系/文系**: 理系レベルと文系レベルの学習コンテンツを3本ずつ(計6本)用意し、協力者が選ぶ。文系は PO が準備する。
- **PO の決定**: ログインは ID/パスワード(研究者が発行)。コンテンツは協力者が6本から選ぶ。10/26 までに、ログイン・ガード・永続化・コンテンツ選択を終わらせたい。字幕は AI 校正案 → PO 確認、動画下に同期表示、切替可、記録しない。
- **スケジュール上の懸念**: 開発の PBI が4本(認証・ガード、永続化、コンテンツ選択、字幕UI)あり、5日間で全部は厳しい。入りきらない分の暫定運用は、PO が決める。

## 7. 補足

- 本書は、`docs/` 配下の既存仕様(system-overview、interfaces-layer、dialog-log-save、research-dialog-download ほか)と README から抽出した。会話の履歴ではなく、リポジトリの記述を根拠にしている。
- 機能要件の詳細な受入基準は各仕様を参照。本書と食い違うときは、各仕様を正とする。
