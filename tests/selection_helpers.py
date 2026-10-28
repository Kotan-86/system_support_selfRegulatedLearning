# 仕様: docs/spec/lecture-selection.md#受入基準
"""講義の選択(PBI #34)のテスト補助。

【test-writer が定めた公開IF(URL・フォームの項目名)】仕様に具体名がないため、ここで固定する。
  - GET  /select-lecture            選択の画面。講義ごとの選択肢は name="lecture_id" と value="<講義ID>" を持つ
                                     要素(submit ボタンまたは radio)で、カタログの順に並ぶ。
  - POST /select-lecture            最初の操作(フォーム項目 lecture_id)。200 で確認の画面を返す。保存しない。
                                     確認の画面は、講義の題名と「一度選ぶと変更できない」と、
                                     action が /select-lecture/confirm のフォーム(lecture_id を持つ)を含む。
  - POST /select-lecture/confirm    確定(フォーム項目 lecture_id)。成功も、選択済みで別の講義が送られた場合も 302 → /lecture。
                                     カタログにない値・空・項目なしは 400(何も保存しない)。
期待値の出典: 講義の一覧・題名・動画は既存の build_near_term_lectures()(#33 で登録済み)と、仕様の系統の値。
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from tests.login_helpers import location_path, login_as
from tests.test_lectures.humanities_data import HUMANITIES_BY_ID

SELECT_PATH = "/select-lecture"
CONFIRM_PATH = "/select-lecture/confirm"
WARNING_TEXT = "一度選ぶと変更できない"

ROOT = Path(__file__).resolve().parent.parent


def catalog_lectures():
    """テスト時点のカタログの全講義(登録順)。"""
    from framework_drivers.db.learning.static_lecture_catalog import build_near_term_lectures

    return build_near_term_lectures()


def all_lecture_ids() -> list[str]:
    return [str(lecture.id) for lecture in catalog_lectures()]


# 仕様: What 1節(lecture-1〜3 が「理系」、lecture-4〜6 が「文系」)
TRACK_OF = {
    "lecture-1": "理系", "lecture-2": "理系", "lecture-3": "理系",
    "lecture-4": "文系", "lecture-5": "文系", "lecture-6": "文系",
}
VIDEO_IDS = {
    "lecture-1": "Y2HC0I8cTAI",
    "lecture-2": "1MuwwFipX9o",
    "lecture-3": "Sa06YB2oXyw",
    **{lid: lec.video_id for lid, lec in HUMANITIES_BY_ID.items()},
}
QUIZ_TITLES = {
    "lecture-1": "球の表面積に関する理解度テスト",
    "lecture-2": "モンティ・ホール問題：直感と論理のクイズ",
    "lecture-3": "3囚人問題：確率のパラドックスに挑戦",
    **{lid: lec.quiz_title for lid, lec in HUMANITIES_BY_ID.items()},
}


def choose(client, lecture_id: str):
    """選択の確定を送る(画面の確定の操作と同じ)。"""
    return client.post(CONFIRM_PATH, data={"lecture_id": lecture_id})


def login_unselected(client, participant_id: str, **kwargs):
    """ログインするが、講義は選ばない(未選択の協力者)。"""
    return login_as(client, participant_id, lecture=None, **kwargs)


def login_and_choose(client, participant_id: str, lecture_id: str):
    """ログインし、画面の操作(確定)で講義を選ぶ。"""
    login_unselected(client, participant_id)
    response = choose(client, lecture_id)
    assert response.status_code == 302, (
        f"選択の確定が成功しない: {response.status_code} {response.get_data(as_text=True)[:200]}"
    )
    return response


def learning_sessions(tmp_path: Path) -> list[tuple[str, str]]:
    """learning_sessions の (学習者, 講義) の一覧。"""
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return sorted(
            (r[0], r[1])
            for r in conn.execute("SELECT learner_id, lecture_id FROM learning_sessions")
        )
    finally:
        conn.close()


def started_at_of(tmp_path: Path, learner: str, lecture_id: str) -> str:
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return conn.execute(
            "SELECT started_at FROM learning_sessions WHERE learner_id=? AND lecture_id=?",
            (learner, lecture_id),
        ).fetchone()[0]
    finally:
        conn.close()


def count_rows(tmp_path: Path, db: str, table: str) -> int:
    conn = sqlite3.connect(str(tmp_path / db))
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def option_values(html: str) -> list[str]:
    """選択の画面の、name="lecture_id" を持つ要素の value(出現順)。"""
    values = []
    for tag in re.findall(r"<[^>]*\bname=\"lecture_id\"[^>]*>", html):
        match = re.search(r"\bvalue=\"([^\"]*)\"", tag)
        values.append(match.group(1) if match else "")
    return values


def is_selection_redirect(response) -> bool:
    return response.status_code == 302 and location_path(response) == SELECT_PATH


_REFLECT_LECTURE_RE = re.compile(r"window\.__REFLECT_LECTURE_ID__\s*=\s*(.+?);\s*$", re.M)


def embedded_reflect_lecture_id(html: str):
    match = _REFLECT_LECTURE_RE.search(html)
    return json.loads(match.group(1)) if match else None


def lecture_page_shows(html: str, lecture_id: str) -> bool:
    """講義の画面が lecture_id の講義(画面の講義ID・動画)か。"""
    return f"<strong>{lecture_id}</strong>" in html and VIDEO_IDS[lecture_id] in html


def lecture_page_has_no_other(html: str, lecture_id: str) -> bool:
    return all(v not in html for lid, v in VIDEO_IDS.items() if lid != lecture_id)


def quiz_payload_for(lecture_id: str, lecture_field=...) -> dict:
    """lecture_id の講義の全問正解の小テスト本文。lecture_field=... なら lecture_id の項目を含めない。"""
    from framework_drivers.db.learning.static_lecture_catalog import build_near_term_lecture

    quiz = build_near_term_lecture(lecture_id=lecture_id).quiz_definition
    answers = [
        {"question_index": q.index, "selected_answer": q.correct_answer, "is_correct": 1}
        for q in quiz.questions
    ]
    body = {
        "timestamp": "2026-10-28T12:00:00",
        "score_numerator": len(answers),
        "score_denominator": len(answers),
        "answers": answers,
    }
    if lecture_field is not ...:
        body["lecture_id"] = lecture_field
    return body


def viewing_body(lecture_field=..., current_time: int = 15, action: str = "play") -> dict:
    body = {
        "time_stamp": "2026-10-28T11:18:42",
        "current_time": current_time,
        "action": action,
        "duration": 0,
    }
    if lecture_field is not ...:
        body["lecture_id"] = lecture_field
    return body
