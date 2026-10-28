# 文系レベル3講義の登録 — lecture-4〜6(律令制、心理カウンセリング、言語の仕組み)を講義カタログに登録し、講義ページの動画・小テスト・字幕・講義情報と、講義ページが送る記録を、その講義のものにする

## Issue

#33(FR-61)

## 目的(Why)

実験(2026-10-27 開始)では、理系レベル3本に加えて、文系レベル3本の学習コンテンツを使う(FR-60、FR-61)。現在の講義カタログには理系の lecture-1〜3 しかなく、文系の動画・小テスト・講義情報・字幕を載せる場所がない。研究者(PO)が用意した文系3本の素材を、理系と同じ形でカタログに登録し、講義ページ(`/lecture?lecture_id=lecture-4` など)で、動画・小テスト・字幕・講義情報が動くことを確かめられる状態にする。

あわせて、講義ページは、視聴ログ・小テストの送信に、ページの講義IDを付けて送る。講義ページから進む振り返りページは、その講義IDを引き継ぎ、AI チューター(`/chat`)・LAD の取得・対話ログの保存(`/api/dialog-log`)に付ける。付けないと、lecture-4 のページで視聴・回答しても lecture-1 として記録され、AI チューターも lecture-1 の字幕で答え、さらに lecture-4 での会話が対話ログに入らない(前提)ため、文系の講義を登録しても実験のデータにならない。

協力者が講義を選ぶ画面、選択の保存(FR-60・FR-63)、選んだ講義を各画面・記録に一貫させること(FR-62 のうち、本 PBI で前倒しする URL の講義IDによる引き継ぎと対話ログの保存を除く残り)、参加者→講義の固定割当の変更は、別の PBI で扱う。参加者→講義の固定割当は変えない。

## 前提

### 実装の現状(コードの観測事実)

