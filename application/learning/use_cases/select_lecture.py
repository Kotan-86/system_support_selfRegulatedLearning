# 仕様: docs/spec/lecture-selection.md#3-選択の保存と固定fr-63
"""講義の選択ユースケース — 選択は既存の LearningSession で表す(新しい表は足さない)。"""
from __future__ import annotations

from datetime import datetime

from application.common.errors import AppError, LectureNotFoundError
from application.common.result import Result, err, ok
from application.learning.ports.id_generators import LearningSessionIdGenerator
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.ports.lecture_catalog import LectureCatalog
from domain.learning.learning_session import LearningSession
from domain.shared.ids import LearnerId, LectureId


class SelectLectureUseCase:
    """協力者が学習する講義を1回選ぶ。保存された選択は変えない。"""

    def __init__(
        self,
        repository: LearningSessionRepository,
        id_generator: LearningSessionIdGenerator,
        lecture_catalog: LectureCatalog,
    ) -> None:
        self._repository = repository
        self._id_generator = id_generator
        self._lecture_catalog = lecture_catalog

    def find_selected(self, learner_id: LearnerId) -> LectureId | None:
        """保存された選択(協力者の学習セッションの講義)を返す。未選択なら None。"""
        sessions = self._repository.list_by_learner(learner_id)
        return sessions[0].lecture_id if sessions else None

    def execute(
        self, learner_id: LearnerId, lecture_id: LectureId, selected_at: datetime
    ) -> Result[LectureId, AppError]:
        """lecture_id を選ぶ。すでに選択済みなら、保存済みの講義を返し、何も変えない。"""
        if self._lecture_catalog.find_by_id(lecture_id) is None:
            return err(LectureNotFoundError(f"lecture not found: {lecture_id!s}"))
        selected = self.find_selected(learner_id)
        if selected is not None:
            return ok(selected)
        session = LearningSession.start(
            id=self._id_generator.next_id(),
            learner_id=learner_id,
            lecture_id=lecture_id,
            started_at=selected_at,
        )
        # 確認と保存は排他的に行う。同時に確定されても1件に保ち、後の側は既存の選択を返す。
        stored = self._repository.save_if_learner_has_none(session)
        return ok(stored.lecture_id)
