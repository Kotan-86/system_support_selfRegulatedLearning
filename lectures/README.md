# 講義アセット（近い実験）

各講義の字幕（SRT）は `lectures/{lecture_id}/subtitles.srt` に配置する。

| lecture_id | participant_id | 動画（YouTube） | SRT |
|------------|----------------|-----------------|-----|
| `lecture-1` | `1` | [Y2HC0I8cTAI](https://www.youtube.com/watch?v=Y2HC0I8cTAI) | `lecture-1/subtitles.srt` |
| `lecture-2` | `2` | [1MuwwFipX9o](https://www.youtube.com/watch?v=1MuwwFipX9o) | `lecture-2/subtitles.srt` |
| `lecture-3` | `3` | [Sa06YB2oXyw](https://www.youtube.com/watch?v=Sa06YB2oXyw) | `lecture-3/subtitles.srt` |
| `lecture-4`(律令制) | なし(`?lecture_id=` で指定) | [a-EqZb_Mpvk](https://www.youtube.com/watch?v=a-EqZb_Mpvk) | `lecture-4/subtitles.srt` |
| `lecture-5`(心理カウンセリングの基礎) | なし(`?lecture_id=` で指定) | [lLcZEIsyHvg](https://www.youtube.com/watch?v=lLcZEIsyHvg) | `lecture-5/subtitles.srt` |
| `lecture-6`(言語の仕組み(音声・音韻・語)) | なし(`?lecture_id=` で指定) | [psbIrfy09Pg](https://www.youtube.com/watch?v=psbIrfy09Pg) | `lecture-6/subtitles.srt` |

lecture-4〜6 は文系の講義で、参加者の固定割当にはない。`/lecture?lecture_id=lecture-4` のように URL で指定して開く(PBI #33。仕様: [docs/spec/humanities-lectures.md](../docs/spec/humanities-lectures.md))。字幕は PO から受け取った SRT をバイト列を変えずに置いたもの。表示用の整形済み字幕(`subtitles.display.srt`)は置かない。

仕様: [docs/spec/application-usecase.md](../docs/spec/application-usecase.md#LectureCatalog)

## 字幕の校正（lecture-1）

`lecture-1/subtitles.srt` は、自動字幕の誤字脱字・誤認識を校正済みである（PBI #35。修正 107 件。番号・時刻・ブロックの構成は元と同じで、変わったのはテキストだけ）。

| ファイル | 内容 |
|----------|------|
| `lecture-1/subtitles.srt` | アプリが読む字幕（校正後） |
| `lecture-1/subtitles.proofread.srt` | 修正案（反映後も残す。`subtitles.srt` とバイト列は同じ） |
| `lecture-1/proofread-diff.md` | 差分一覧（番号、時刻、修正前後、理由、確信度） |

校正前の字幕は git の履歴から取り出せる。仕様: [docs/spec/srt-proofreading.md](../docs/spec/srt-proofreading.md)

## 字幕の校正（lecture-2）

`lecture-2/subtitles.srt` は、自動字幕の誤字脱字・誤認識を校正済みである（PBI #35。修正 123 件。番号・時刻・ブロックの構成は元と同じで、変わったのはテキストだけ）。

| ファイル | 内容 |
|----------|------|
| `lecture-2/subtitles.srt` | アプリが読む字幕（校正後） |
| `lecture-2/subtitles.proofread.srt` | 修正案（反映後も残す。`subtitles.srt` とバイト列は同じ） |
| `lecture-2/proofread-diff.md` | 差分一覧（番号、時刻、修正前後、理由、確信度） |

校正前の字幕は git の履歴から取り出せる。仕様: [docs/spec/srt-proofreading.md](../docs/spec/srt-proofreading.md)

## 字幕の校正（lecture-3）

`lecture-3/subtitles.srt` は、自動字幕の誤字脱字・誤認識を校正済みである（PBI #35。修正 73 件。番号・時刻・ブロックの構成は元と同じで、変わったのはテキストだけ）。

| ファイル | 内容 |
|----------|------|
| `lecture-3/subtitles.srt` | アプリが読む字幕（校正後） |
| `lecture-3/subtitles.proofread.srt` | 修正案（反映後も残す。`subtitles.srt` とバイト列は同じ） |
| `lecture-3/proofread-diff.md` | 差分一覧（番号、時刻、修正前後、理由、確信度） |

校正前の字幕は git の履歴から取り出せる。仕様: [docs/spec/srt-proofreading.md](../docs/spec/srt-proofreading.md)

## 字幕の整形（表示専用）

講義ページに表示する字幕は、講義ごとの整形済みファイルがあれば、それを使う（PBI #44）。語や言い回しの途中で切れた字幕を、1文として意味が伝わる単位にまとめ、フィラー（「えっと」「えー」、単独の「え」「ま」「まあ」など）を除いたものである。

| ファイル | 内容 |
|----------|------|
| `lecture-N/subtitles.display.srt` | 表示専用の整形済み字幕 |
| `lecture-N/display-fillers.md` | 整形時に除いたフィラーの一覧 |

- **用途**: 講義ページの字幕表示だけに使う。AIチューターの文脈、保存データ、`subtitles.srt` には使わない（これらは元の `subtitles.srt` のまま）。
- **形式**: UTF-8（BOMなし）、改行は CRLF、1ブロック3行（番号、時刻、1行の文）。
- **除去一覧の列**: 元の番号 / 位置（その元キューの文の中の、0 から数えた文字の位置） / 除いた語 / メモ（「ええ」の判断の理由など）。
- **ないとき・読めないとき**: 整形済みファイルがない、または読めない（壊れている、件が1つもない）講義は、`subtitles.srt` をそのまま表示する。
- **`subtitles.srt` を変更したとき**（校正など）: 整形済みファイルの作り直しが必要である。`tests/test_lectures/test_subtitle_display_data.py` が、文字の保存の検査で食い違いを検出する。

仕様: [docs/spec/subtitle-formatting.md](../docs/spec/subtitle-formatting.md)
