# 仕様: docs/spec/domain-model.md#Domain Service（Tutoring）
# 仕様: docs/spec/domain-implementation-plan.md Phase 5
"""NearTermExperimentPolicy のテスト。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.services.near_term_experiment_policy import (
    NearTermExperimentPolicy,
    TutorSessionStartRequest,
)
from domain.tutoring.tutor_session import TutorSession

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _tutor_session(
    *,
    tutor_id: str = "tutor-1",
    learning_session_id: str = "learning-session-1",
) -> TutorSession:
    return TutorSession.start(
        id=TutorSessionId(tutor_id),
        learning_session_id=LearningSessionId(learning_session_id),
        started_at=FIXED_NOW,
    )


class TestNearTermExperimentPolicy:
    """近い実験向け TutorSession 1 本制約を検証する。"""

    def test_allows_first_tutor_session_for_learning_session(self) -> None:
        """既存 TutorSession が無いとき新規開始を許可する。"""
        request = TutorSessionStartRequest(
            id=TutorSessionId("tutor-new"),
            learning_session_id=LearningSessionId("ls-1"),
        )
        assert NearTermExperimentPolicy.can_start_tutor_session(
            existing_sessions=(),
            request=request,
        )

    def test_rejects_second_tutor_session_for_same_learning_session(self) -> None:
        """同一 LearningSession に 2 本目の TutorSession 開始を拒否する。"""
        existing = (_tutor_session(learning_session_id="ls-1"),)
        request = TutorSessionStartRequest(
            id=TutorSessionId("tutor-2"),
            learning_session_id=LearningSessionId("ls-1"),
        )
        assert not NearTermExperimentPolicy.can_start_tutor_session(
            existing_sessions=existing,
            request=request,
        )

    def test_assert_raises_on_second_session(self) -> None:
        """assert_can_start_tutor_session は 2 本目で ValueError を送出する。"""
        existing = (_tutor_session(learning_session_id="ls-1"),)
        request = TutorSessionStartRequest(
            id=TutorSessionId("tutor-2"),
            learning_session_id=LearningSessionId("ls-1"),
        )
        with pytest.raises(ValueError):
            NearTermExperimentPolicy.assert_can_start_tutor_session(
                existing_sessions=existing,
                request=request,
            )

    def test_allows_tutor_sessions_for_different_learning_sessions(self) -> None:
        """異なる LearningSession なら複数 TutorSession を許可する。"""
        existing = (_tutor_session(learning_session_id="ls-1"),)
        request = TutorSessionStartRequest(
            id=TutorSessionId("tutor-2"),
            learning_session_id=LearningSessionId("ls-2"),
        )
        assert NearTermExperimentPolicy.can_start_tutor_session(
            existing_sessions=existing,
            request=request,
        )

    def test_policy_is_stateless(self) -> None:
        """Policy はインスタンス状態を持たず、同一入力で常に同じ結果を返す。"""
        existing = (_tutor_session(),)
        request = TutorSessionStartRequest(
            id=TutorSessionId("tutor-x"),
            learning_session_id=LearningSessionId("learning-session-1"),
        )
        first = NearTermExperimentPolicy.can_start_tutor_session(
            existing_sessions=existing, request=request
        )
        second = NearTermExperimentPolicy.can_start_tutor_session(
            existing_sessions=existing, request=request
        )
        assert first is False
        assert first == second
