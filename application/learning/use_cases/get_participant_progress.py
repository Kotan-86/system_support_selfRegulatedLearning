# 仕様: docs/spec/multi-video-learning.md#1-協力者の進行状態
"""協力者の進行状態を、2つの DB の既存の表から決める(スキーマは変えない。Q3)。"""
from __future__ import annotations

from application.learning.dto.participant_progress import (
    TOTAL_ROUNDS,
    ParticipantProgress,
    ProgressState,
    round_order,
)
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.ports.round_record_query import RoundRecordQuery
from domain.shared.ids import LearnerId


class GetParticipantProgressUseCase:
    def __init__(
        self, repository: LearningSessionRepository, round_records: RoundRecordQuery
    ) -> None:
        self._repository = repository
        self._round_records = round_records

    def execute(self, learner_id: LearnerId) -> ParticipantProgress:
        """終えた回 = 終了ボタンの対話ログがある学習セッション。今の回 = 終えていない最も古い学習セッション。"""
        sessions = round_order(self._repository.list_by_learner(learner_id))
        ended = self._round_records.ended_learning_session_ids([s.id for s in sessions])
        finished = tuple(s.lecture_id for s in sessions if s.id in ended)
        unfinished = [s for s in sessions if s.id not in ended]
        if len(finished) >= TOTAL_ROUNDS:
            return ParticipantProgress(
                ProgressState.FINISHED, TOTAL_ROUNDS, finished_lecture_ids=finished
            )
        round_number = len(finished) + 1
        if not unfinished:
            return ParticipantProgress(
                ProgressState.WAITING, round_number, finished_lecture_ids=finished
            )
        current = unfinished[0]
        has_records = bool(current.viewing_events or current.quiz_attempts) or bool(
            self._round_records.learning_session_ids_with_tutor_session([current.id])
        )
        return ParticipantProgress(
            ProgressState.LEARNING,
            round_number,
            current_lecture_id=current.lecture_id,
            current_learning_session_id=current.id,
            current_has_records=has_records,
            finished_lecture_ids=finished,
        )
