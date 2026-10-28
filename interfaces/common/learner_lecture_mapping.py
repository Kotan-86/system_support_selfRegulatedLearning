# 仕様: docs/spec/lecture-selection.md#4-講義-id-の一貫fr-62
# 仕様: docs/spec/interfaces-layer.md#default_lecture
"""参加者の要求の講義 ID を LectureId にする。

participant_id による固定対応(1/2/3 → lecture-1/2/3、それ以外は既定の講義)は、
講義の選択(FR-60、#34)で廃止した。参加者の講義は保存された選択で決まり、
platform 層が選択した講義の ID を必ず渡す。
"""
from __future__ import annotations

from application.common.errors import ValidationError
from application.common.result import Result, err, ok
from domain.shared.ids import LectureId
from interfaces.common.default_lecture import resolve_default_lecture_id


def resolve_lecture_id_for_participant(
    participant_id: str,
    lecture_id: str | None = None,
) -> Result[LectureId, ValidationError]:
    """明示された lecture_id を検証して LectureId にする(participant_id では決めない)。

    lecture_id が None のときだけ既定の講義(resolve_default_lecture_id)を返す。これは
    Controller を直接呼ぶ単体テスト・内部用の最終手段で、HTTP の経路では使われない
    (platform 層が、保存された選択の講義を必ず渡す)。
    """
    if lecture_id is None:
        return ok(resolve_default_lecture_id())
    normalized = lecture_id.strip()
    if not normalized:
        return err(ValidationError("lecture_id must not be empty"))
    try:
        return ok(LectureId(normalized))
    except ValueError as exc:
        return err(ValidationError(str(exc)))
