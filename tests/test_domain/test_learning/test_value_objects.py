# 仕様: docs/spec/domain-model.md#Value Object（Learning）
# 仕様: docs/spec/domain-model.md#Learner（学習者）— Shared Kernel
# 仕様: docs/spec/domain-implementation-plan.md Phase 1
"""
Learning コンテキストの Value Object と Shared Kernel の Learner Entity の単体テスト。

Phase 1 では ViewingAction, QuizDefinition, Question, Learner の不変条件を定義する。
"""
from __future__ import annotations

import dataclasses

import pytest

from domain.learning.quiz_definition import Question, QuizDefinition
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LearnerId
from domain.shared.learner import Learner

EXPECTED_VIEWING_ACTIONS: frozenset[str] = frozenset(
    {
        "play",
        "pause",
        "forward_skip",
        "backward_skip",
        "forward_seek",
        "backward_seek",
    }
)


def _sample_question(*, index: int = 1, text: str = "問1の本文") -> Question:
    return Question(
        index=index,
        text=text,
        choices=("A", "B", "C"),
        correct_answer="A",
    )


class TestViewingAction:
    """ViewingAction 列挙の不変条件を検証する。"""

    def test_has_six_values(self) -> None:
        """ViewingAction は 6 種類の値を持つ。"""
        assert len(ViewingAction) == 6

    def test_values_match_spec(self) -> None:
        """play / pause / forward_skip / backward_skip / forward_seek / backward_seek が定義されている。"""
        actual = {member.value for member in ViewingAction}
        assert actual == EXPECTED_VIEWING_ACTIONS

    @pytest.mark.parametrize(
        ("member_name", "expected_value"),
        [
            ("PLAY", "play"),
            ("PAUSE", "pause"),
            ("FORWARD_SKIP", "forward_skip"),
            ("BACKWARD_SKIP", "backward_skip"),
            ("FORWARD_SEEK", "forward_seek"),
            ("BACKWARD_SEEK", "backward_seek"),
        ],
    )
    def test_member_value(self, member_name: str, expected_value: str) -> None:
        """各メンバーが仕様どおりの文字列値を持つ。"""
        member = ViewingAction[member_name]
        assert member.value == expected_value


class TestQuestion:
    """Question Value Object の不変条件を検証する。"""

    def test_accepts_non_empty_text(self) -> None:
        """text が非空の Question を生成できる。"""
        question = _sample_question(text="設問本文")
        assert question.text == "設問本文"

    def test_rejects_empty_text(self) -> None:
        """text が空文字のとき ValueError で拒否される。"""
        with pytest.raises(ValueError):
            _sample_question(text="")


class TestQuizDefinition:
    """QuizDefinition Value Object の不変条件を検証する。"""

    def test_accepts_one_or_more_questions(self) -> None:
        """questions が 1 件以上のとき QuizDefinition を生成できる。"""
        definition = QuizDefinition(questions=(_sample_question(),))
        assert len(definition.questions) == 1

    def test_rejects_empty_questions(self) -> None:
        """questions が 0 件のとき ValueError で拒否される。"""
        with pytest.raises(ValueError):
            QuizDefinition(questions=())

    def test_rejects_duplicate_question_index(self) -> None:
        """同一 QuizDefinition 内で question index が重複すると拒否される。"""
        with pytest.raises(ValueError):
            QuizDefinition(
                questions=(
                    _sample_question(index=1),
                    _sample_question(index=1, text="別の問"),
                )
            )

    def test_accepts_unique_question_indexes(self) -> None:
        """index が一意なら複数 Question を持てる。"""
        definition = QuizDefinition(
            questions=(
                _sample_question(index=1),
                _sample_question(index=2, text="問2"),
            )
        )
        assert [q.index for q in definition.questions] == [1, 2]


class TestLearner:
    """Shared Kernel の Learner Entity の不変条件を検証する。"""

    def test_accepts_learner_id(self) -> None:
        """LearnerId を持つ Learner を生成できる。"""
        learner = Learner(id=LearnerId("p1"))
        assert learner.id == LearnerId("p1")

    def test_has_only_id_field(self) -> None:
        """Learner は id: LearnerId のみを持つ最小 Entity である。"""
        fields = {field.name for field in dataclasses.fields(Learner)}
        assert fields == {"id"}

    def test_rejects_empty_learner_id(self) -> None:
        """空の LearnerId は Learner 生成時に拒否される。"""
        with pytest.raises(ValueError):
            Learner(id=LearnerId(""))
