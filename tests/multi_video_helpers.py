# 仕様: docs/spec/multi-video-learning.md#受入基準
"""1人3本の動画の学習(PBI #56、PBI-A サーバー)のテスト補助。

状態は、すべて HTTP の操作(ログイン、選択の確定、視聴ログ、終了ボタンの保存)で作る。
内部の IF(ポートやユースケースの名前)には依存しない。

【test-writer が置いた前提(共有IFが未確定のため、URL に依存しない形にしたもの)】
  - 全体の終了の画面の URL は、仕様の共有IF(実装の最初に固定)で未定。テストは具体的な URL を
    書かず、「全体の終了の協力者の `/` の 302 の移動先」を全体の終了の画面とみなし、
    それが既知の画面(`/`、`/lecture`、`/reflect`、選択の画面、`/login`)のどれでもないこと、
    他の画面・ログインの移動先が同じ URL であること、その URL が 200 であることを確かめる。
  - 選択待ち・全体の終了の API の 409 の本文は未定のため、状態コードだけを確かめる。
  - 「n本目 / 3本」の表示、選び直しの導線、全体の終了の画面の文言は PBI-B(画面)の範囲で、ここでは見ない。
  - 回の順は学習セッションの開始時刻(秒の分解能)で決まるため、2本目以降の確定の前に、時計の秒が
    変わるまで待つ(next_second)。同じ秒の確定で順が ID(UUID)の順に入れ替わらないようにする。
"""
from __future__ import annotations

import html as html_lib
import importlib
import re
import sqlite3
import time
from pathlib import Path

from interfaces.tutoring.srt import parse_srt_file
from tests.login_helpers import TEST_PASSWORD, location_path
from tests.selection_helpers import (
    CONFIRM_PATH,
    SELECT_PATH,
    VIDEO_IDS,
    all_lecture_ids,
    choose,
    lecture_page_shows,
    login_unselected,
    quiz_payload_for,
    viewing_body,
)

ROOT = Path(__file__).resolve().parent.parent

# 仕様の講義 X、Y、Z、W(カタログの互いに異なる講義。lecture-1 以外を含む)
X, Y, Z, W = "lecture-2", "lecture-5", "lecture-3", "lecture-6"

KNOWN_SCREEN_PATHS = {"/", "/lecture", "/reflect", SELECT_PATH, CONFIRM_PATH, "/login"}

BODY_APIS = ["viewing-log", "quiz-attempts", "chat", "dialog-log"]
GET_APIS = ["lad", "last-updated"]
SIX_APIS = BODY_APIS + GET_APIS  # #34 の AC14 の6つの API


def next_second() -> None:
    """時計の秒が変わるまで待つ(学習セッション・対話セッションの時刻を、前の操作と別の秒にする)。"""
    start = int(time.time())
    while int(time.time()) == start:
        time.sleep(0.02)


# ---------------------------------------------------------------- 操作


def confirm_round(client, lecture_id: str) -> None:
    """確定の前の確認の操作を経て、確定を送る。302 → /lecture であることを確かめる。"""
    first = client.post(SELECT_PATH, data={"lecture_id": lecture_id})
    assert first.status_code == 200, (
        f"準備: {lecture_id} の確定の前の確認が 200 にならない: {first.status_code}"
    )
    response = choose(client, lecture_id)
    assert response.status_code == 302 and location_path(response) == "/lecture", (
        f"準備: {lecture_id} の確定が /lecture への 302 にならない: "
        f"{response.status_code} {response.headers.get('Location')}"
    )


def save_dialog_log(client, end_method: str, lecture_field=..., participant_id=...):
    body = {"end_method": end_method}
    if lecture_field is not ...:
        body["lecture_id"] = lecture_field
    if participant_id is not ...:
        body["participant_id"] = participant_id
    return client.post("/api/dialog-log", json=body)


def finish_round(client, lecture_field=...) -> None:
    """終了ボタンで保存する(200 を受ける)= 回の終了。"""
    response = save_dialog_log(client, "end_button", lecture_field)
    assert response.status_code == 200, (
        f"準備: 終了ボタンの保存が 200 にならない: {response.status_code} "
        f"{response.get_data(as_text=True)[:200]}"
    )


