# 仕様: docs/spec/interfaces-layer.md#default_lecture
"""participant_id から lecture_id を解決する。"""
from __future__ import annotations

from application.common.errors import ValidationError
from application.common.result import Result, err, ok
from domain.shared.ids import LectureId

from interfaces.common.default_lecture import resolve_default_lecture_id

NEAR_TERM_PARTICIPANT_LECTURE_MAP: dict[str, str] = {
    "1": "lecture-1",
    "2": "lecture-2",
    "3": "lecture-3",
}
"""近い実験: participant_id → lecture_id の固定マップ。"""


def _parse_explicit_lecture_id(lecture_id: str) -> Result[LectureId, ValidationError]:
    """明示 lecture_id を LectureId へ変換する（default は使用しない）。"""
    normalized = lecture_id.strip()
    if not normalized:
        return err(ValidationError("lecture_id must not be empty"))
    try:
        return ok(LectureId(normalized))
    except ValueError as exc:
        return err(ValidationError(str(exc)))


def resolve_lecture_id_for_participant(
    participant_id: str,
    lecture_id: str | None = None,
) -> Result[LectureId, ValidationError]:
    """participant_id と optional lecture_id から LectureId を解決する。

    優先順位:
    1. lecture_id 明示 → 検証のみ（マップ・default 不使用）
    2. participant_id が近い実験マップに命中 → 対応 LectureId
    3. それ以外 → resolve_default_lecture_id()（lecture-1）
    """
    if lecture_id is not None:
        return _parse_explicit_lecture_id(lecture_id)

    normalized_participant = participant_id.strip()
    mapped = NEAR_TERM_PARTICIPANT_LECTURE_MAP.get(normalized_participant)
    if mapped is not None:
        return ok(LectureId(mapped))

    return ok(resolve_default_lecture_id())
