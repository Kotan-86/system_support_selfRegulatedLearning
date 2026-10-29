# 研究用の視聴ログ・小テストの CSV ダウンロード — 研究者だけが、LAD の元になる記録(生ログ)を、参加者別・全員一括で CSV で取得できる

## Issue

#55(https://github.com/Kotan-86/system_support_selfRegulatedLearning/issues/55)。作成日 2026-10-29。

## 目的(Why)

LAD に示される学習行動(視聴ログ・小テストの結果)は、対話ログと並ぶ本研究の分析対象である(プロダクトゴール: 研究協力者を通じて効果を検証できる状態にする。「有効な1人分」の条件のうち、視聴と小テストの受験は、この記録でしか確かめられない)。対話ログは #25 で研究者が取得できるようになったが、視聴ログと小テストは `learning.db` にあるだけで、研究者が取り出す手段がない。

LAD は集計(操作6種の回数、120秒区間、最新1回の小テスト)しか見せないため、分析には元の記録が要る。研究者が表計算ソフトや統計ソフトでそのまま開けるよう、CSV で取得できるようにする。記録は研究協力者の行動そのものであり、研究者以外が取得できてはならない点は、対話ログと同じである。

## 前提

### 実装の現状(コードの観測事実)

確認の方法: 「実行」は、一時ディレクトリの DB に対し、テスト用の設定でアプリを起動し、Flask のテストクライアントで API を呼んで DB の行を表示した(2026-10-29。プロダクトのファイルと DB は変更していない)。

