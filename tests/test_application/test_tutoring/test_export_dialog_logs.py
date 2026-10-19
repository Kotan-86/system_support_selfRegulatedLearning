# 仕様: docs/spec/research-dialog-download.md#受入基準 (R5 R6 R7)
"""ExportDialogLogsUseCase: 取得の切り替えと並び順(Q3)を、フェイクのポートで検証する。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.tutoring.dto.export_dialog_logs import (
    ExportDialogLogsRequest,
    ResearchDialogLog,
)
from application.tutoring.use_cases.export_dialog_logs import ExportDialogLogsUseCase
from tests.test_application.fakes.tutoring.fake_dialog_log_export_query import (
    FakeDialogLogExportQuery,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)


def _log(pid: str, tsid: str, created: datetime = T0) -> ResearchDialogLog:
    return ResearchDialogLog(
        participant_id=pid,
        lecture_id="lecture-1",
        learning_session_id=f"ls-{pid}",
        tutor_session_id=tsid,
        tutor_session_created_at=created,
        ended_at=None,
        end_method=None,
        messages=(),
    )


def _keys(response) -> list[tuple[str, str]]:
    return [(log.participant_id, log.tutor_session_id) for log in response.logs]


def _run(query: FakeDialogLogExportQuery, participant_id: str | None):
    result = ExportDialogLogsUseCase(query).execute(
        ExportDialogLogsRequest(participant_id=participant_id)
    )
    assert result.is_ok, result
    return result.value


class TestSelection:
    def test_r4_participant_request_uses_list_for_participant(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R4(参加者別は、その参加者の対話セッションだけ)
        query = FakeDialogLogExportQuery((_log("1", "a"), _log("2", "b")))

        response = _run(query, "1")

        assert _keys(response) == [("1", "a")]
        assert query.list_for_participant_calls == ["1"]
        assert query.list_all_calls == 0

    def test_r6_all_request_uses_list_all(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(一括は全参加者)
        query = FakeDialogLogExportQuery((_log("1", "a"), _log("2", "b")))

        response = _run(query, None)

        assert sorted(_keys(response)) == [("1", "a"), ("2", "b")]
        assert query.list_all_calls == 1
        assert query.list_for_participant_calls == []

    def test_r7_participant_id_is_passed_unchanged(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R7 (Q6: 変換せずそのまま照合)
        query = FakeDialogLogExportQuery((_log("1", "a"),))

        for raw in (" 1", " ", "1 ", "", "ＡＢ"):
            response = _run(query, raw)
            assert response.logs == ()
        assert query.list_for_participant_calls == [" 1", " ", "1 ", "", "ＡＢ"]


class TestEmpty:
    def test_r7_participant_with_no_data_is_empty_tuple(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R7
        response = _run(FakeDialogLogExportQuery((_log("1", "a"),)), "nobody")

        assert response.logs == ()

    def test_r7_all_with_no_data_is_empty_tuple(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R7
        response = _run(FakeDialogLogExportQuery(()), None)

        assert response.logs == ()


class TestOrdering:
    def test_r6_participant_ids_sort_as_strings(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(1, 10, 2, foo の順。数値順ではない)
        query = FakeDialogLogExportQuery(
            (_log("foo", "d"), _log("2", "b"), _log("10", "c"), _log("1", "a"))
        )

        response = _run(query, None)

        assert [log.participant_id for log in response.logs] == ["1", "10", "2", "foo"]

    def test_r6_within_participant_sorted_by_created_at(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(作成時刻の昇順)
        query = FakeDialogLogExportQuery(
            (
                _log("1", "z-late", T0 + timedelta(seconds=30)),
                _log("1", "a-early", T0),
                _log("1", "m-mid", T0 + timedelta(seconds=10)),
            )
        )

        response = _run(query, None)

        assert [log.tutor_session_id for log in response.logs] == [
            "a-early",
            "m-mid",
            "z-late",
        ]

    def test_r6_same_second_sorted_by_tutor_session_id(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(同じ時刻なら対話セッションIDの昇順)
        query = FakeDialogLogExportQuery(
            (_log("1", "c"), _log("1", "a"), _log("1", "b"))
        )

        response = _run(query, None)

        assert [log.tutor_session_id for log in response.logs] == ["a", "b", "c"]

    def test_r6_participant_order_takes_precedence_over_time(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(参加者ID → 時刻 → ID)
        query = FakeDialogLogExportQuery(
            (
                _log("2", "x", T0),
                _log("1", "y", T0 + timedelta(hours=1)),
            )
        )

        response = _run(query, None)

        assert _keys(response) == [("1", "y"), ("2", "x")]

    def test_r6_participant_request_result_is_also_sorted(self) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(参加者別のリストも同じ規則)
        query = FakeDialogLogExportQuery(
            (_log("2", "late", T0 + timedelta(seconds=5)), _log("2", "early", T0))
        )

        response = _run(query, "2")

        assert [log.tutor_session_id for log in response.logs] == ["early", "late"]
