# 仕様: docs/spec/multi-video-learning.md#2-回の選択n本目
# 仕様: docs/spec/multi-video-learning.md#8-回の選び直しfr-63-の改訂q4
# 仕様: docs/spec/lecture-selection.md#3-選択の保存と固定fr-63
"""回の選択ユースケース — 選択は既存の LearningSession で表す(新しい表は足さない)。"""
from __future__ import annotations

from datetime import datetime

from application.common.errors import AppError, LectureNotFoundError, ValidationError
from application.common.result import Result, err, ok
from application.learning.dto.participant_progress import ParticipantProgress, ProgressState
from application.learning.ports.id_generators import LearningSessionIdGenerator
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.ports.lecture_catalog import LectureCatalog
from application.learning.use_cases.get_participant_progress import (
    GetParticipantProgressUseCase,
)
from domain.learning.learning_session import LearningSession
from domain.learning.lecture import Lecture
from domain.shared.ids import LearnerId, LectureId


class SelectLectureUseCase:
    """n本目の選択待ちの協力者が、終えた回の講義以外から1本を選ぶ。

    選び直せる学習中(記録のない今の回)は、今の回を別の講義に置き換える(8節)。他の状態では何も変えない。
    """

    def __init__(
        self,
        repository: LearningSessionRepository,
        id_generator: LearningSessionIdGenerator,
        lecture_catalog: LectureCatalog,
        progress: GetParticipantProgressUseCase,
    ) -> None:
        self._repository = repository
        self._id_generator = id_generator
        self._lecture_catalog = lecture_catalog
        self._progress = progress

    def options(self, progress: ParticipantProgress) -> tuple[Lecture, ...]:
        """選択肢: カタログの講義から、終えた回の講義と今の回の講義を除いたもの(カタログの順)。"""
        excluded = {*progress.finished_lecture_ids, progress.current_lecture_id}
        return tuple(x for x in self._lecture_catalog.list_all() if x.id not in excluded)

    def execute(
        self, learner_id: LearnerId, lecture_id: LectureId, selected_at: datetime
    ) -> Result[ParticipantProgress, AppError]:
        """選択待ちなら lecture_id の学習セッションを作り、選び直せるなら今の回を置き換える。

        確定の後の進行状態を返す。カタログにない講義・終えた回の講義は Err(400)。
        それ以外の状態と、今の回の講義の確定は、何も変えない。
        """
        if self._lecture_catalog.find_by_id(lecture_id) is None:
            return err(LectureNotFoundError(f"lecture not found: {lecture_id!s}"))
        progress = self._progress.execute(learner_id)
        if lecture_id in progress.finished_lecture_ids:
            return err(ValidationError(f"lecture already finished: {lecture_id!s}"))
        reselect = progress.can_reselect and lecture_id != progress.current_lecture_id
        if progress.state is not ProgressState.WAITING and not reselect:
            return ok(progress)
        session = LearningSession.start(
            id=self._id_generator.next_id(),
            learner_id=learner_id,
            lecture_id=lecture_id,
            started_at=selected_at,
        )
        if reselect:
            # 記録がないことを確かめてから置き換える(記録と同時なら一方だけが成立。8節)。
            # 同時の選び直しでは、後の側は今の回が既にないため何も変えない(学習セッションは n のまま)。
            self._repository.replace_if_no_records(
                progress.current_learning_session_id, session  # type: ignore[arg-type]
            )
        else:
            # 選択待ちの学習セッションはすべて終えた回。数の確認と保存を排他的に行い、
            # 同時の確定・二重送信でも1つだけ増やす(後の側は何も保存しない)。
            self._repository.save_if_learner_session_count(
                session, len(progress.finished_lecture_ids)
            )
        return ok(self._progress.execute(learner_id))
