# 仕様: docs/spec/domain-model.md
# 仕様: docs/spec/domain-implementation-plan.md Phase 2
"""test_domain 共通フィクスチャ。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId, LearnerId, LearningSessionId

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_learner_id() -> LearnerId:
    return LearnerId("learner-1")


@pytest.fixture
def sample_lecture_id() -> LectureId:
    return LectureId("lecture-1")


@pytest.fixture
def sample_learning_session_id() -> LearningSessionId:
    return LearningSessionId("session-1")


@pytest.fixture
def sample_quiz_definition() -> QuizDefinition:
    return QuizDefinition(
        questions=(
            Question(
                index=1,
                text="問1",
                choices=("A", "B", "C"),
                correct_answer="A",
            ),
            Question(
                index=2,
                text="問2",
                choices=("X", "Y", "Z"),
                correct_answer="Y",
            ),
        )
    )
