"""
PBI-A-2 (11-T6): GET /reflect の「対話ログを送信して終了する」ボタンのマークアップ。

仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-2) A1, A9(完了表示), A10(失敗表示の文言)
位置・見た目・実ブラウザの操作は PO確認(ここでは検証しない)。
"""
from html.parser import HTMLParser

import pytest

BUTTON_LABEL = "対話ログを送信して終了する"
# 研究者への連絡を促す文言は出さない(N5)。
FORBIDDEN_IN_ERROR = ("研究者", "連絡", "問い合わせ", "問合せ", "報告してください")


class _Page(HTMLParser):
    """要素を出現順に記録し、id ごとの属性・テキスト・親をたどれるようにする。"""

    _VOID = {"meta", "link", "br", "img", "input", "hr"}

    def __init__(self) -> None:
        super().__init__()
        self.events: list[tuple[str, str, dict]] = []  # (start|end, tag, attrs)
        self.by_id: dict[str, dict] = {}
        self.buttons: list[dict] = []
        self.scripts: list[str] = []
        self._stack: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        node = {
            "tag": tag,
            "attrs": a,
            "text": "",
            "index": len(self.events),
            "ancestors": [n["attrs"].get("id") for n in self._stack] + [n["tag"] for n in self._stack],
        }
        self.events.append(("start", tag, a))
        if "id" in a:
            self.by_id[a["id"]] = node
        if tag == "button":
            self.buttons.append(node)
        if tag == "script" and "src" in a:
            self.scripts.append(a["src"])
        if tag not in self._VOID:
            self._stack.append(node)

    def handle_endtag(self, tag):
        self.events.append(("end", tag, {}))
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i]["tag"] == tag:
                node = self._stack[i]
                node["end_index"] = len(self.events) - 1
                del self._stack[i:]
                break

    def handle_data(self, data):
        for n in self._stack:
            n["text"] += data


@pytest.fixture
def page(phase2_client) -> _Page:
    r = phase2_client.get("/reflect?participant_id=1")
    assert r.status_code == 200
    p = _Page()
    p.feed(r.get_data(as_text=True))
    return p


class TestEndButtonMarkup:
    def test_a1_exactly_one_end_button_with_label(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A1
        ends = [b for b in page.buttons if b["attrs"].get("id") == "end-dialog-button"]
        assert len(ends) == 1, f"id=end-dialog-button のボタンがちょうど1つ(実際: {len(ends)})"
        assert ends[0]["text"].strip() == BUTTON_LABEL
        labelled = [b for b in page.buttons if BUTTON_LABEL in b["text"]]
        assert len(labelled) == 1, "ラベルのボタンが画面に1つだけ"

    def test_a1_end_button_is_not_a_submit_button(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A1(送信ボタンと見分けがつく。押しても送信フォームを submit しない)
        b = page.by_id["end-dialog-button"]
        assert b["attrs"].get("type") == "button"
        assert "end-dialog-button" in (b["attrs"].get("class") or "").split()

    def test_a1_end_button_is_below_message_form_and_outside_it(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A1(入力欄と送信ボタンより下。位置の見た目は PO確認)
        form = page.by_id["message-form"]
        btn = page.by_id["end-dialog-button"]
        assert btn["index"] > form["end_index"], "終了ボタンは #message-form の終了タグより後にある"
        assert "form" not in btn["ancestors"], "終了ボタンは form の中にない"

    def test_a1_end_button_is_inside_chat_panel(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A1(AI チューターの欄の中)。11-T6 の契約: section.chat-panel に id="chat-panel"
        panel = page.by_id.get("chat-panel")
        assert panel is not None, 'id="chat-panel" の要素がある'
        assert panel["tag"] == "section"
        assert "chat-panel" in (panel["attrs"].get("class") or "").split()
        assert "chat-panel" in page.by_id["end-dialog-button"]["ancestors"]
        assert "chat-panel" in page.by_id["message-form"]["ancestors"]

    def test_a10_error_element_is_hidden_alert_with_text_and_no_contact_words(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A10, N5(研究者への連絡を促す文言を含めない)
        err = page.by_id.get("dialog-end-error")
        assert err is not None, "#dialog-end-error が存在する"
        assert "hidden" in err["attrs"], "初期状態で hidden"
        assert err["attrs"].get("role") == "alert"
        text = err["text"].strip()
        assert text, "失敗の文言が空でない"
        for word in FORBIDDEN_IN_ERROR:
            assert word not in text, f"失敗の文言に {word!r} を含めない(N5): {text!r}"

    def test_a9_complete_element_is_hidden_status_with_text(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A9(完了画面に、対話ログを送信したことが表示される)
        done = page.by_id.get("dialog-end-complete")
        assert done is not None, "#dialog-end-complete が存在する"
        assert "hidden" in done["attrs"], "初期状態で hidden"
        assert done["attrs"].get("role") == "status"
        assert done["text"].strip(), "完了の文言が空でない"

    def test_a9_a10_error_and_complete_elements_are_in_chat_panel(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A9, A10(AI チューターの欄の中で表示される)
        for i in ("dialog-end-error", "dialog-end-complete"):
            assert "chat-panel" in page.by_id[i]["ancestors"], f"#{i} は #chat-panel の中"

    def test_a9_dialog_log_js_is_loaded_between_chat_panel_and_reflect_app(self, page: _Page) -> None:
        # 仕様: docs/spec/dialog-log-save.md#受入基準 A9(画面の JS の読み込み。11-T6 の契約)
        def idx(name: str) -> int:
            hits = [i for i, s in enumerate(page.scripts) if name in s]
            assert len(hits) == 1, f"{name} の script がちょうど1つ(実際: {len(hits)}): {page.scripts}"
            return hits[0]

        assert idx("js/reflect/chat_panel.js") < idx("js/reflect/dialog_log.js") < idx("js/reflect/reflect_app.js")
        assert idx("js/common/api_client.js") < idx("js/reflect/dialog_log.js")