- 記録の表は `learning.db` の4つ: `learning_sessions`(id、`learner_id` = 参加者ID、`lecture_id`、`started_at`。`(learner_id, lecture_id)` で一意)、`viewing_logs`(id、`learning_session_id`、`time_stamp`、`current_time` = 動画内の位置(整数の秒)、`action`、`duration`)、`quiz_attempts`(id、`learning_session_id`、`created_at`、`score_numerator`、`score_denominator`)、`quiz_attempt_answers`(id、`attempt_id`、`question_index`(1始まり)、`selected_answer`、`is_correct`(0/1))。〔確認: 読み取りのみ(`db/schema_learning.sql`)。下の実行で行の形を確認〕
- 1人の参加者は、講義ごとに1つの学習セッションを持つ(複数の講義を選べば複数)。〔確認: 読み取りのみ(一意制約)(未確認: コードを読んだ推測)〕
- 時刻は、端末が送った値の時差(オフセット)のまま保存される。`+09:00` を付けて送れば `+09:00` のまま、時差なしで送れば時差なしのまま、`Z` は `+00:00` になり、秒未満は捨てられる。小テストの受験の時刻(`created_at`)も同じ。〔確認: 実行(`2026-10-29T10:00:00+09:00` → そのまま、`2026-10-29T01:00:00` → そのまま、`2026-10-29T01:00:00.123Z` → `2026-10-29T01:00:00+00:00`)〕
- 画面(講義画面)は、時刻を UTC(`toISOString`)で送る。したがって、画面からの記録は `+00:00` になる。上の他の形は、API を直接呼んだ場合にだけ入りうる。〔確認: 読み取りのみ(`static/js/common/api_client.js`)(未確認: コードを読んだ推測)〕
- `duration` は、書き込みのときに0の方向へ切り捨てた整数の値が、小数の型で保存される(`-12.7` を送ると `-12.0`、`10` を送ると `10.0`)。後ろ向きの操作は負の値。〔確認: 実行〕
- 視聴ログの `action` は6種の列挙に限られ、参加者IDはログインした ID、講義IDは選択した講義から決まる。したがって、視聴ログの CSV に出る文字列の列に、カンマ・二重引用符・改行や `=` などで始まる値は、API からは入らない(DB に直接置いた場合だけ)。〔確認: 読み取りのみ(`domain/learning/viewing_event.py`、`framework_drivers/platform/main.py`)(未確認: コードを読んだ推測)〕
- `selected_answer` は、端末が送った文字列が、前後の空白を除いてそのまま保存される。設問の選択肢と一致するかは検査されない。`=1+1`、`a,b"c` + 改行 + `d` のような値も保存され、201 が返る。`is_correct` も端末が送った値がそのまま保存される。〔確認: 実行(`=1+1` を `is_correct: 1` で送り、そのまま保存された)〕
- 講義 lecture-1〜6 の小テストの選択肢(全120個)に、`=`、`+`、`-`、`@`、タブ、CR で始まるもの、カンマ・二重引用符・改行を含むものはない。〔確認: 実行(定義を読み込んで全選択肢を検査)〕
- 設問の文・選択肢・正解は DB になく、講義の小テストの定義(`framework_drivers/db/learning/quiz_definitions/lecture_{1..6}.py`)にある。〔確認: 読み取りのみ〕
- 研究者向けの既存のダウンロード(#25)は `/research/` 配下にあり、この前置詞の URL には、Basic 認証の検査と `Cache-Control: no-store` が自動で付く。資格情報がない・誤り・サーバーに未設定なら 401 になる(参加者としてログインした要求も 401)。〔確認: 実行(ログイン済みの参加者のクライアントで `/research/participants/P01/dialog-logs` → 401)。仕組みは読み取り(`research_auth.py`)〕
- 研究用の応答に CSV を返す仕組みは、まだない(既存の研究用の応答は JSON だけ)。〔確認: 読み取りのみ(`http_response.py`)(未確認: コードを読んだ推測)〕
- 視聴ログ・小テストを、全参加者分まとめて読む既存の読み出しはない(LAD の読み出しは、参加者1人・講義1つの単位)。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕

### POの意図(確認済み)

〔出典: PO の依頼と決定(2026-10-29、main 経由で受領)〕

1. LAD に示されている情報(視聴ログ・小テストの結果)を、研究者側で CSV 形式でダウンロードできるようにする。
2. 出力内容は生ログ。視聴ログは `viewing_logs` の全イベント行、小テストは全受験・全設問の回答。LAD の集計(6種の回数、120秒区間、最新1回だけ)は出さない。
3. 構成は、視聴ログ・小テストの2種類 × (参加者別 / 全員一括)= 4 つの URL。
4. 確認専用の ID(`P01`)の記録も含める。除外用の列は付けない。
5. 文字コードは UTF-8、先頭に BOM を付ける。

〔出典: PO の決定(2026-10-29、質問 Q1〜Q3 と分割案への回答。main 経由で受領)〕

6. 2つの PBI に分け、標準経路で順に進める。PBI-1 = 視聴ログの CSV(CSV の書式の共通部分 + 視聴ログの2 URL)、PBI-2 = 小テストの CSV(2 URL。PBI-1 の書式を使うので PBI-1 の後)。仕様は1ファイルとし、各 AC の属する PBI を表で示す(下記「PBI の分割と範囲」「PBI と AC の対応」)。
7. 小テストの CSV に、設問の文・正解の列は入れない(Q1)。
8. 文字列の列だけ、値が `=`、`+`、`-`、`@`、タブ、CR で始まるとき、先頭に `'` を付ける。数値の列(負の `duration` など)には付けない(Q2)。
9. 同じ参加者・講義の中の並びは、記録された順(ID の昇順)とする(Q3)。

〔出典: 既存の研究用ダウンロード(research-dialog-download.md)の PO 決定を踏襲する(main の依頼、2026-10-29)〕

- 研究者の識別は Basic 認証(共有の1組、環境変数 `RESEARCHER_BASIC_AUTH_USER` / `RESEARCHER_BASIC_AUTH_PASSWORD`)。未設定なら常に拒否(401)。
- 0件は 200(拒否しない)。応答をキャッシュさせない。サーバーのログに中身を出さない。取得の記録を残さない(DB に何も書かない)。
- 参加者別の参加者IDは、変換せず(前後の空白の除去や大文字・小文字の同一視をせず)そのまま照合する。
- 並び順を定め、取得のたびに変わらないようにする。

## 実現内容(What)

- **研究者だけが使える4つの CSV ダウンロード**を用意する。どれも、研究者の資格情報(Basic 認証)を付けた要求にだけ応じる。認証・キャッシュ・ログ・DB の扱いは、research-dialog-download.md と同じ規則に従う(下記「既存と同じ規則」)。
- 視聴ログの CSV は、視聴イベント1件 = 1行。小テストの CSV は、1回の受験の1問の回答 = 1行。どちらも、記録を集計・選別せず、すべて出す。
- ブラウザで URL を開いて資格情報を入力すると、CSV ファイルとして保存される。Excel で開いても文字化けしない(BOM)。curl 等からも同じ URL で取得できる。
- 対象の記録がなければ、見出しの行だけの CSV を状態 200 で返す。

### PBI の分割と範囲

| PBI | 範囲 | 依存 |
|---|---|---|
| PBI-1 視聴ログの CSV | 「CSV の書式」(4つに共通)、「既存と同じ規則」、視聴ログの2 URL、「視聴ログの CSV の列」、「対象と並び順」の視聴ログの部分 | なし |
| PBI-2 小テストの CSV | 小テストの2 URL、「小テストの CSV の列」、「対象と並び順」の小テストの部分。書式と規則は PBI-1 のものを使う | PBI-1 の完了後 |

### URL(共有IF)

| ダウンロード | 要求 | 保存されるファイル名 | PBI |
|---|---|---|---|
| 視聴ログ・参加者別 | `GET /research/participants/<参加者ID>/viewing-logs.csv` | `viewing-logs_<参加者ID>.csv` | PBI-1 |
| 視聴ログ・全員一括 | `GET /research/viewing-logs.csv` | `viewing-logs_all.csv` | PBI-1 |
| 小テスト・参加者別 | `GET /research/participants/<参加者ID>/quiz-answers.csv` | `quiz-answers_<参加者ID>.csv` | PBI-2 |
| 小テスト・全員一括 | `GET /research/quiz-answers.csv` | `quiz-answers_all.csv` | PBI-2 |

- ファイル名は `Content-Disposition: attachment; filename="..."` で示す。参加者IDが英数字・`-`・`_` だけでできていないとき(空白、`"`、日本語などを含むとき)は、参加者IDを入れず、`viewing-logs_participant.csv` / `quiz-answers_participant.csv` とする(ヘッダの値を壊さないため)。
- `Content-Type` は `text/csv; charset=utf-8`。

### CSV の書式(共有IF。4つに共通。PBI-1 で定める)

- 文字コードは UTF-8。本文の先頭に BOM(バイト列 `EF BB BF`)を1回だけ付ける。
- 1行目は見出しの行(下記の列名)。見出しの行は、0件のときも必ず出す。
- 区切りはカンマ、各行の終わり(最後の行を含む)は CRLF。
- 値にカンマ、二重引用符、CR、LF のいずれかを含むときは、値全体を二重引用符で囲み、値の中の二重引用符は2つ重ねる(RFC 4180)。それ以外の値は囲まない。
- 値は DB に保存された内容を変えずに書く(時刻の時差の変換、`selected_answer` の正規化、`action` の検査をしない)。例外は「数式とみなされる値の扱い」だけ。
- 空の値は、何も書かない(カンマの間が空)。`null` などの文字は書かない。

### 数式とみなされる値の扱い(PBI-1 で定める)〔決定: Q2〕

- 文字列の列(`participant_id`、`lecture_id`、`learning_session_id`、`time_stamp`、`attempted_at`、`action`、`selected_answer`)の値が、`=`、`+`、`-`、`@`、タブ、CR のいずれかで始まるときは、値の先頭に `'`(半角のアポストロフィ)を1つ付けて書く。表計算ソフトで開いたとき、値が数式として実行されないようにするため。
- `'` を付けた後の値に、カンマ・二重引用符・CR・LF が含まれるときは、上の書式のとおり囲む(`'` は囲みの内側の先頭)。
- 数値の列(`viewing_log_id`、`current_time`、`duration`、`attempt_id`、`score_numerator`、`score_denominator`、`question_index`、`is_correct`)には付けない(負の `duration` は `-12.0` のまま)。
- 理由: 前提のとおり、`selected_answer` には参加者の端末から任意の文字列を送れる。正規の選択肢(120個)は、どれもこの対象にならない。

### 視聴ログの CSV の列(この順。PBI-1)

| 列名 | 値 |
|---|---|
| `participant_id` | 参加者ID(`learning_sessions.learner_id`) |
| `lecture_id` | 講義ID(`learning_sessions.lecture_id`) |
| `learning_session_id` | 学習セッションID |
| `viewing_log_id` | 視聴イベントのID(`viewing_logs.id`。整数) |
| `time_stamp` | 操作の時刻。保存された文字列のまま(通常は `2026-10-29T01:00:00+00:00` の形。前提のとおり、別の時差や時差なしもありうる) |
| `current_time` | 動画内の位置(整数の秒) |
| `action` | 操作の種類。保存された文字列のまま(`play`、`pause`、`forward_skip`、`backward_skip`、`forward_seek`、`backward_seek`) |
| `duration` | 位置の変化(秒)。保存された数値を10進で書く(例: `10.0`、`-12.0`、`0.0`)。後ろ向きの操作は負 |

### 小テストの CSV の列(この順。PBI-2)〔決定: Q1〕

| 列名 | 値 |
|---|---|
| `participant_id` | 参加者ID |
| `lecture_id` | 講義ID |
| `learning_session_id` | 学習セッションID |
| `attempt_id` | 受験のID(`quiz_attempts.id`。整数)。同じ受験の行は同じ値 |
| `attempted_at` | 受験の時刻(`quiz_attempts.created_at`)。保存された文字列のまま |
| `score_numerator` | その受験の得点(整数) |
| `score_denominator` | その受験の満点(整数) |
| `question_index` | 設問の番号(1始まりの整数) |
| `selected_answer` | 選んだ答え(選択肢の文字列)。保存された文字列のまま(数式とみなされる値の扱いを除く) |
| `is_correct` | 正誤。`1`(正解)または `0`(不正解) |

- 回答の行が1つもない受験は、回答の列(`question_index`、`selected_answer`、`is_correct`)を空にした1行として出す(受験の記録を落とさないため)。
- 設問の文と正解の列は出さない。設問は、講義IDと `question_index` で講義の定義と対応づく。

### 対象と並び順〔決定: Q3〕

- 対象: 参加者別は、`learning_sessions.learner_id` が URL の参加者IDと完全に一致する学習セッション(すべての講義)の記録。一括は、すべての学習セッションの記録。確認専用の `P01` を含め、参加者や講義で除外しない。記録のない学習セッションは、行を出さない。
- 視聴ログの並び(PBI-1): 参加者IDの昇順 → 講義IDの昇順 → `viewing_log_id` の昇順(記録された順)。
- 小テストの並び(PBI-2): 参加者IDの昇順 → 講義IDの昇順 → `attempt_id` の昇順(記録された順)→ `question_index` の昇順(数値として)。
- 参加者IDと講義IDの昇順は、文字列としての順(文字コードの順)。例: `P01`、`P02`、`P10` の順、`1`、`10`、`2`、`foo` の順。
- 時刻の文字列では並べない(時差の違う値が混ざると、文字列の順が時刻の順にならないため)。同じ秒の記録があっても、ID で順が決まる(取得のたびに同じ並び)。研究者は `time_stamp` / `attempted_at` で並べ替えられる。

### 既存と同じ規則(research-dialog-download.md を参照。PBI-1 で定め、PBI-2 も従う)

- 資格情報と 401 の応答: 同仕様の「URL と資格情報」と同じ(`WWW-Authenticate` 付きの 401、本文に記録の内容を含めない。未設定も 401)。
- `Cache-Control: no-store`: 成功時・拒否時とも。
- サーバーのログに記録の内容を出さない。DB に何も書かない(取得の記録を残さない)。予期しない失敗では、記録の内容を含まない固定の応答(状態 500)を返す。
- 参加者IDは変換せずそのまま照合する(同仕様の Q6)。

## 受入基準

前提(すべての AC に共通): 「研究者の資格情報」は、サーバーの環境変数に設定した Basic 認証のユーザー名とパスワード。自動テストは、一時ディレクトリの DB と Flask のテストクライアントで行い、記録は既存の API(`POST /api/viewing-log`、`POST /api/quiz-attempts`)で作る(DB に直接行を置くのは、API では作れない状態だけ)。「CSV を読む」とは、BOM を除いた本文を、RFC 4180 の規則で行と値に分けることをいう。

### PBI と AC の対応

各 PBI は、その PBI の AC だけで承認・完了を判断する。PBI-1 の AC は、小テストの URL がなくても検証できる。

| PBI | 対象の URL | AC |
|---|---|---|
| PBI-1 視聴ログの CSV | 視聴ログの2つ | A1〜A9(認証、形式・BOM・CRLF、内容、一括と並び、0件、囲み、数式、no-store・ログ・DB 不変・回帰、ブラウザ) |
| PBI-2 小テストの CSV | 小テストの2つ | B1〜B10(認証、形式、内容(全受験・全設問)、回答のない受験、一括と並び、0件、囲みと日本語、数式、no-store・ログ・DB 不変・回帰、ブラウザ) |

### PBI-1: 視聴ログの CSV

「視聴ログの2つの URL」は、`/research/participants/<参加者ID>/viewing-logs.csv` と `/research/viewing-logs.csv`。

1. **A1 資格情報なし・誤り・未設定・参加者は拒否**: 視聴ログの2つの URL について、資格情報なし、ユーザー名かパスワードが誤り、サーバーに資格情報が未設定(どちらかが空を含む)、参加者としてログインしただけ、のいずれの要求にも、状態 401、`WWW-Authenticate` ヘッダありで応じ、本文に参加者ID・学習セッションIDのいずれも含まない。〔検証: 自動テスト〕
2. **A2 応答の形式**: 研究者の資格情報を付けた視聴ログの2つの URL の成功時の応答は、状態 200、`Content-Type` が `text/csv; charset=utf-8`、`Content-Disposition` が `attachment` で、ファイル名が URL の表のとおり(参加者 `P01` の参加者別は `viewing-logs_P01.csv`、一括は `viewing-logs_all.csv`、参加者ID ` 1`(前に空白)の参加者別は `viewing-logs_participant.csv`)。本文は BOM(`EF BB BF`)で始まり、BOM はほかの位置にない。すべての行が CRLF で終わる。〔検証: 自動テスト〕
3. **A3 視聴ログの内容**: 参加者 `P02` が lecture-1 で `play`(位置 0)、`forward_skip`(位置 30、変化 10)、`backward_seek`(位置 20、変化 `-12.7`)を記録した後、`P02` の視聴ログの参加者別を取得すると、CSV の見出しが `participant_id,lecture_id,learning_session_id,viewing_log_id,time_stamp,current_time,action,duration` で、続く3行が記録した順に、`participant_id` = `P02`、`lecture_id` = `lecture-1`、`learning_session_id`・`viewing_log_id`・`time_stamp` が DB の値と一致し、`current_time` が `0`・`30`・`20`、`action` が `play`・`forward_skip`・`backward_seek`、`duration` が `0.0`・`10.0`・`-12.0` である。〔検証: 自動テスト〕
4. **A4 一括の内容と並び順**: 参加者 `P01`、`P02`、`P10`、`10`、`2` が視聴ログを記録し、`P02` は lecture-1 と lecture-2 の両方で記録した後、視聴ログの一括を取得すると、見出しの後の行は、各参加者の視聴ログの参加者別の CSV の(見出しを除く)行をすべて含み、それ以外の行を含まない。`P01` の行も含まれる。並びは、参加者IDの文字列の昇順(`10`、`2`、`P01`、`P02`、`P10`)、同じ参加者の中は講義IDの昇順(`P02` は lecture-1 の行が lecture-2 の行より前)、その中は `viewing_log_id` の昇順である。同じ参加者・講義で、後に記録した行の `time_stamp` が先に記録した行より早い時刻(または同じ秒)であっても、記録した順(`viewing_log_id` の昇順)に並ぶ。〔検証: 自動テスト〕
5. **A5 0件は見出しの行だけ**: 記録のない参加者ID(存在しないID、学習セッションだけあって視聴ログのない参加者を含む)の視聴ログの参加者別、および視聴ログが1件もない状態の一括は、状態 200 で、本文が BOM + 視聴ログの見出しの行 + CRLF だけである。参加者 `1` が視聴ログを記録した後、参加者IDを ` 1`(前に空白)として参加者別を要求すると、0件と同じ応答になる(そのまま照合する)。〔検証: 自動テスト〕
6. **A6 特殊な文字の囲み**: 参加者ID が `a,b"c` + LF + `d` の学習セッションと、その視聴ログの行を DB に直接置いた後(API では作れないため)、視聴ログの一括を取得すると、その行の `participant_id` は `"a,b""c` + LF + `d"` と書かれ、CSV を読むとその値が元の文字列 `a,b"c` + LF + `d` と一致し、その行の列の数が見出しと同じである。〔検証: 自動テスト〕
7. **A7 数式とみなされる値**: 講義ID がそれぞれ `=1+1`、`+1`、`-1`、`@SUM(A1)`、タブ + `x`、CR + `x` の学習セッションと、その視聴ログの行を DB に直接置いた後(API では作れないため)、視聴ログの一括を読むと、その行の `lecture_id` はそれぞれ `'=1+1`、`'+1`、`'-1`、`'@SUM(A1)`、`'` + タブ + `x`、`'` + CR + `x` である。同じ取得で、A3 の `backward_seek` の行の `duration` は `-12.0` のまま(`'` が付かない)である。〔検証: 自動テスト〕
8. **A8 キャッシュさせない・ログに出さない・DB を変えない・既存を壊さない**: 視聴ログの2つの URL の成功時(200)と拒否時(401)の応答に `Cache-Control: no-store` がある。固有の文字列を参加者IDとする学習セッションと視聴ログを記録した後に視聴ログの2つの URL を取得すると、その間のアプリの logger の出力にその参加者IDと学習セッションIDが含まれず、`learning.db` と `tutor.db` の全表の行と値が取得の前後で変わらない。既存の自動テスト(`uv run pytest tests/ -v`、実 LLM を除く)がすべて成功する。〔検証: 自動テスト〕
9. **A9 ブラウザで取得できる**: 研究者の資格情報を設定してサーバーを起動し、PC のブラウザで視聴ログの2つの URL を順に開くと、資格情報の入力欄が出て、正しく入力すると、URL の表のファイル名で CSV ファイルが保存される。保存した一括のファイルを Excel で開くと、列が見出しのとおりに分かれ、`P01` の行が含まれ、負の `duration` が数値として表示される。入力を取り消すと、記録の内容は表示されず、ファイルも保存されない。〔検証: **PO確認**〕

### PBI-2: 小テストの CSV

「小テストの2つの URL」は、`/research/participants/<参加者ID>/quiz-answers.csv` と `/research/quiz-answers.csv`。

1. **B1 資格情報なし・誤り・未設定・参加者は拒否**: 小テストの2つの URL について、A1 と同じ4通りの要求に、状態 401、`WWW-Authenticate` ヘッダありで応じ、本文に参加者ID・学習セッションID・`selected_answer` の値のいずれも含まない。〔検証: 自動テスト〕
2. **B2 応答の形式**: 研究者の資格情報を付けた小テストの2つの URL の成功時の応答は、状態 200、`Content-Type` が `text/csv; charset=utf-8`、`Content-Disposition` が `attachment` で、ファイル名が URL の表のとおり(参加者 `P01` の参加者別は `quiz-answers_P01.csv`、一括は `quiz-answers_all.csv`、参加者ID ` 1`(前に空白)の参加者別は `quiz-answers_participant.csv`)。本文は BOM で始まり、BOM はほかの位置にない。すべての行が CRLF で終わる。〔検証: 自動テスト〕
3. **B3 小テストの内容(全受験・全設問)**: 参加者 `P02` が lecture-1 の小テストを2回受験(1回目は3問、2回目は2問)した後、`P02` の小テストの参加者別を取得すると、見出しが `participant_id,lecture_id,learning_session_id,attempt_id,attempted_at,score_numerator,score_denominator,question_index,selected_answer,is_correct` で(設問の文・正解の列はない)、続く5行が、1回目の3問(`question_index` 1、2、3)→ 2回目の2問の順に並ぶ。各行の `attempt_id`・`attempted_at`・得点・満点・`selected_answer`・`is_correct` は、その受験・回答の DB の値と一致し(`is_correct` は `1` または `0`)、1回目の3行の `attempt_id` は互いに同じで、2回目の行と異なる。最新1回だけに絞られていない。〔検証: 自動テスト〕
4. **B4 回答のない受験**: 回答の行が1つもない受験が DB にあるとき(DB に直接置く)、小テストの CSV にその受験が1行あり、`question_index`・`selected_answer`・`is_correct` が空で、ほかの列は受験の値である。〔検証: 自動テスト〕
5. **B5 一括の内容と並び順**: 参加者 `P01`、`P02`、`P10`、`10`、`2` が小テストを受験し、`P02` は lecture-1 と lecture-2 の両方で受験した後、小テストの一括を取得すると、見出しの後の行は、各参加者の小テストの参加者別の CSV の(見出しを除く)行をすべて含み、それ以外の行を含まない。`P01` の行も含まれる。並びは、参加者IDの文字列の昇順(`10`、`2`、`P01`、`P02`、`P10`)、同じ参加者の中は講義IDの昇順(`P02` は lecture-1 の行が lecture-2 の行より前)、その中は `attempt_id` の昇順、同じ受験の中は `question_index` の昇順である。同じ参加者・講義で、後の受験の `attempted_at` が先の受験より早い時刻(または同じ秒)であっても、受験した順(`attempt_id` の昇順)に並ぶ。〔検証: 自動テスト〕
6. **B6 0件は見出しの行だけ**: 記録のない参加者ID(存在しないID、学習セッションだけあって受験のない参加者を含む)の小テストの参加者別、および受験が1件もない状態の一括は、状態 200 で、本文が BOM + 小テストの見出しの行 + CRLF だけである。参加者 `1` が受験した後、参加者IDを ` 1`(前に空白)として参加者別を要求すると、0件と同じ応答になる。〔検証: 自動テスト〕
7. **B7 特殊な文字の囲みと日本語**: `selected_answer` に `a,b"c` + LF + `d` を記録した後、小テストの CSV を取得すると、その値は `"a,b""c` + LF + `d"` と書かれ、CSV を読むとその値が元の文字列 `a,b"c` + LF + `d` と一致する。日本語の選択肢(例: lecture-1 の `側面`)は、UTF-8 でそのまま書かれる。〔検証: 自動テスト〕
8. **B8 数式とみなされる値**: `selected_answer` に `=1+1`、`+1`、`-1`、`@SUM(A1)` を記録した後、小テストの CSV を読むと、その値はそれぞれ `'=1+1`、`'+1`、`'-1`、`'@SUM(A1)` である。同じ CSV の数値の列(`attempt_id`、`score_numerator`、`score_denominator`、`question_index`、`is_correct`)の値には `'` が付かない。〔検証: 自動テスト〕
9. **B9 キャッシュさせない・ログに出さない・DB を変えない・既存を壊さない**: 小テストの2つの URL の成功時(200)と拒否時(401)の応答に `Cache-Control: no-store` がある。固有の文字列を `selected_answer` に記録した後に小テストの2つの URL を取得すると、その間のアプリの logger の出力にその文字列が含まれず、`learning.db` と `tutor.db` の全表の行と値が取得の前後で変わらない。既存の自動テスト(PBI-1 の A1〜A8 を含む。`uv run pytest tests/ -v`、実 LLM を除く)がすべて成功する。〔検証: 自動テスト〕
10. **B10 ブラウザで取得できる**: 研究者の資格情報を設定してサーバーを起動し、PC のブラウザで小テストの2つの URL を順に開くと、資格情報の入力欄が出て、正しく入力すると、URL の表のファイル名で CSV ファイルが保存される。保存した一括のファイルを Excel で開くと、日本語(選択肢)が文字化けせず、列が見出しのとおりに分かれ、`P01` の行が含まれる。入力を取り消すと、記録の内容は表示されず、ファイルも保存されない。〔検証: **PO確認**〕

## 制約・関連機能

- **踏襲する既存仕様**: research-dialog-download.md(認証、401、no-store、ログ、DB 不変、参加者IDの照合、`/research/` 配下)。本件はその規則を変えない。
- **本件で新たに固定する共有IF**: 上記「URL」「CSV の書式」「数式とみなされる値の扱い」「視聴ログの CSV の列」「小テストの CSV の列」「対象と並び順」。PBI-1 の承認で、URL(視聴ログの2つ)、書式、数式の扱い、視聴ログの列と並びを固定する。PBI-2 は、それを変えずに使う(変えるときはレベル2以上の判断)。
- **読む表**: `learning.db` の4つの表だけ(PBI-1 は `learning_sessions` と `viewing_logs`、PBI-2 は `learning_sessions`、`quiz_attempts`、`quiz_attempt_answers`)。`tutor.db` は読まない(不変の確認だけ)。LAD の集計(application の LAD のユースケース)は使わない(生ログのため)。
- **同期が要る既存文書(実装後)**: README(研究者向けの取得手順に URL を追加。`P01` の行を分析で除くこと(participant-bulk-issuance.md の運用規則)、`'` の付いた値の意味(先頭の `'` は数式の実行を防ぐために付けたもので、元の値は `'` を除いたもの)。PBI-2 では、`is_correct` は端末が送った値であること)、framework-drivers-layer.md(HTTP 契約)、interfaces-layer.md(CSV の書き出しを置く場合)。PBI ごとに、その PBI の URL の分を更新する。
- 参加者ログイン(participant-login.md)、講義の選択(lecture-selection.md): 変えない。参加者としてログインした要求が拒否されることは A1・B1 で確認する。

### 既知の限界

- 消えない保存基盤ができるまでは、再デプロイ・再起動の前の記録は取得できない(research-dialog-download.md と同じ)。
- `/` を含む参加者ID、空の参加者IDは、参加者別の URL で指定できない(一括には含まれる)。
- 時刻は保存された形のまま出すため、API を直接呼んで記録された行には、`+00:00` 以外の時差や時差なしの値がありうる(画面からの記録は `+00:00`)。
- 学習セッションの行がない視聴ログ・小テストの行(外部キーの外れ)は、参加者と講義が分からないため出さない(`(未確認: 実データにあるかは確認していない)`)。
- 全員一括は、全記録を1回の応答で返す。30人規模で問題になる量かは、`(未確認: 実データの件数で確認していない)`。
- 正規の値が `-` などで始まる文字列の列(現状はない)があれば、その値にも `'` が付く。

### スコープ外

- 設問の文・正解の列(Q1 の決定による)、LAD の集計値の CSV、期間・講義での絞り込み、zip でのまとめ、対話ログの CSV。

### 実現性の点検

- **PBI-1 視聴ログの CSV**(既存の層分けに沿う場合):
  - 新規: application の読み出しの口(Port)と受け渡しの型(DTO)、視聴ログの取得のユースケース、interfaces の Controller・Presenter・ViewModel、CSV の書き出し(BOM、CRLF、囲み、`'` の付与。interfaces/common に置く想定)、framework_drivers/db/learning の SQLite の読み出し(`learning_sessions` と `viewing_logs` を結合して並べる)。
  - 変更: `framework_drivers/platform/main.py`(2つのルート。既存の `_research_response` は対話ログの Controller を固定で作るので、CSV 用に別の口が要る)、`framework_drivers/platform/http_response.py`(CSV の応答。`Content-Disposition` を付ける)、`framework_drivers/platform/wiring.py`(組み立て)。
  - 実装ファイル数: 新規 6〜7、変更 3 → **9〜10 ファイル**。src 行数の概算: **約 230〜270 行**(300行の基準内)。
  - テスト: `tests/test_api/test_research_viewing_logs_csv_api.py`(A1〜A8)、`tests/test_framework_drivers/db/learning/test_sqlite_viewing_log_export_query.py`(並び、0件)、`tests/test_interfaces/common/test_csv_encoding.py`(BOM、CRLF、囲み、`'`)。
- **PBI-2 小テストの CSV**:
  - 新規または変更: 読み出しの口と DTO に小テストの分を追加、小テストの取得のユースケース、Controller・Presenter・ViewModel(小テストの列)、SQLite の読み出し(3つの表の結合。回答のない受験を落とさない)。変更: `main.py`(2つのルート)、`wiring.py`。CSV の書き出しと `http_response.py` は PBI-1 のものを変えずに使う。
  - 実装ファイル数: **6〜8 ファイル**。src 行数の概算: **約 120〜160 行**。
  - テスト: `tests/test_api/test_research_quiz_answers_csv_api.py`(B1〜B9)、`tests/test_framework_drivers/db/learning/test_sqlite_quiz_answer_export_query.py`(並び、0件、回答のない受験)。
- **衝突・矛盾・依存の不足**: なし。新しい依存は不要(CSV は Python の標準ライブラリで書ける。interfaces は flask・sqlite3 を import しない規則があるが、標準の csv は対象外)。共有ファイル(`main.py`、`http_response.py`、`wiring.py`)は両 PBI が変更するため、PBI-2 は PBI-1 の完了後に行う。
- **テスト不能・曖昧な AC**: なし。A9・B10 は Excel での表示を含むため PO 確認。A6・A7 は、視聴ログの文字列の列に特殊な値を API から入れられないため、DB に直接置く(共通の前提の例外に当たる)。
- **規模**: 分割後、各 PBI の src 行数は 300 行の基準内の見込み。影響ファイル数は、どちらも5を超える(層分けによる。1つの機能のまとまりで、これ以上は分けない)。
- **未解決の論点**: なし(Issue 番号は Q0 で決定済み)。

## 質問(PO への確認)

| # | 論点 | 状態 |
|---|---|---|
| Q0 | Issue 番号 | 〔決定: #55(2026-10-29)〕 |
| Q1 | 小テストの CSV に、設問の文と正解の列を入れるか | 〔決定: 入れない。`question_index`、`selected_answer`、`is_correct` 等の記録の列だけ(2026-10-29)〕 |
| Q2 | 数式とみなされる値の扱い | 〔決定: 文字列の列だけ、値が `=`、`+`、`-`、`@`、タブ、CR で始まるとき先頭に `'` を付ける。数値の列には付けない(2026-10-29)〕 |
| Q3 | 同じ参加者・講義の中の並び | 〔決定: 記録された順(ID の昇順)(2026-10-29)〕 |
| — | 分割 | 〔決定: 案A。PBI-1 = 視聴ログの CSV(書式の共通部分を含む)、PBI-2 = 小テストの CSV。標準経路で PBI-1 → PBI-2 の順(2026-10-29)〕 |

## 変更理由

- issue 未確認(2026-10-29): PO が、LAD に示される情報(視聴ログ・小テスト)を研究者が CSV で取得できるよう依頼し、出力内容(生ログ)、構成(2種類 × 参加者別/一括)、`P01` を含めること、UTF-8 BOM を決めた。これに合わせて新規に起草した。認証・キャッシュ・ログ・DB 不変・参加者IDの照合は research-dialog-download.md を踏襲した。時刻の保存形式、`duration` の値、`selected_answer` に任意の文字列が入ることを実行で確認し、CSV の書式と数式の扱い、並びに反映した。DR はなし。
- issue 未確認(2026-10-29): PO の決定(分割は案A、Q1 = 設問の文・正解の列は入れない、Q2 = 文字列の列だけ `'` を付ける、Q3 = 記録された順)を反映した。AC を PBI-1(A1〜A9)と PBI-2(B1〜B10)に分け、共通部分(認証、BOM、CRLF、囲み、数式の扱い、0件、no-store、DB 不変、ログ非出力)を PBI-1 で検証できるようにした。視聴ログの文字列の列には特殊な値を API から入れられないため、PBI-1 の囲み・数式の AC(A6・A7)は DB に直接置いた行で確かめる形にした。DR はなし。
