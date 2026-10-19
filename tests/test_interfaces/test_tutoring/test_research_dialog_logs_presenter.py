# 仕様: docs/spec/research-dialog-download.md#json-の形 (R4 R5 R7)
"""ResearchDialogLogsPresenter と、ViewModel のリスト化(キーの順)。"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from application.tutoring.dto.export_dialog_logs import (
    ExportDialogLogsResponse,
    ResearchDialogLog,
)
from application.tutoring.dto.save_dialog_log import EndMethod
from domain.shared.ids import MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from interfaces.tutoring.dialog_log_json_format import message_to_json_dict
from interfaces.tutoring.presenters.research_dialog_logs_presenter import (
    ResearchDialogLogsPresenter,
)
from interfaces.tutoring.view_models.research_dialog_logs import (
    ResearchDialogLogsViewModel,
)
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    sample_updated_state_card,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
T7 = datetime(2026, 9, 29, 1, 0, 7, tzinfo=timezone.utc)
ENDED = datetime(2026, 9, 29, 1, 5, 0, 987654, tzinfo=timezone.utc)

TOP_LEVEL_KEYS_IN_ORDER = [
    "format_version",
    "participant_id",
    "lecture_id",
    "learning_session_id",
    "tutor_session_id",
    "ended_at",
    "end_method",
    "messages",
]


def _messages() -> tuple[Message, ...]:
    return (
        Message.create(id=MessageId("1"), role=MessageRole.USER, content="質問", created_at=T0),
        Message.create(
            id=MessageId("2"),
            role=MessageRole.ASSISTANT,
            content="応答",
            created_at=T0,
            utterance_type=LearnerUtteranceType.FACT_REQUEST,
            dialogue_move=DialogueMove.ELICIT_REASON,
            interpretation_state=sample_updated_state_card(),
            responded_at=T7,
        ),
    )


def _log(**overrides) -> ResearchDialogLog:
    base = dict(
        participant_id="1",
        lecture_id="lecture-1",
        learning_session_id="ls-1",
        tutor_session_id="ts-1",
        tutor_session_created_at=T0,
        ended_at=ENDED,
        end_method=EndMethod.END_BUTTON,
        messages=_messages(),
    )
    base.update(overrides)
    return ResearchDialogLog(**base)


def _present(*logs: ResearchDialogLog) -> ResearchDialogLogsViewModel:
    return ResearchDialogLogsPresenter().present(ExportDialogLogsResponse(logs=tuple(logs)))


class TestPresenter:
    def test_r4_all_shared_if_values_are_set(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R4
        (vm,) = _present(_log()).logs

        assert vm.format_version == 1
        assert vm.participant_id == "1"
        assert vm.lecture_id == "lecture-1"
        assert vm.learning_session_id == "ls-1"
        assert vm.tutor_session_id == "ts-1"
        assert vm.messages == tuple(message_to_json_dict(m) for m in _messages())

    def test_r5_ended_at_is_formatted_to_the_second_and_end_method_is_a_string(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R5(dialog-log-save.md の時刻の形式)
        (vm,) = _present(_log()).logs

        assert vm.ended_at == "2026-09-29T01:05:00+00:00"
        assert vm.end_method == "end_button"

    def test_r5_page_leave_value(self) -> None:
        (vm,) = _present(_log(end_method=EndMethod.PAGE_LEAVE)).logs

        assert vm.end_method == "page_leave"

    def test_r5_without_saved_log_ended_at_and_end_method_are_none(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R5(保存していない側はどちらも null)
        (vm,) = _present(_log(ended_at=None, end_method=None)).logs

        assert vm.ended_at is None
        assert vm.end_method is None

    def test_r5_zero_messages_stays_empty(self) -> None:
        (vm,) = _present(_log(messages=())).logs

        assert list(vm.messages) == []

    def test_r6_order_of_the_use_case_result_is_kept(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(Presenter は並べ替えない)
        logs = (_log(participant_id="2", tutor_session_id="b"), _log(participant_id="1", tutor_session_id="a"))

        vm = _present(*logs)

        assert [(v.participant_id, v.tutor_session_id) for v in vm.logs] == [("2", "b"), ("1", "a")]

    def test_r7_no_logs_gives_empty_view_model(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R7
        assert _present().logs == ()


class TestJsonList:
    """interfaces/common/json_encoding.py に追加される関数(既存ファイルのため、実装前は未定義)。"""

    def test_r4_keys_follow_the_spec_example_order(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#json-の形(キーは仕様の例の順)
        from interfaces.common.json_encoding import (
            research_dialog_logs_view_model_to_json_list,
        )

        result = research_dialog_logs_view_model_to_json_list(_present(_log()))

        assert len(result) == 1
        assert list(result[0]) == TOP_LEVEL_KEYS_IN_ORDER
        assert result[0]["format_version"] == 1
        assert result[0]["participant_id"] == "1"
        assert [m["role"] for m in result[0]["messages"]] == ["user", "assistant"]
        assert list(result[0]["messages"][1]) == [
            "role",
            "content",
            "timestamp",
            "utterance_type",
            "dialogue_move",
            "interpretation_state",
        ]
        assert json.loads(json.dumps(result, ensure_ascii=False)) == result

    def test_r5_null_and_empty_messages_are_kept(self) -> None:
        from interfaces.common.json_encoding import (
            research_dialog_logs_view_model_to_json_list,
        )

        result = research_dialog_logs_view_model_to_json_list(
            _present(_log(ended_at=None, end_method=None, messages=()))
        )

        assert result[0]["ended_at"] is None
        assert result[0]["end_method"] is None
        assert result[0]["messages"] == []

    def test_r7_zero_logs_is_empty_list(self) -> None:
        from interfaces.common.json_encoding import (
            research_dialog_logs_view_model_to_json_list,
        )

        assert research_dialog_logs_view_model_to_json_list(_present()) == []
