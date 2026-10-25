# 講義アセット（近い実験）

各講義の字幕（SRT）は `lectures/{lecture_id}/subtitles.srt` に配置する。

| lecture_id | participant_id | 動画（YouTube） | SRT |
|------------|----------------|-----------------|-----|
| `lecture-1` | `1` | [Y2HC0I8cTAI](https://www.youtube.com/watch?v=Y2HC0I8cTAI) | `lecture-1/subtitles.srt` |
| `lecture-2` | `2` | [1MuwwFipX9o](https://www.youtube.com/watch?v=1MuwwFipX9o) | `lecture-2/subtitles.srt` |
| `lecture-3` | `3` | [Sa06YB2oXyw](https://www.youtube.com/watch?v=Sa06YB2oXyw) | `lecture-3/subtitles.srt` |

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