- 講義の定義は4か所にハードコードされている: `framework_drivers/db/learning/static_lecture_catalog.py` の `_NEAR_TERM_LECTURES`(講義ID、題名、動画URL)、`_quiz_definition_for` と `_lecture_outline_for` の対応表、`framework_drivers/platform/main.py` の `_QUIZ_MODULES`(小テストの題名・説明の取得元)。SRT は `lectures/<講義ID>/subtitles.srt` に固定。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- 現在、`/lecture?lecture_id=lecture-4` は 404 を返す。〔確認: 実行(一時ディレクトリの pytest で、ログイン ID `P01` で GET。2026-10-26)〕
- 既存の講義題名は仮の「線形代数入門(近い実験 N)」。講義題名を、画面または AI チューターの文脈で使っている箇所は、`grep` では見つからなかった。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- 小テストの定義(`Question`)は、問題文、4つの選択肢、正解(選択肢の文字列そのもの)だけを持つ。解説の項目はなく、画面にも解説は表示されない。既存3講義の選択肢には「A.」などの記号がなく、設問の見出しもない。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- 小テストの送信(`/api/quiz-attempts`)は、設問番号が講義の小テストに含まれるかだけを検査し、選んだ選択肢の文字列は検査しない。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- 講義情報(`LectureOutline`)は、章(id、題、start_sec、end_sec、要約)、動画内演習(0件でもよい)、設問ごとの採点意図(`QuizRubricNote`)を持ち、AI チューターのプロンプトに入る(`interfaces/tutoring/context_formatters.py` の `format_lecture_outline`)。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- **講義IDの決め方(サーバー側)**: `/chat`・`/api/viewing-log`・`/api/quiz-attempts` は本文の `lecture_id` を、LAD(`/api/participants/<id>/lad`)と `/api/last-updated` はクエリの `lecture_id` を読む。送られなければ、参加者IDの固定マップ(`1`/`2`/`3` → `lecture-1`/`2`/`3`、それ以外は `lecture-1`)で決める。`/api/dialog-log` は本文の `lecture_id` を読まず、常に固定マップで決める。〔確認: `/chat` は実行(下記)。LAD は実行(ログイン ID `P01` で `?lecture_id=lecture-2` を付けて 200。2026-10-26)。その他は読み取りのみ(未確認: コードを読んだ推測)〕
- **講義ページ(`lecture.html`)の JS は、講義IDを送らない。** 視聴ログ(`player.js` → `ApiClient.postViewingLog`)と小テスト送信(`quiz.js` → `ApiClient.buildQuizAttemptPayload`)の本文は、参加者IDと操作・回答だけを持つ。ページに埋め込まれる値は、参加者ID、動画ID、正解、字幕で、講義IDは画面の表示だけ。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- **AI チューター(チャット)と LAD は、講義ページではなく振り返りページ(`/reflect`)にある。** 講義ページの「振り返り画面へ進む」のリンク先は `/reflect` で、講義IDを含まない。`/reflect` は講義IDのクエリを読まない(`/reflect?lecture_id=lecture-2` は 200 で、ページに `lecture-2` は現れない。`/reflect?lecture_id=lecture-99` も 200)。振り返りページの JS(`chat_panel.js` の `/chat`、`reflect_app.js` の LAD 取得、`dialog_log.js`・`leave_guard.js` の `/api/dialog-log`)も講義IDを送らない。〔確認: リンク先と `/reflect` の応答は実行(ログイン ID `P01`。2026-10-26)。JS は読み取りのみ(未確認: コードを読んだ推測)〕
- ログイン ID `P01` で、講義IDなしで `/chat` を送ると、プロンプトには lecture-1 の字幕が入る。本文に `lecture_id: "lecture-2"` を入れると、lecture-2 の字幕が入る。〔確認: 実行(一時ディレクトリの pytest、FakeLlmGateway。2026-10-26)〕
- **対話ログは、チャットと別の講義IDで保存されると、その会話を含まない。** ログイン ID `P01` で、`lecture_id: "lecture-2"` を付けて `/chat` を2回送り(対話セッション A)、続けて `/api/dialog-log`(`end_button`)を送ると、200 が返り、`dialog_logs` には lecture-1 の別の対話セッション B が `messages: []` で保存された。セッション A の2往復は、対話ログに入らなかった。〔確認: 実行(一時ディレクトリの pytest、FakeLlmGateway。2026-10-26)〕 → 対話セッションは「参加者 × 講義」の学習セッションごとに作られ、対話ログの保存は固定マップの講義(P01 なら lecture-1)の対話セッションを保存するため(読み取りのみ(未確認: コードを読んだ推測))。
- **対話ログの保存が講義を lecture-2 と決めた場合**: 同じ手順(`P01`、`lecture_id: "lecture-2"` で `/chat` を2回)の後、保存の Controller が講義を lecture-2 と決めるよう、テストの中だけで差し替えて(プロダクトのファイルは変えない)`/api/dialog-log` を送ると、200 が返り、`dialog_logs` には lecture-2 の対話ログが1件だけ保存され、その発言は `user`・`assistant`・`user`・`assistant` の4件だった。〔確認: 実行(一時ディレクトリの pytest、FakeLlmGateway。2026-10-26)〕 → 保存の処理自体は講義を問わず動き、講義IDを Controller まで渡せば、その講義の会話が保存される。
- **未登録の講義IDで対話ログを保存した場合**: 同じ差し替えで講義を `lecture-99`(未登録)と決めると、`/api/dialog-log` は 200 を返し、`lecture-99` の対話ログ(発言0件)が保存された。同じ講義IDの `/chat` は 404(`LECTURE_NOT_FOUND`)を返す。〔確認: 実行(同上。2026-10-26)〕 → 対話ログの保存は、講義がカタログにあるかを検査しない。本文の講義IDを読むようにすると、検査がない限り、未登録の講義IDで空の対話ログが保存されうる(AC21 で 404 にする)。
- 字幕の画面表示は、同じディレクトリに整形済み(`subtitles.display.srt`)があればそれを、なければ元の `subtitles.srt` を使う(#44、スプリント009、未コミット)。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- 字幕ファイルの形式(一時スクリプトで解析し、`parse_srt_file` で読んだ。2026-10-26)〔確認: 実行〕

  | 項目 | lecture-1 `subtitles.srt`(既存) | lecture-4 律令(`【飛鳥時代】25 律令制ってそもそも何なの？【日本史】 [Japanese] [DownloadYoutubeSubtitles.com].srt`) | lecture-5 心理(`心理臨床面接_カウンセリングの基礎知識_修正版.srt`) | lecture-6 言語(`言語の仕組み_音声・音韻・語_修正版.srt`) |
  |---|---|---|---|---|
  | BOM | なし | なし | なし | なし |
  | 改行 | CRLF のみ | **混在**(ブロックの区切りは CRLF、ブロック内の2行目への改行は LF のみ。CRLF 900、LF のみ 218) | CRLF のみ | CRLF のみ |
  | 末尾の改行 | なし | あり | あり | あり |
  | ブロック数 | 295 | 225 | 295 | 237 |
  | 1ブロックの行数 | 3(番号、時刻、文1行) | **4(文2行)が 218、3 が 7** | 3 | 3 |
  | 番号の連番・時刻行の形式 | 正常 | 正常 | 正常 | 正常 |
  | 前のキューと時刻が重なる組 | 282 | 0 | 292 | 231 |
  | 最終の終了時刻 | 821.67 秒 | 892.52 秒 | 739.35 秒 | 785.959 秒 |
  | 括弧のキュー | `[音楽]` | なし | `[音楽]` | なし |
  | `parse_srt_file` のセグメント数 | 295 | 225 | 295 | 237 |
  | バイト数 | — | 23729 | 26364 | 22164 |
  | SHA-256 | — | `acd74f8593f16e50e8a29be871d5dadf7faf383fb6dcacbd179d23c7f0c0b530` | `7351694e71c349acb960009e4b66c58a28f590335469036df16e74591b7e5dd5` | `3b5b6c8ac6b66372b72cf6e7ef32ddfcd613839a4b42e4e3626007fe7f733414` |

  - 4ファイルとも `parse_srt_file` で読め、セグメント数はブロック数と一致した。律令の文2行は、半角空白でつながった1つの文になる(例: 「その時に律令なんかよくわかん ないけどいいや」)。
  - バイト数と SHA-256 は、`~/Downloads` の受領ファイルを 2026-10-26 に計測した値。
- 講義の追加で、既存のテストは壊れない(既存のテストは、講義IDを固定した列挙で検査しており、講義数の一致を検査していない)。例外は `test_static_lecture_catalog.py` の「SRT が実在する」検査で、カタログに登録した全講義について `lectures/<講義ID>/subtitles.srt` の実在を求める。〔確認: 読み取り(関係するテストの `grep`)、実行(関係する 113 件が現状で成功。2026-10-26)〕
- 既存の JS テスト(`tests/test_framework_drivers/js/`)への影響: `lecture_player_seek_count.mjs`・`lecture_subtitles.mjs`(#44 が変更中)は `ApiClient.postViewingLog` を差し替えて呼び出しの回数と引数(4つ)を見る。`reflect_chat_panel_input.mjs` は `/chat` の本文の `participant_id` を見る(本文のキーの完全一致は見ない)。`reflect_leave_guard.mjs` は、離脱時の `/api/dialog-log` の本文のキーが `participant_id` と `end_method` の2つだけであることを検査する(`LeaveGuard.init` を参加者IDだけで呼ぶ)。`reflect_dialog_log.mjs` は `ApiClient.postDialogLog` を差し替え、引数のうち参加者IDと終了の方法(2つ)を記録する。`test_dialog_log_api.py`・`test_save_dialog_log_controller.py` は、講義IDを本文に入れずに送り、講義が固定マップで決まることを検査する。講義ページの「振り返り画面へ進む」のリンク先(`href="/reflect"`)を検査するテストはない。講義ページの JS(`player.js`・`quiz.js`)の送信本文に講義IDが入ることを検査するテストはない。〔確認: 読み取りのみ(未確認: コードを読んだ推測)〕
- 既存の仕様 `docs/spec/framework-drivers-layer.md` の「参加者導線」は「`lecture_id` は URL に含めない(サーバーが `participant_id` から解決)」と書いている。`docs/spec/dialog-log-save.md` の保存 API は、本文を「`participant_id` と `end_method` の2つだけ」とし、対話ログの `lecture_id` を「その参加者の学習セッションの講義ID」としている。〔確認: 読み取り〕

### POの意図(確認済み)

- 範囲: lecture-4〜6 をカタログに登録し、`/lecture?lecture_id=lecture-4` などで、動画・小テスト・字幕・AI チューター・講義情報が動くところまで。協力者の選択画面、選択の保存、参加者→講義の割当の変更は、別 PBI。〔出典: PO決定 2026-10-26(`sprint-backlog.md`)〕
- 対応: lecture-4 = 律令制(YouTube `cUCNymPtQ5Y`)、lecture-5 = 心理カウンセリングの基礎(`lLcZEIsyHvg`)、lecture-6 = 言語の仕組み(音声・音韻・語)(`psbIrfy09Pg`)。〔出典: 同上〕
- 講義情報(章立て、動画内演習、小テストの採点意図 Q1〜Q5)は、AI が案を作り、PO が PO確認シートで講義ごとに確認する。動画内演習がない講義は0件でよい。〔出典: PO決定 2026-10-26(論点9)〕
- 講義IDの伝搬(論点1 = B): 講義ページが、chat・視聴ログ・小テスト送信(と、LAD 取得など同様に必要なもの)に、ページの講義IDを付ける。`/api/dialog-log` は lecture-1 のまま(別 PBI = FR-62)。その結果のずれを「既知の制約」に書き、ACで現状維持を固定する。既存の理系の挙動(参加者の固定割当、`P01`〜`P30` = lecture-1、participant-login AC25)は変えない。講義IDを送らない既存の呼び出しの後方互換を保つ。〔出典: PO決定 2026-10-26(論点1)〕 → 対話ログの扱いは、下記の論点11 = a で変更された。
- 振り返りページへの引き継ぎ(論点10 = A): 講義ページの「振り返り画面へ進む」を `/reflect?lecture_id=<ページの講義ID>` にし、振り返りページがその講義IDを `/chat` と LAD の取得に付ける。講義IDなしの `/reflect` は従来どおり固定割当。未登録の講義IDは 404。`framework-drivers-layer.md` の「`lecture_id` は URL に含めない」の記述は AC16 で直す。〔出典: PO決定 2026-10-26(論点10)〕
- 対話ログ(論点11 = a): 対話ログの保存を本 PBI に含める(FR-62 の一部を前倒し)。振り返りページが、終了ボタンとページ離脱の両方で `/api/dialog-log` に講義IDを付ける。サーバーは、講義IDがなければ従来どおり固定割当で決める。`reflect_leave_guard.mjs` の「本文のキーは2つだけ」の検査の更新が要る。〔出典: PO決定 2026-10-26(論点11)〕
- PBI の大きさ: 小テスト・講義情報のデータ定義は、大きさの基準(src 300 行)に数えない。1 PBI。〔出典: PO決定 2026-10-26(論点2)〕
- 解説は使わない(表示せず、データにも入れない)。講義情報の採点意図(Q1〜Q5)は、設問と正解から書く。〔出典: PO決定 2026-10-26(論点3)〕
- 題名と説明: 講義題名は「律令制」「心理カウンセリングの基礎」「言語の仕組み(音声・音韻・語)」。小テストの題名は「律令制の仕組み」「心理カウンセリングの基礎」「言語の仕組み（音声・音韻・語）」。小テストの説明は「動画で解説された<小テストの題名>に関する確認問題です。」。〔出典: PO決定 2026-10-26(論点4、案どおり)〕
- 小テストの文面: 選択肢の記号「A.〜D.」と設問の見出しは含めず、選択肢は貼られた順。〔出典: PO決定 2026-10-26(論点5)〕
- 字幕の素材: lecture-4 = `~/Downloads/【飛鳥時代】25 律令制ってそもそも何なの？【日本史】 [Japanese] [DownloadYoutubeSubtitles.com].srt`(PO が「修正済み&整形済み」としたもの。仮データではない)、lecture-5 = `~/Downloads/心理臨床面接_カウンセリングの基礎知識_修正版.srt`、lecture-6 = `~/Downloads/言語の仕組み_音声・音韻・語_修正版.srt`。バイト列を変えずに置く。〔出典: PO決定 2026-10-26(論点6)〕
- 3本は `subtitles.srt` として置き、AI チューターの文脈にも使う。`subtitles.display.srt` は本 PBI の範囲外で、画面は `subtitles.srt` で表示する。〔出典: PO決定 2026-10-26(論点7)〕
- lecture-6 第2問の問題文の全文は付録A のとおり。〔出典: PO決定 2026-10-26(論点8)〕
- 小テストは、PO が貼った本文(付録A)をデータにする。〔出典: 起草の依頼(2026-10-26)〕

## 実現内容(What)

1. **講義の登録**: 講義カタログに lecture-4・5・6 を追加する。各講義は、講義ID、題名、YouTube 動画、字幕(`lectures/<講義ID>/subtitles.srt`)、小テスト、講義情報を持つ。lecture-1〜3 の内容は変えない。
2. **講義ページ**: `/lecture?lecture_id=lecture-4`(5、6 も同じ)を開くと、その講義の動画、字幕、小テストが表示される。
3. **小テスト**: 付録A の本文を、各講義の5問×4択の小テストにする。問題文・選択肢・正解は付録A のとおり。選択肢の記号と設問の見出しは文面に含めず、選択肢は付録A の順に並べる。解説は表示せず、データにも持たない。
4. **字幕**: PO から受け取った SRT を、バイト列を変えずに、各講義の `subtitles.srt` として置く。表示用の整形済み字幕は置かず、画面は `subtitles.srt` で表示する。
5. **講義情報**: 各講義の章立て(開始・終了秒、要約)、動画内演習(ないときは0件)、Q1〜Q5 の採点意図を、AI が字幕・設問・正解から案として作り、PO が確認してからデータにする。
6. **AI チューターの文脈**: lecture-4〜6 を講義IDとして指定した AI チューターの要求では、その講義の字幕と講義情報がプロンプトに入る。
7. **講義ページが送る講義ID**: 講義ページは、視聴ログと小テストの送信に、ページの講義ID(ページが表示している講義)を付ける。これにより、lecture-4 のページでの視聴と回答は lecture-4 として記録される。
8. **振り返りページへの講義IDの引き継ぎ**(置き換え(#34): 「講義IDなしは固定割当」「未登録の講義IDは 404」は、[lecture-selection.md](./lecture-selection.md) の What 4節・AC15 に置き換えた。講義は選択で決まり、選択済みで選択と異なる値は 403(未登録の値を含む)、空の値は 404 のまま、未選択は選択の画面へ 302): 講義ページの「振り返り画面へ進む」は、振り返りページを、ページの講義ID(表示している講義)を付けた URL(`/reflect?lecture_id=<講義ID>`)で開く。振り返りページは、URL の講義IDを、AI チューター(`/chat`)と LAD の取得に付ける。講義IDなしで振り返りページを開いたときは、従来どおり固定割当の講義になる。未登録の講義IDを付けた振り返りページは開けない(404)。
9. **対話ログの講義ID**(置き換え(#34): 講義IDなしの扱いは [lecture-selection.md](./lecture-selection.md) の What 4節に置き換えた。選択した講義で保存する): 講義IDを付けて開いた振り返りページは、対話ログの保存(終了ボタン、ページ離脱の両方)に、その講義IDを付ける。サーバーは、付いた講義の対話セッション(その講義で行った会話)を、その講義の対話ログとして保存する。講義IDなしで開いた振り返りページの保存要求は、従来どおり講義IDを含まず、固定割当の講義で保存される。
10. **後方互換**(置き換え(#34): 固定割当は廃止した。[lecture-selection.md](./lecture-selection.md) の What 4節): 講義IDを付けない要求(既存の呼び出し、講義IDなしで開いたページ)は、従来どおり参加者IDの固定割当で講義を決める。
11. **範囲外(既存の挙動を変えない)**: 協力者の講義選択画面(FR-60)、選択の保存と選べる回数・変更(FR-60・FR-63)、選んだ講義を各画面・記録に一貫させること(FR-62 の残り。本 PBI は URL の講義IDで引き継ぐところまで)、参加者→講義の固定割当の変更(`P01`〜`P30` は lecture-1。participant-login の AC25)、研究者向けの対話ログの取り出し(`/research/...`)の変更、`/api/last-updated` への講義IDの付与(振り返りページの JS から呼ばれていない)。

### 既知の制約

- **講義IDは URL で引き継ぐ**: 振り返りページの講義は、URL の講義IDで決まる。講義ページを経ずに `/reflect` を直接開く(ブックマーク、URL の手入力、講義IDを外した URL)と、固定割当の講義(`P01`〜`P30` なら lecture-1)の AI チューター・LAD・対話ログになる。同じ参加者が別の講義の振り返りページを開くと、講義ごとに別の対話セッション・対話ログになる(学習セッションが「参加者 × 講義」で分かれるため)。
- **理系の講義を講義ID付きで開いたとき**: 講義IDを付けずに `/lecture` を開いたとき(実験の通常の導線)の記録は変わらない。一方、`P01` で `/lecture?lecture_id=lecture-2` のように固定割当と異なる講義を明示して開いたとき、視聴ログと小テストは、従来の lecture-1 ではなく、ページの講義(lecture-2)として記録されるようになる。そこから進んだ振り返りページの AI チューター・LAD・対話ログも lecture-2 になる(本 PBI の目的どおりの変化)。講義IDを付けずに開いた講義ページから進んだ振り返りページは、表示していた講義(固定割当の講義)のIDが URL に付くため、AI チューター・LAD・対話ログの講義は従来と同じになる。
- 文系の協力者を講義に割り当てる仕組み(選択画面、選択の保存)はないため、文系の講義は `?lecture_id=` を付けた URL で開く。

## 受入基準

1. **講義の登録**: 講義カタログで `lecture-4`・`lecture-5`・`lecture-6` を引くと講義が返り、動画 URL はそれぞれ `https://www.youtube.com/watch?v=cUCNymPtQ5Y`、`https://www.youtube.com/watch?v=lLcZEIsyHvg`、`https://www.youtube.com/watch?v=psbIrfy09Pg`、題名はそれぞれ「律令制」「心理カウンセリングの基礎」「言語の仕組み(音声・音韻・語)」である。〔検証: 自動テスト〕
2. **字幕ファイルの配置**: lecture-4〜6 の字幕のパスは `lectures/<講義ID>/subtitles.srt` で、ファイルが実在する。〔検証: 自動テスト〕
3. **講義ページの表示**: ログインした状態で `/lecture?lecture_id=lecture-4` を開くと 200 が返り、ページに YouTube 動画ID `cUCNymPtQ5Y` が埋め込まれ、他の講義の動画IDは含まれない。lecture-5(`lLcZEIsyHvg`)、lecture-6(`psbIrfy09Pg`)も同じ。〔検証: 自動テスト〕
4. **小テストの内容**: lecture-4〜6 の小テストは、それぞれ5問、各4択で、各設問の問題文・選択肢(並び順を含む)・正解が付録A と一致する。問題文と選択肢は、付録A の表のセルの文字列そのもので、記号「A.〜D.」と見出しを含まない。正解は、付録A の正解の記号が指す選択肢の文字列である。小テストのデータは解説を持たない。〔検証: 自動テスト〕
5. **小テストの表示**: `/lecture?lecture_id=lecture-4` のページに、小テストの題名「律令制の仕組み」、説明「動画で解説された律令制の仕組みに関する確認問題です。」、5問の問題文、各選択肢が含まれる。lecture-5 は題名「心理カウンセリングの基礎」・説明「動画で解説された心理カウンセリングの基礎に関する確認問題です。」、lecture-6 は題名「言語の仕組み（音声・音韻・語）」・説明「動画で解説された言語の仕組み（音声・音韻・語）に関する確認問題です。」。ページに付録A の解説の文は含まれない(各講義の解説の1文目で確かめる)。〔検証: 自動テスト〕
6. **小テストの送信(API)**: 講義IDに `lecture-4`(5、6 も同じ)を指定し、その講義の全問正解の回答で `/api/quiz-attempts` に送ると、201 と attempt_id が返り、記録された試行の講義IDは指定した講義である。〔検証: 自動テスト〕
7. **字幕の表示データ**: `/lecture?lecture_id=lecture-4` のページに埋め込まれる字幕は、`lectures/lecture-4/subtitles.srt` を `parse_srt_file` で読んだ結果(開始・終了・文)と一致する(lecture-5・6 も同じ。整形済みファイルを置かないため)。〔検証: 自動テスト〕
8. **字幕の構造と同一性**: lecture-4〜6 の `subtitles.srt` について、次がすべて成り立つ。(a) バイト数と SHA-256 が、前提の表の値と一致する(受領ファイルのバイト列のまま)。(b) BOM がない。(c) ブロック(空行で区切る。改行は CRLF と LF の両方を区切りとして扱う)の番号が 1 からの連番。(d) 各ブロックの2行目が `HH:MM:SS,mmm --> HH:MM:SS,mmm` の形式。(e) 各ブロックの文が空でない。(f) 開始時刻が減らない。(g) `parse_srt_file` のセグメント数がブロック数と一致する(225 / 295 / 237)。(h) 最終の終了時刻が、lecture-4 は 892.52 秒、lecture-5 は 739.35 秒、lecture-6 は 785.959 秒。校正前との比較(proofread)は行わない。〔検証: 自動テスト〕
9. **講義情報の構造**: lecture-4〜6 の講義情報は、章が1つ以上、章の開始秒が昇順、全章の開始・終了秒が 0 以上かつその講義の字幕の最終終了時刻以下、採点意図が設問 1〜5 のそれぞれに1件ある。動画内演習は0件でもよい。〔検証: 自動テスト〕
10. **講義情報の内容**: lecture-4〜6 の章立て(題、開始・終了秒、要約)、動画内演習、Q1〜Q5 の採点意図を、PO が PO確認シートで講義ごとに、動画・字幕・設問・正解と照らして確認し、承認する。採点意図は、設問と正解から書かれ、付録A の解説(本仕様には残していない)に依存しない。〔検証: PO確認〕
11. **AI チューターの文脈(講義ID指定)**: 講義IDに `lecture-4` を指定して視聴ログ(再生位置 15 秒など、字幕のある位置)を送り、続けて講義IDに `lecture-4` を指定して `/chat` を送ると、LLM に渡るプロンプトに、lecture-4 の字幕のその位置の文と、lecture-4 の講義情報の章の題が含まれ、lecture-1 の字幕のその位置の文は含まれない(lecture-5・6 も同じ。LLM は Fake)。〔検証: 自動テスト〕
12. **未登録の講義**: `/lecture?lecture_id=lecture-7` は、従来どおり 404 を返す。〔検証: 自動テスト〕
13. **既存の挙動を変えない**: 次が従来どおりである。(a) ログイン ID `P01` で講義IDを付けずに `/lecture` を開くと lecture-1 の動画が表示され(participant-login AC25)、そのページが送る視聴ログと小テストは lecture-1 として記録される。(b) 参加者ID `1`/`2`/`3` で講義IDを付けずに `/lecture` を開くと、それぞれ lecture-1/2/3 が表示され、記録もその講義になる。(c) lecture-1〜3 の動画・小テスト・講義情報・字幕のデータが変わらない。(d) 講義IDを付けない `/api/dialog-log` は、従来どおり固定割当の講義(`P01` なら lecture-1、参加者ID `2` なら lecture-2)の対話セッションを、その講義の対話ログとして保存する(既存の `test_dialog_log_api.py` が変更なしで成功する。`test_save_dialog_log_controller.py` の、講義IDなしで固定マップの講義に決まることの検査(参加者ID `1`/`2`/`3`/`abc` → lecture-1/2/3/1)は、期待値を変えずに成功する)。講義IDなしで開いた `/reflect` の対話ログの保存要求(終了ボタン、ページ離脱)の本文は、従来どおり `participant_id` と `end_method` の2つだけである。既存のテストがすべて成功することでも確かめる。〔検証: 自動テスト〕
14. **動画の再生**: PO が `/lecture?lecture_id=lecture-4`・`5`・`6` を開き、それぞれ律令制・心理カウンセリング・言語の仕組みの動画が再生され、再生に合わせて字幕が表示され、小テストに回答して送信できることを確認する。〔検証: PO確認〕
15. **AI チューターの応答(実呼び出し)**: PO が `/lecture?lecture_id=lecture-4`(5、6 も同じ)から「振り返り画面へ進む」で振り返りページを開き、AI チューターに講義の内容を質問すると、その講義(律令制・心理カウンセリング・言語の仕組み)の内容に基づいて答え、lecture-1(線形代数)の内容で答えないことを確認する。LAD に、その講義ページでの視聴と小テストの結果が表示されることも確認する。続けて PO が終了ボタンで対話を終えた後、AI が `tutor.db` の対話ログを読み、その講義IDの対話ログに、PO が送った質問と AI チューターの応答が入っていることを確かめる。〔検証: PO確認(応答の内容と LAD の表示)+ AI実行(対話ログの確認)〕
16. **ドキュメント**: `lectures/README.md` の講義表に lecture-4〜6(講義ID、動画、SRT)が載る。「3 講義」と書いている既存仕様(`docs/spec/application-usecase.md` の LectureCatalog、`docs/spec/framework-drivers-layer.md` の db)に、lecture-4〜6 の登録が反映される(参加者の割当が固定マップのままであることも書く)。`docs/spec/framework-drivers-layer.md` の参加者導線・HTTP 契約に、講義ページが講義IDを送ること、振り返りページが URL の講義ID(`/reflect?lecture_id=`)を `/chat`・LAD の取得・`/api/dialog-log` に付けること、未登録の講義IDの `/reflect` は 404 であること、講義IDなしの要求は固定割当で決まることが反映され、「`lecture_id` は URL に含めない」の記述が現状に合わせて直る。`docs/spec/dialog-log-save.md` の保存 API の本文の定義(「2つだけ」)と対話ログの `lecture_id` の定義に、任意の `lecture_id`(付けたときはその講義、付けないときは固定割当。未登録は 404)が反映される(変更の出典として本仕様と #33 を書く)。〔検証: AI実行〕
17. **視聴ログの講義ID**: `/lecture?lecture_id=lecture-4` のページで視聴操作(再生・一時停止・スキップ・シーク)をしたとき、送られる視聴ログの本文に `lecture_id: "lecture-4"` が付き、従来の項目(`participant_id`、`time_stamp`、`current_time`、`action`、`duration`)は従来どおり付く。サーバーに送られた視聴ログは lecture-4 として記録される。lecture-5・6、講義IDなしで開いたページ(付くのは表示している講義のID)も同じ。〔検証: 自動テスト〕
18. **小テスト送信の講義ID**: `/lecture?lecture_id=lecture-4` のページで小テストを送信したとき、送られる本文に `lecture_id: "lecture-4"` が付き、従来の項目(`participant_id`、`timestamp`、`score_numerator`、`score_denominator`、`answers`)は従来どおり付く。記録された試行は lecture-4 として記録される。lecture-5・6 も同じ。〔検証: 自動テスト〕
19. **振り返りページへの引き継ぎ**(置き換え(#34): (c)「講義IDなしは固定割当」と (d)「未登録の講義IDは 404」は、[lecture-selection.md](./lecture-selection.md) の What 4節・AC15 に置き換えた。講義は選択で決まり、選択済みで選択と異なる値は 403(未登録の値を含む)、空の値は 404 のまま、未選択は選択の画面へ 302。以下は #33 の時点の内容の記録): 次がすべて成り立つ。(a) `/lecture?lecture_id=lecture-4` のページの「振り返り画面へ進む」のリンク先は `/reflect?lecture_id=lecture-4` である(lecture-5・6 も同じ)。ログイン ID `P01` で講義IDを付けずに開いた `/lecture` のリンク先は `/reflect?lecture_id=lecture-1`(表示している講義)である。(b) ログインした状態で `/reflect?lecture_id=lecture-4` を開くと 200 が返り、そのページで送る `/chat` の本文に `lecture_id: "lecture-4"` が付き(従来の項目は従来どおり)、LAD の取得(`/api/participants/<id>/lad`)のクエリに `lecture_id=lecture-4` が付く。(c) 講義IDなしで `/reflect` を開くと、`/chat` の本文と LAD の取得に講義IDは付かず、従来どおり固定割当の講義になる。(d) `/reflect?lecture_id=lecture-7`(未登録)は 404 を返す。(e) ログイン ID `P01` で lecture-4 の視聴ログと小テストを講義ID付きで記録した後、`lecture_id=lecture-4` を付けた LAD の取得は、その視聴と小テストの結果を返す。〔検証: 自動テスト〕
20. **後方互換(講義IDなしの要求)**(置き換え(#34): 固定割当は廃止した。講義IDなしの要求は、保存された選択の講義で処理し、未選択は 409。[lecture-selection.md](./lecture-selection.md) の What 4節・AC10・14・17。以下は #33 の時点の内容の記録): 講義IDを付けない `/chat`・`/api/viewing-log`・`/api/quiz-attempts`・LAD の取得は、従来どおり参加者IDの固定割当(`1`/`2`/`3` → lecture-1/2/3、それ以外は lecture-1)で講義を決め、従来と同じ応答を返す(既存の契約テスト `test_viewing_log_gas_contract.py`・`test_quiz_attempts_gas_contract.py` が変更なしで成功する)。〔検証: 自動テスト〕
21. **対話ログの講義ID**(置き換え(#34): (c)「講義IDなしは固定割当」と (d)「未登録の講義IDは 404」は、[lecture-selection.md](./lecture-selection.md) の What 4節・AC13・14・17 に置き換えた。講義IDなしは選択した講義で保存、未選択は 409、選択と異なる値(未登録を含む)は 403、空文字は 400。以下は #33 の時点の内容の記録): 次がすべて成り立つ。(a) `/reflect?lecture_id=lecture-4` のページで、終了ボタンを押したときと、発言済みでページ離脱が確定したときの、それぞれの `/api/dialog-log` の本文に `lecture_id: "lecture-4"` が付き、`participant_id` と `end_method`(`end_button` / `page_leave`)は従来どおり付く。(b) ログイン ID `P01` で、講義IDに `lecture-4` を付けて `/chat` を2回送った後、`lecture_id: "lecture-4"` を付けて `/api/dialog-log`(`end_button`)を送ると 200 が返り、`dialog_logs` には講義ID `lecture-4` の対話ログが1件だけ保存され、その発言は送受信した4件(`user`・`assistant`・`user`・`assistant`)である。lecture-1 の対話ログは作られない。`page_leave` でも同じ。(c) 講義IDを付けない `/api/dialog-log` は、従来どおり固定割当の講義で保存する(AC13(d))。(d) 未登録の講義ID(`lecture-7`)を付けた `/api/dialog-log` は 404 を返し、対話ログを保存・変更しない(`/chat` と同じ扱い。前提のとおり、現状の保存の処理は講義の存在を検査しない)。〔検証: 自動テスト〕

## 制約・関連機能

- 関連仕様: `docs/spec/application-usecase.md#LectureCatalog`、`docs/spec/framework-drivers-layer.md#db`・参加者導線・HTTP 契約、`docs/spec/interfaces-layer.md#default_lecture`、`docs/spec/domain-model.md#LectureOutline`、`docs/spec/subtitle-display.md`(#36)、`docs/spec/subtitle-formatting.md`(#44、AC13 のフォールバック)、`docs/spec/participant-login.md`(AC25)、`docs/spec/dialog-log-save.md`(対話ログの保存 API。本 PBI で任意の `lecture_id` を加える)、`docs/spec/srt-proofreading.md`(#35。lecture-4〜6 は対象外)。
- 共有IF: 型(`Question`、`QuizDefinition`、`LectureOutline`)は変えない。小テストの題名・説明の取得元(`_QUIZ_MODULES`)と講義カタログの両方に登録が要る(登録漏れは、ページ表示の失敗になる)。API の本文・クエリの `lecture_id` は、サーバー側ですでに任意項目として受け付けている(視聴ログ、小テスト、チャット、LAD)。送る側(ページの JS と、ページに埋め込む値)を足す。`/api/dialog-log` だけは、本文の任意項目 `lecture_id` を新たに受け付ける(共有IFの変更。`dialog-log-save.md` の保存 API の契約を AC16 で更新する)。対話ログの JSON の形(`dialog-log-save.md` の共有IF)は変えない(`lecture_id` に入る値が、付けた講義になるだけ)。`/reflect` は、任意のクエリ `lecture_id` を新たに受け付ける。
- スプリント009(#44)・#32(HTTPS)が同じ作業ツリーで未コミット。`framework_drivers/platform/main.py`(#44・#32 が変更中。本 PBI は `_QUIZ_MODULES` と `/reflect` を変更)、`tests/test_api/test_lecture_route.py`(#44 が変更中)、`tests/test_framework_drivers/js/lecture_subtitles.mjs`(#44 が変更中。本 PBI では変更しない見込み)が重なる。講義ページ・振り返りページの JS とテンプレート(`api_client.js`、`player.js`、`quiz.js`、`chat_panel.js`、`reflect_app.js`、`lecture.html`、`reflect.html`)は #44・#32 の差分に含まれない(`git diff --stat` で確認)。`dialog_log.js`、`leave_guard.js`、`save_dialog_log_controller.py`、`wiring.py`、`reflect_leave_guard.mjs`、`reflect_dialog_log.mjs` も、作業ツリーの変更一覧(`git status`)に含まれない。提出時は差分を PBI ごとに分ける必要がある。
- 実験開始(2026-10-27)に文系の協力者が講義を使うには、講義IDを付けた URL(`/lecture?lecture_id=lecture-4` など)を協力者に渡す必要がある(選択画面は別 PBI)。協力者が講義ページの「振り返り画面へ進む」から振り返りページへ進めば、AI チューター・LAD・対話ログはその講義になる。

### 実現性の点検

- 影響ファイルの見込み:
  - 追加(src、データ定義。大きさに数えない): `framework_drivers/db/learning/quiz_definitions/lecture_4.py`・`lecture_5.py`・`lecture_6.py`、`framework_drivers/db/learning/lecture_outlines/lecture_4.py`・`lecture_5.py`・`lecture_6.py`
  - 変更(src、登録): `framework_drivers/db/learning/static_lecture_catalog.py`、`framework_drivers/platform/main.py`(`_QUIZ_MODULES`)
  - 変更(src、講義ページの講義ID): `framework_drivers/platform/templates/lecture.html`(講義IDの埋め込み、振り返りへのリンク)、`framework_drivers/platform/static/js/common/api_client.js`(視聴ログ・小テストの本文、LAD 取得)、`framework_drivers/platform/static/js/lecture/player.js`、`framework_drivers/platform/static/js/lecture/quiz.js`
  - 変更(src、振り返りページ): `framework_drivers/platform/main.py`(`/reflect` が講義IDを受け取り、カタログで検証してページに渡す。未登録は 404)、`framework_drivers/platform/templates/reflect.html`(講義IDの埋め込み)、`framework_drivers/platform/static/js/reflect/chat_panel.js`(`/chat` の本文)、`framework_drivers/platform/static/js/reflect/reflect_app.js`(LAD の取得、対話ログの2モジュールへの受け渡し)
  - 変更(src、対話ログ): `interfaces/tutoring/controllers/save_dialog_log_controller.py`(本文の講義IDを読む。未登録は 404)、`framework_drivers/platform/wiring.py`(Controller に講義カタログを渡す場合。既存の `GetLearningSnapshotController` は Controller で講義の存在を検査している)、`api_client.js`(`postDialogLog`・`postDialogLogOnLeave` の本文)、`framework_drivers/platform/static/js/reflect/dialog_log.js`、`framework_drivers/platform/static/js/reflect/leave_guard.js`
  - 追加(データ): `lectures/lecture-4/subtitles.srt`、`lectures/lecture-5/subtitles.srt`、`lectures/lecture-6/subtitles.srt`
  - 変更(ドキュメント): `lectures/README.md`、`docs/spec/application-usecase.md`、`docs/spec/framework-drivers-layer.md`(#44 も変更中)、`docs/spec/dialog-log-save.md`
  - 合計: src 19 ファイル(データ定義の追加6、ロジックの変更13)、字幕3、ドキュメント4。
- テストの更新一覧:

  | 区分 | ファイル | 対応AC | 内容 |
  |---|---|---|---|
  | 拡張 | `tests/test_framework_drivers/db/learning/test_static_lecture_catalog.py` | AC1・2 | lecture-4〜6 の登録と SRT の実在 |
  | 拡張 | `tests/test_framework_drivers/db/learning/test_quiz_definitions.py` | AC4 | 付録A との一致 |
  | 拡張 | `tests/test_framework_drivers/db/learning/test_lecture_outlines.py` | AC9 | 講義情報の構造 |
  | 拡張 | `tests/test_api/test_lecture_route.py`(#44 と同じファイル) | AC3・5・7・12・19(a) | 講義ページの表示、リンク先 |
  | 拡張 | `tests/test_api/test_lecture_quiz_submit.py` | AC6・18(サーバー側) | 講義ID付きの小テストの記録 |
  | 拡張 | `tests/test_api/test_viewing_log_api.py` | AC17(サーバー側) | 講義ID付きの視聴ログの記録 |
  | 拡張 | `tests/test_api/test_reflect_ui.py` | AC19(b)〜(d) | `/reflect?lecture_id=` の 200・埋め込み・404、講義IDなしの従来どおり |
  | 拡張 | `tests/test_interfaces/test_tutoring/test_save_dialog_log_controller.py` | AC21(b)〜(d)・AC13(d) | 本文の講義IDで決まること、未登録の 404。既存の固定マップの検査は期待値を変えない(Controller の組み立てに引数が増える場合、組み立て部分だけ直す) |
  | 拡張 | `tests/test_framework_drivers/js/reflect_leave_guard.mjs` | AC21(a)・AC13(d) | 講義IDを渡したときの離脱時の本文(`lecture_id` を含む3つ)を加える。既存の B4「2つだけ」の検査は、講義IDを渡さない場合の検査として残す |
  | 拡張 | `tests/test_framework_drivers/js/reflect_dialog_log.mjs` | AC21(a) | 終了ボタンの保存要求に講義IDが渡ること(差し替えた `postDialogLog` が講義IDも記録する) |
  | 新規 | `tests/test_lectures/` の新しいファイル | AC8 | 字幕の構造と同一性(`test_srt_proofread_structure.py` の `LECTURES` には入れない) |
  | 新規 | `tests/test_chat_lad/` の新しいファイル | AC11 | 講義ID指定の AI チューターの文脈 |
  | 新規 | `tests/test_framework_drivers/js/` の新しい `.mjs` と、それを起動する `tests/test_framework_drivers/test_*.py` | AC17・18 | 講義ページの JS が送る講義ID(既存の `lecture_player_seek_count.mjs` は引数4つを記録する形のため、別ファイルにする) |
  | 新規または拡張 | `tests/test_framework_drivers/js/` の新しい `.mjs`、または `reflect_chat_panel_input.mjs` の拡張 | AC19(b)(c) | 振り返りページの JS が送る講義ID(`/chat` の本文、LAD の取得) |
  | 新規 | `tests/test_api/` の新しいファイル | AC19(e)・AC21(b)〜(d) | LAD の講義ID指定、対話ログの講義ID(API を通して) |
  | 変更しない | `test_dialog_log_api.py`、`test_viewing_log_gas_contract.py`、`test_quiz_attempts_gas_contract.py` | AC13(d)・AC20 | 後方互換として、変更なしで成功することを確かめる |
  | 変更しない | `test_srt_proofread_structure.py`、`test_subtitle_display_data.py`(#44)、`lecture_subtitles.mjs`(#44)、`lecture_player_seek_count.mjs`、`test_learner_lecture_mapping.py`、`test_save_dialog_log.py`(ユースケース) | — | `postViewingLog` の差し替えは5つ目の引数を無視するため、講義IDの追加の影響を受けない見込み(未確認: コードを読んだ推測)。ユースケースは講義IDを受け取る形のままで変えない見込み |
- 衝突・矛盾・依存の不足:
  - 既存仕様 `framework-drivers-layer.md` の「`lecture_id` は URL に含めない」と、`dialog-log-save.md` の「本文は2つだけ」は、本 PBI の決定(論点10 = A、論点11 = a)と食い違う。AC16 で両仕様を直す。
  - 対話ログの保存は講義の存在を検査しない(前提の実行結果)。本文の講義IDを読むようにすると未登録の講義IDで空の対話ログが保存されうるため、AC21(d) で 404 にする(`/chat`・`/reflect` と同じ扱い)。
  - 新しい依存: なし。型(`Question`、`QuizDefinition`、`LectureOutline`、対話ログの JSON)の変更: なし。API の受け付け項目の変更: `/api/dialog-log` の本文に任意の `lecture_id`、`/reflect` に任意のクエリ `lecture_id` を加える(どちらも、付けないときは従来どおり)。
- テスト不能・曖昧なAC:
  - AC10(講義情報の内容の妥当性)、AC14(実動画の再生、字幕の目視、小テストの操作)、AC15(実 LLM の応答、LAD の表示): 自動テストでは確認できないため PO確認(AC15 の対話ログの中身は AI実行)。
  - ページ離脱時の保存の実ブラウザでの到達は、AC21 では JS の論理(本文)とサーバーの保存を分けて自動テストで確かめる。実ブラウザでの到達の確認は `dialog-log-save.md` の B4 の範囲で、本 PBI では行わない。
  - その他: なし。
- 規模:
  - src のデータ定義(大きさに数えない): 約 580 行(小テスト3本 各約 110 行、講義情報3本 各約 85 行。既存の lecture_1〜3 の行数 84〜106 行からの見積もり)。
  - **src のロジック(大きさに数える。データ定義を除く): 合計 約 110 行**(基準 300 行を下回る)。
    - 登録 約 30 行(カタログ 約 25、`main.py` の `_QUIZ_MODULES` 約 5)
    - 講義ページの講義ID 約 25 行(`lecture.html` 約 2、`api_client.js` 約 15、`player.js` 約 3、`quiz.js` 約 3)
    - 振り返りページの引き継ぎ 約 25 行(`main.py` の `/reflect` 約 15、`reflect.html` 約 1、`chat_panel.js` 約 4、`reflect_app.js` 約 5)
    - 対話ログの講義ID 約 30 行(`save_dialog_log_controller.py` 約 12、`wiring.py` 約 2、`api_client.js` 約 8、`dialog_log.js` 約 3、`leave_guard.js` 約 3、`reflect_app.js` 約 2)
  - **経路の推奨: 標準経路(1 PBI、タスク1つ)**。理由: ロジックは約 110 行で基準を大きく下回る。ファイル数は多い(src 19)が、半数はデータ定義と1〜5行の変更で、`main.py` と `api_client.js` を登録・講義ページ・振り返りページ・対話ログの複数のまとまりが共有するため、分けても直列の部分が多く、タスク分割・統合検証の手間が利点を上回る。
  - 分割案(並列経路を選ぶ場合): (1) 登録(データ定義6、カタログ、`_QUIZ_MODULES`、字幕3。AC1〜12・14 と AC16 の登録部分)と、(2) 講義IDの伝搬(講義ページ・振り返りページのテンプレートと JS、`/reflect`、対話ログの Controller と組み立て。AC13・15・17〜21 と AC16 の伝搬部分)。所有ファイルは `main.py`(`_QUIZ_MODULES` と `/reflect`)だけが重なるため、`main.py` を (2) に持たせるか、(2) を (1) の後にする。(2) の自動テストのうち lecture-4 を使うもの(AC19(b)(e)・AC21(b))は (1) の登録に依存する(lecture-2 などで書けば依存しない)。
- 未解決の論点: なし(論点10・11 は PO決定 2026-10-26 で解決。前提の「POの意図」に記録)

### 解決した論点の記録

- 論点10(振り返りページへの講義IDの引き継ぎ): A に決定(PO 2026-10-26)。採らなかった案: B(ブラウザの保存領域で引き継ぐ。別タブで引き継がれず、画面から確かめにくい)、C(引き継がない。AI チューターと LAD が lecture-1 のまま)。LAD の取得を含める理由: 視聴ログと小テストが lecture-4 として記録されるため、LAD を講義IDなしで取得すると lecture-1 の記録(空)が表示され、AI チューターのプロンプトと画面が食い違う。
- 論点11(対話ログに会話が入らない件): a に決定(PO 2026-10-26)。採らなかった案: b(対話ログを変えず、空の対話ログを既知の制約として固定)、c(チャットに講義IDを付けない)。

## 付録A: 小テストの本文(PO 提供、2026-10-26)

正解は記号で示す。データにするのは「問題文」「A〜D」「正解」の列だけで、「見出し」と記号は文面に含めない(論点5)。解説は使わない(論点3)。

### lecture-4 律令制(小テスト：律令制の仕組み)

| 問 | 見出し | 問題文 | A | B | C | D | 正解 |
|---|---|---|---|---|---|---|---|
| 1 | 律と令の違い | 「律」と「令」は、それぞれどのような決まりでしょうか。 | 律は貴族だけが守る決まり、令は平民だけが守る決まり。 | 律は犯罪と刑罰についての決まり、令は政治や税などについての決まり。 | 律は地方で使う決まり、令は都で使う決まり。 | 律は神様や祭りについての決まり、令は軍事についての決まり。 | B |
| 2 | 中央の政治 | 動画では、中央で決まった政策が実施されるまでの流れを、どのように説明していましたか。 | 八省が政策を決め、国民の投票を経て、天皇が実施する。 | 地方の代表者が政策を決め、太政官を通さずに実施する。 | 神祇官が政策を決め、弾正台がすべての実務を担当する。 | 太政官の上位の貴族たちが話し合い、天皇の許可を得て、八省が実務を担当する。 | D |
| 3 | 官位相当制 | 「官位相当制」とは、どのような制度でしょうか。 | 役人の位に応じて、就く役職が対応している制度。 | 役人が希望すれば、どの役職にも自由に就ける制度。 | 同じ役職を、すべての貴族が順番に担当する制度。 | 税を多く納めた人ほど、高い役職に就ける制度。 | A |
| 4 | 租・調・庸 | 「租・調・庸」の説明として、正しい組み合わせはどれですか。 | 租は各地の特産品、調は都での労働の代わりの布、庸は稲の一部。 | 租は都での労働の代わりの布、調は稲の一部、庸は各地の特産品。 | 租は稲の一部、調は各地の特産品、庸は都での労働の代わりの布。 | 租は稲の一部、調は都での労働の代わりの布、庸は各地の特産品。 | C |
| 5 | 応用問題 | ある地方で暮らす人が、「税として納める品物を都まで運ぶように」と命じられました。運ぶ途中の食料も、自分で用意しなければなりません。この負担に当たるものはどれですか。 | 雑徭 | 運脚 | 防人 | 衛士 | B |

### lecture-5 心理カウンセリングの基礎(小テスト：心理カウンセリングの基礎)

| 問 | 見出し | 問題文 | A | B | C | D | 正解 |
|---|---|---|---|---|---|---|---|
| 1 | 臨床心理学とは | 動画では、臨床心理学と一般の心理学の違いをどのように説明していましたか。 | 臨床心理学は、主に患者さんの心理を扱う。 | 臨床心理学は、人付き合いがうまくなる方法を扱う。 | 臨床心理学は、主に営業の場面で相手の心を読む方法を扱う。 | 臨床心理学は、心理学の知識を使わずに相談を受ける。 | A |
| 2 | カウンセリングでの関わり方 | 動画では、ロジャーズのカウンセリングについて「非指示的」で「支持的」と説明していました。これに最も近い関わり方はどれですか。 | 相談者が迷わないように、支援者が進む道を決める。 | 相談者に影響を与えないように、気持ちへの反応を控える。 | 相談者が自分で考えることを大切にしながら、支える。 | 相談者が話す内容を評価し、間違いをその都度指摘する。 | C |
| 3 | ラポール | 動画に出てきた「ラポール」とは、何を指す言葉ですか。 | 初回の面接で、相談内容を確認すること。 | 相談者と支援者の間にある信頼関係。 | 面接の時間や料金についての決まり。 | 治療が終わった後に、様子を確認すること。 | B |
| 4 | 治療構造 | 動画では、時間・頻度・場所・料金などを決める「治療構造」が大切だと説明していました。その説明に合うものはどれですか。 | 相談者の調子に合わせて、面接の長さを毎回自由に変える。 | 長く続けやすくするため、料金はできるだけ安く設定する。 | 治療法が決まっていれば、時間や場所は決めなくてもよい。 | 継続して取り組める条件を決め、その枠組みをできるだけ守る。 | D |
| 5 | 応用問題 | ある相談室では、相談者の調子がよい日は面接を10分で終え、調子が悪い日は予定を超えて2時間話を聞いていました。その結果、次の相談者を待たせたり、「前の人より自分の時間が短い」と不満が出たりしました。動画の説明に照らすと、まず見直すべきことはどれですか。 | 面接時間の決め方と、その時間を守る仕組み。 | 相談者を「患者さん」と呼ぶか「クライアント」と呼ぶか。 | 支援者が知っている心理療法の種類。 | 面接の最初に雑談をするかどうか。 | A |

### lecture-6 言語の仕組み(小テスト：言語の仕組み（音声・音韻・語）)

| 問 | 見出し | 問題文 | A | B | C | D | 正解 |
|---|---|---|---|---|---|---|---|
| 1 | 言語とは何か | 動画では、言語を一言でどのように説明していましたか。 | 気持ちを表す声の集まり | 記号の体系 | 文字の書き方の決まり | ものの形を写した絵の集まり | B |
| 2 | 音と意味の結びつき | 動画では「猫をカバと呼んでもよかった」と説明していました。この説明に最も近いものはどれですか。 | 猫とカバは、言葉の上では同じ動物である。 | 呼び名は、一人ひとりが自由に変えても相手に伝わる。 | 動物の姿が分かれば、その呼び名も自然に分かる。 | 呼び名が「猫」でなければならない理由はなく、約束によって結びついている。 | D |
| 3 | 線条性 | 言語の特徴である「線条性」とは、どのようなことでしょうか。 | 音を、時間の流れに沿って順に並べること。 | 一つの単語に含まれる音を、すべて同時に出すこと。 | 同じ音を使えば、順番を変えても意味が変わらないこと。 | 話した内容を、必ず横一列の文字で書き表せること。 | A |
| 4 | 二重分節 | 動画では「僕はたぬきです」という文を使って、二重分節を説明していました。その分け方に合うものはどれですか。 | 文を前半と後半に分け、それぞれの意味を考える。 | 文を文字に分け、さらに文字を線に分ける。 | 文を「僕／は／たぬき／です」のように語に分け、さらに語を音に分ける。 | 文を語に分け、それぞれの語を別の言語に訳す。 | C |
| 5 | 応用問題 | 「さる」と「まる」では、最初の子音が /s/ から /m/ に変わると、別の意味の語になります。この例から分かることはどれですか。 | /s/ という音だけで、「猿」という動物を表している。 | 音そのものに意味がなくても、語の意味を区別する働きがある。 | /m/ という音には、どの語でも「丸い」という意味がある。 | 一つの音を変えても、語全体の意味は変わらない。 | B |

## 変更理由

- issue #33(FR-61、2026-10-26): 文系レベル3本(lecture-4〜6)を講義カタログに登録する仕様を新規に起草した。範囲は PO決定(2026-10-26)の「登録のみ」。講義ページから講義IDが API に渡らない現状を実行で確認し、範囲の衝突を論点1として挙げた。
- issue #33(2026-10-26、PO決定 論点1〜9 の反映): 論点1 = B(講義ページが講義IDを送る。対話ログは別 PBI)により、目的・What・既知の制約を更新し、AC17〜21 を追加、AC13・15・16 を変更した。論点3(解説は使わない)により付録A から解説を外し、AC4・5・10 を変更した。論点4・5・8 により AC1・4・5 と付録A の文面を確定した。論点6・7 により字幕の素材(lecture-4 は仮データでない)とバイト列の同一性(SHA-256)を前提に記録し、AC8 の値を確定した。論点9 により AC9・10 を補った。論点2 によりロジック行数を再計算した(約 55〜95 行)。反映中に、チャット・LAD が振り返りページにあること(論点10)と、対話ログに会話が入らないこと(論点11)を実行で確認し、未解決の論点として追加した。
- issue #33(2026-10-26、PO決定 論点10 = A・論点11 = a の反映): 論点10 により、振り返りページが URL の講義ID(`/reflect?lecture_id=`)を `/chat` と LAD の取得に付けることを What 8 に確定し、AC19 を確定した(講義IDなしで開いた講義ページのリンク先、LAD の講義ID指定の結果(e)を補った)。論点11 により、対話ログの保存(終了ボタン、ページ離脱)に講義IDを付けることを本 PBI に含め(FR-62 の一部を前倒し)、What 9 を追加、AC21 を「対話ログの現状維持」から「講義IDを付けるとその講義の会話を保存、付けないと従来どおり」に変更し、AC13(d)・AC15・AC16 を変更した。未登録の講義IDの対話ログの保存が 200 で空の対話ログを作ることを実行で確認し、AC21(d) で 404 とした(`/chat`・`/reflect` と同じ扱い)。目的、範囲外(FR-60・FR-63・FR-62 の残り・割当の変更)、既知の制約、共有IF、実現性の点検(影響ファイル、テストの更新一覧、ロジック約 110 行、標準経路の推奨、分割案)を更新し、未解決の論点を解消した。