def send_chat(client, message: str, lecture_field=...):
    body = {"message": message}
    if lecture_field is not ...:
        body["lecture_id"] = lecture_field
    return client.post("/chat", json=body)


def record_viewing(client, action: str = "play", lecture_field=..., current_time: int = 15):
    return client.post(
        "/api/viewing-log", json=viewing_body(lecture_field, current_time=current_time, action=action)
    )


def record_quiz(client, lecture_id: str, lecture_field=...):
    return client.post("/api/quiz-attempts", json=quiz_payload_for(lecture_id, lecture_field))


def build_progress(
    client,
    participant_id: str,
    finished: list[str],
    current: str | None = None,
    *,
    record_current: bool = False,
    login: bool = True,
) -> None:
    """HTTP の操作で、finished の講義の回を順に終え、current があればそれを今の回として選ぶ。

    finished の各回は、確定 → 視聴ログ(play)1件 → 終了ボタンの保存。
    record_current なら、今の回に視聴ログ(play)を1件記録する。
    """
    if login:
        login_unselected(client, participant_id)
    for index, lecture_id in enumerate(finished):
        if index > 0:
            next_second()
        confirm_round(client, lecture_id)
        assert record_viewing(client, "play").status_code == 201, f"準備: {lecture_id} の視聴ログ"
        finish_round(client)
    if current is not None:
        if finished:
            next_second()
        confirm_round(client, current)
        if record_current:
            assert record_viewing(client, "play").status_code == 201, f"準備: {current} の視聴ログ"


def login_follow(client, participant_id: str, next_path=None):
    """ログインを送り、移動先までたどった応答(request.path が最終の移動先)。"""
    data = {"participant_id": participant_id, "password": TEST_PASSWORD}
    if next_path is not None:
        data["next"] = next_path
    return client.post("/login", data=data, follow_redirects=True)


def call_api(client, api: str, participant_id: str, quiz_lecture: str, value=...):
    """6つの API のいずれかを呼ぶ。value=... なら lecture_id を含めない。"""
    from urllib.parse import quote

    if api == "viewing-log":
        body = viewing_body(value)
        body["participant_id"] = participant_id
        return client.post("/api/viewing-log", json=body)
    if api == "quiz-attempts":
        body = quiz_payload_for(quiz_lecture, value)
        body["participant_id"] = participant_id
        return client.post("/api/quiz-attempts", json=body)
    if api == "chat":
        body = {"message": "質問", "participant_id": participant_id}
        if value is not ...:
            body["lecture_id"] = value
        return client.post("/chat", json=body)
    if api == "dialog-log":
        body = {"end_method": "end_button", "participant_id": participant_id}
        if value is not ...:
            body["lecture_id"] = value
        return client.post("/api/dialog-log", json=body)
    query = "" if value is ... else f"lecture_id={quote(str(value))}"
    if api == "lad":
        return client.get(f"/api/participants/{participant_id}/lad" + (f"?{query}" if query else ""))
    separator = "&" if query else ""
    return client.get(f"/api/last-updated?participant_id={participant_id}{separator}{query}")


# ---------------------------------------------------------------- 観察


def end_screen_path(client) -> str:
    """全体の終了の協力者の `/` の移動先(全体の終了の画面の URL)。既知の画面でないことも確かめる。"""
    response = client.get("/")
    assert response.status_code == 302, f"全体の終了の `/` が 302 でない: {response.status_code}"
    path = location_path(response)
    assert path not in KNOWN_SCREEN_PATHS, (
        f"全体の終了の `/` の移動先が、全体の終了の画面ではなく既知の画面 {path!r} になっている"
    )
    return path


def shown_lecture(html: str) -> str | None:
    """講義の画面に表示されている講義の ID(画面の講義ID・動画で判定。1つに決まらなければ None)。"""
    shown = [lid for lid in VIDEO_IDS if lecture_page_shows(html, lid)]
    return shown[0] if len(shown) == 1 else None


# PBI-D(選び直し)の観察。仕様: docs/spec/multi-video-learning.md#8-回の選び直しfr-63-の改訂q4
# 【test-writer が置いた前提】選び直しの導線は「選択の画面へのリンク」(8節)なので、
# href が選択の画面(クエリ・断片は問わない)の <a> 要素があるかで判定する。
_RESELECT_LINK = re.compile(
    r"<a\b[^>]*\bhref\s*=\s*[\"']" + re.escape(SELECT_PATH) + r"(?:[?#][^\"']*)?[\"']",
    re.I,
)
_ROUND_LABEL = re.compile(r"(\d)\s*本目\s*/\s*3\s*本")


