# 仕様: docs/spec/multi-video-learning.md#受入基準 (PBI #56 PBI-B 画面) AC1・AC5・AC8・AC15(何本目の表示)
"""1人3本の動画の学習の、画面の「n本目 / 3本」の表示(What 2節、Q12)を、
Flask のテストクライアント(一時ディレクトリの DB、偽の LLM)で確かめる。

状態は HTTP の操作だけで作る(tests/multi_video_helpers.py)。

PBI-B の範囲(tests.md の境界の判断による):
  - 選択の画面の「n本目 / 3本」(AC1・AC5・AC8 の画面の部分。サーバーの部分は PBI-A のテスト)
  - 確定の前の確認の画面の、題名と「n本目 / 3本」と、保存しないこと(AC15 のうち選び直しに依存しない部分)
PBI-D の範囲(ここでは見ない): AC15 の「この回の動画が変えられなくなる条件」の文言(「再生」「小テスト」
「対話」)と、#34 の「一度選ぶと変更できない」が含まれないこと(選び直し(8節)を前提とする文言のため)。

表示の判定: HTML のタグを除き、文字参照を戻した本文で、「<数字>本目 / 3本」(空白の有無は問わない)を探す。
画面に出る「n本目 / 3本」の n の集合が、ちょうど {n} であることを確かめる(他の回の表示が混ざらない)。
"""
from __future__ import annotations

import html as html_lib
import re

import pytest

from tests.login_helpers import build_app
from tests.multi_video_helpers import X, Y, Z, build_progress, sessions_of
from tests.selection_helpers import SELECT_PATH, catalog_lectures, login_unselected, option_values

PID = "P02"

_ROUND_LABEL = re.compile(r"(\d)\s*本目\s*/\s*3\s*本")


@pytest.fixture
def env(monkeypatch, tmp_path):
    app, llm = build_app(monkeypatch, tmp_path)
    return app, llm, tmp_path


def _text(html: str) -> str:
    """タグを除き、文字参照を戻した本文(空白は1つにまとめる)。"""
    without_tags = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html, flags=re.S)
    without_tags = re.sub(r"<[^>]+>", " ", without_tags)
    return re.sub(r"\s+", " ", html_lib.unescape(without_tags))


def _round_labels(html: str) -> set[int]:
    return {int(m.group(1)) for m in _ROUND_LABEL.finditer(_text(html))}


def _title_of(lecture_id: str) -> str:
    return next(str(lec.title) for lec in catalog_lectures() if str(lec.id) == lecture_id)


# 回ごとの準備: (n, 終えた回の講義, 確認の画面で選ぶ講義)
ROUNDS = [
    pytest.param(1, [], X, id="round1"),
    pytest.param(2, [X], Y, id="round2"),
    pytest.param(3, [X, Y], Z, id="round3"),
]


# ---------------------------------------------------------------- AC1・AC5・AC8 選択の画面の「n本目 / 3本」


class TestRoundLabelOnSelectionScreen:
    @pytest.mark.parametrize("n, finished, _chosen", ROUNDS)
    def test_ac1_ac5_ac8_selection_screen_shows_n_of_3(self, env, n, finished, _chosen) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC1(1本目 / 3本)、AC5(2本目 / 3本)、AC8(3本目 / 3本)
        # 仕様: docs/spec/multi-video-learning.md#2-回の選択n本目(Q12)
        app, _llm, _tmp_path = env
        client = app.test_client()
        if finished:
            build_progress(client, PID, finished)
        else:
            login_unselected(client, PID)

        screen = client.get(SELECT_PATH)

        assert screen.status_code == 200
        html = screen.get_data(as_text=True)
        # 準備の確認: n本目の選択待ちの選択の画面である(選択肢から終えた回の講義が除かれている)
        assert not set(finished) & set(option_values(html)), option_values(html)
        assert _round_labels(html) == {n}, (
            f"{n}本目の選択の画面に「{n}本目 / 3本」(だけ)が表示されていない: "
            f"見つかった n = {sorted(_round_labels(html))}\n本文: {_text(html)[:400]}"
        )


# ---------------------------------------------------------------- AC15(選び直しに依存しない部分) 確定の前の確認


class TestRoundLabelOnConfirmScreen:
    @pytest.mark.parametrize("n, finished, chosen", ROUNDS)
    def test_ac15_confirm_screen_shows_title_and_n_of_3_and_saves_nothing(
        self, env, n, finished, chosen
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC15(題名、「n本目 / 3本」、この時点では保存されない。
        #       n = 1, 2。n = 3 は What 2節「選択の画面と確定の前の確認の画面に、何本目を選ぶのか」による)
        # AC15 の「変えられなくなる条件」の文言と #34 の文言が無いことは PBI-D(tests.md の境界)
        app, _llm, tmp_path = env
        client = app.test_client()
        if finished:
            build_progress(client, PID, finished)
        else:
            login_unselected(client, PID)
        before = sessions_of(tmp_path, PID)

        confirm = client.post(SELECT_PATH, data={"lecture_id": chosen})

        assert confirm.status_code == 200
        html = confirm.get_data(as_text=True)
        assert _title_of(chosen) in _text(html), f"確認の画面に {chosen} の題名が無い"
        assert _round_labels(html) == {n}, (
            f"{n}本目の確定の前の確認に「{n}本目 / 3本」(だけ)が表示されていない: "
            f"見つかった n = {sorted(_round_labels(html))}\n本文: {_text(html)[:400]}"
        )
        assert sessions_of(tmp_path, PID) == before, "確定の前の確認で学習セッションが変わった"
