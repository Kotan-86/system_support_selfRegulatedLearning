# 仕様: docs/spec/domain-model.md#Domain Service（Tutoring）
# 仕様: docs/spec/domain-implementation-plan.md Phase 5
"""近い実験向け TutorSession 制約の Domain Service。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.tutor_session import TutorSession


@dataclass(frozen=True)
class TutorSessionStartRequest:
    """新規 TutorSession 開始要求。"""

    id: TutorSessionId
    learning_session_id: LearningSessionId


class NearTermExperimentPolicy:
    """
    近い実験向け制約: 1 LearningSession に TutorSession は 1 本まで。

    状態を持たず、既存 Session 一覧と新規要求から許可/拒否を判定する。
    """

    @staticmethod
    def can_start_tutor_session(
        *,
        existing_sessions: Iterable[TutorSession],
        request: TutorSessionStartRequest,
    ) -> bool:
        for existing in existing_sessions:
            if existing.learning_session_id == request.learning_session_id:
                return False
        return True

    @staticmethod
    def assert_can_start_tutor_session(
        *,
        existing_sessions: Iterable[TutorSession],
        request: TutorSessionStartRequest,
    ) -> None:
        if not NearTermExperimentPolicy.can_start_tutor_session(
            existing_sessions=existing_sessions,
            request=request,
        ):
            raise ValueError(
                "Near-term experiment allows only one TutorSession per LearningSession"
            )