def has_reselect_link(html: str) -> bool:
    """講義の画面に、選び直しの導線(選択の画面へのリンク)があるか。"""
    return _RESELECT_LINK.search(html) is not None


def page_text(html: str) -> str:
    """タグを除き、文字参照を戻した本文(空白は1つにまとめる。script・style は除く)。"""
    without = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html, flags=re.S | re.I)
    without = re.sub(r"<[^>]+>", " ", without)
    return re.sub(r"\s+", " ", html_lib.unescape(without))


def round_labels(html: str) -> set[int]:
    """画面に出ている「n本目 / 3本」の n の集合。"""
    return {int(m.group(1)) for m in _ROUND_LABEL.finditer(page_text(html))}


def text_blocks(html: str) -> list[str]:
    """ブロック要素(p、div、li、section、見出しなど)ごとの本文。1つの文言のまとまりの判定用。"""
    body = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html, flags=re.S | re.I)
    parts = re.split(
        r"</?(?:p|div|li|ul|ol|section|article|aside|h[1-6]|form|body|br|table|tr|td)\b[^>]*>",
        body,
        flags=re.I,
    )
    return [t for t in (page_text(p).strip() for p in parts) if t]


def option_lectures_expected(excluded: list[str]) -> list[str]:
    return [lid for lid in all_lecture_ids() if lid not in excluded]


def sessions_of(tmp_path: Path, learner: str) -> list[tuple[str, str]]:
    """その学習者の (学習セッションID, 講義) を、開始時刻 → ID の順に。"""
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return [
            (r[0], r[1])
            for r in conn.execute(
                "SELECT id, lecture_id FROM learning_sessions WHERE learner_id=? "
                "ORDER BY started_at, id",
                (learner,),
            )
        ]
    finally:
        conn.close()


def lectures_of(tmp_path: Path, learner: str) -> list[str]:
    return sorted(lecture for _id, lecture in sessions_of(tmp_path, learner))


def session_id_of(tmp_path: Path, learner: str, lecture_id: str) -> str:
    matches = [sid for sid, lec in sessions_of(tmp_path, learner) if lec == lecture_id]
    assert len(matches) == 1, f"{learner} の {lecture_id} の学習セッションが {len(matches)} 個"
    return matches[0]


def count_records(tmp_path: Path, table: str, learning_session_id: str) -> int:
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE learning_session_id=?", (learning_session_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def tutor_rows(tmp_path: Path, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = sqlite3.connect(str(tmp_path / "tutor.db"))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def quiz_question_texts(lecture_id: str) -> set[str]:
    from framework_drivers.db.learning.static_lecture_catalog import build_near_term_lecture

    quiz = build_near_term_lecture(lecture_id=lecture_id).quiz_definition
    return {q.text for q in quiz.questions}


def cue_text_at(lecture_id: str, position: float) -> str:
    """その講義の字幕の、その位置の文(講義の文脈がプロンプトに入ったかの判定用)。"""
    path = ROOT / "lectures" / lecture_id / "subtitles.srt"
    assert path.is_file(), f"{path} が無い"
    segments = parse_srt_file(path)
    for seg in segments:
        if seg["start_sec"] <= position <= seg["end_sec"]:
            return seg["text"].strip()
    for seg in segments:
        if seg["start_sec"] >= position:
            return seg["text"].strip()
    raise AssertionError("位置に対応するキューが無い")


def outline_titles(lecture_id: str) -> list[str]:
    number = lecture_id.split("-")[1]
    module = importlib.import_module(
        f"framework_drivers.db.learning.lecture_outlines.lecture_{number}"
    )
    return [section.title for section in module.build_lecture_outline().sections]


def schema_of(db_path: Path) -> list[tuple]:
    """sqlite_master の内容(type, name, tbl_name, sql)。内部の索引(sqlite_autoindex)を含む。"""
    conn = sqlite3.connect(str(db_path))
    try:
        return sorted(
            tuple(r)
            for r in conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master")
        )
    finally:
        conn.close()
