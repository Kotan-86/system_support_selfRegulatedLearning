# 仕様: docs/spec/research-dialog-download.md#受入基準 (R4 R6 R7)
"""ExportDialogLogsController: 参加者IDを変換せずユースケースへ渡す(Q6)。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.tutoring.dto.export_dialog_logs import ResearchDialogLog
from application.tutoring.use_cases.export_dialog_logs import ExportDialogLogsUseCase
from interfaces.tutoring.controllers.export_dialog_logs_controller import (
    ExportDialogLogsController,
)
from interfaces.tutoring.presenters.research_dialog_logs_presenter import (
    ResearchDialogLogsPresenter,
)
from interfaces.tutoring.view_models.research_dialog_logs import (
    ResearchDialogLogsViewModel,
)
from tests.test_application.fakes.tutoring.fake_dialog_log_export_query import (
    FakeDialogLogExportQuery,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)


def _log(pid: str, tsid: str) -> ResearchDialogLog:
    return ResearchDialogLog(
        participant_id=pid,
        lecture_id="lecture-1",
        learning_session_id=f"ls-{pid}",
        tutor_session_id=tsid,
        tutor_session_created_at=T0,
        ended_at=None,
        end_method=None,
        messages=(),
    )


def _controller(*logs: ResearchDialogLog):
    query = FakeDialogLogExportQuery(tuple(logs))
    controller = ExportDialogLogsController(
        ExportDialogLogsUseCase(query), ResearchDialogLogsPresenter()
    )
    return controller, query


def test_r4_participant_request_returns_only_that_participant() -> None:
    controller, _ = _controller(_log("1", "a"), _log("2", "b"))

    result = controller.execute_for_participant("1")

    assert isinstance(result, ResearchDialogLogsViewModel)
    assert [(v.participant_id, v.tutor_session_id) for v in result.logs] == [("1", "a")]


def test_r7_participant_id_is_not_trimmed_or_normalized() -> None:
    # 仕様: docs/spec/research-dialog-download.md#受入基準 R7 (Q6: 変換せずそのまま照合)
    controller, query = _controller(_log("1", "a"))

    for raw in (" 1", " ", "1 ", "１"):
        result = controller.execute_for_participant(raw)
        assert isinstance(result, ResearchDialogLogsViewModel)
        assert result.logs == ()

    assert query.list_for_participant_calls == [" 1", " ", "1 ", "１"]


def test_r7_participant_with_no_data_is_empty_view_model_not_error() -> None:
    controller, _ = _controller(_log("1", "a"))

    result = controller.execute_for_participant("nobody")

    assert isinstance(result, ResearchDialogLogsViewModel)
    assert result.logs == ()


def test_r6_all_returns_every_participant_in_the_specified_order() -> None:
    controller, query = _controller(_log("foo", "d"), _log("2", "b"), _log("10", "c"), _log("1", "a"))

    result = controller.execute_all()

    assert isinstance(result, ResearchDialogLogsViewModel)
    assert [v.participant_id for v in result.logs] == ["1", "10", "2", "foo"]
    assert query.list_all_calls == 1


def test_r7_all_with_no_data_is_empty_view_model() -> None:
    controller, _ = _controller()

    result = controller.execute_all()

    assert isinstance(result, ResearchDialogLogsViewModel)
    assert result.logs == ()
