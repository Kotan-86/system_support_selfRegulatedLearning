# 仕様: docs/spec/application-usecase.md#LearningSessionRepository
"""LearningSession 集約の永続化 Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.learning.learning_session import LearningSession
from domain.shared.ids import LectureId, LearnerId, LearningSessionId


class LearningSessionRepository(ABC):
    """1 学習者 × 1 講義の LearningSession 集約を永続化する。"""

    @abstractmethod
    def find_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSession | None:
        """指定 (learner_id, lecture_id) の Session を返す。存在しなければ None。"""

    @abstractmethod
    def list_by_learner(self, learner_id: LearnerId) -> tuple[LearningSession, ...]:
        """学習者に紐づく全 LearningSession を返す（重複チェック用）。"""

    @abstractmethod
    def save(self, session: LearningSession) -> LearningSession:
        """集約全体を upsert し、DB 確定後の集約を返す。"""

    def save_if_learner_session_count(
        self, session: LearningSession, expected_count: int
    ) -> bool:
        """学習者の Session の数が expected_count のときだけ保存し、保存したかを返す。

        仕様: docs/spec/multi-video-learning.md#2-回の選択n本目
        実装は、確認と保存を排他的に行うこと(同時の確定でも1つだけ増やす)。
        既定実装は排他しない(単一スレッド用)。
        """
        if len(self.list_by_learner(session.learner_id)) != expected_count:
            return False
        self.save(session)
        return True

    def replace_if_no_records(
        self, current_id: LearningSessionId, session: LearningSession
    ) -> bool:
        """current_id の Session に視聴ログ・小テストがなければ、それを消して session を保存する。

        仕様: docs/spec/multi-video-learning.md#8-回の選び直しfr-63-の改訂q4
        置き換えたかを返す(current_id がない・記録があるときは何も変えずに False)。
        実装は、確認と置き換えを、視聴ログ・小テストの記録と排他的に行うこと。
        """
        raise NotImplementedError
