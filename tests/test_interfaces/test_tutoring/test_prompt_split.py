# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
# 仕様: interfaces/tutoring/prompts/（ITS 3段プロンプト分割）
"""プロンプト分割の完全性テスト。"""
from __future__ import annotations

from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from interfaces.tutoring.prompts import SYSTEM_PROMPT
from interfaces.tutoring.prompts.interface_model import INTERFACE_MODEL_PROMPT
from interfaces.tutoring.prompts.pedagogical_model import PEDAGOGICAL_MODEL_PROMPT
from interfaces.tutoring.prompts.student_model import STUDENT_MODEL_PROMPT

# 旧 SYSTEM_PROMPT に含まれていた主要キーワード（分割後もいずれかに残る）
_LEGACY_KEYWORDS: frozenset[str] = frozenset(
    {
        "## Scope",
        "## Goal",
        "Interpretation State Card",
        "Learner Utterance Type",
        "Evidence First",
        "Coach Moves",
        "Move Selection Priority",
        "Response Budget",
        "## Prohibited",
        "ORIENT_SHARED_REVIEW",
        "JOINT_EVIDENCE_CHECK",
        "FACT_REQUEST",
        "VAGUE_MEMORY",
    }
)

_STATE_CARD_FIELDS: frozenset[str] = frozenset(
    {
        "task_understanding",
        "answer_rationale",
        "felt_dissonance",
        "domain_connection",
        "process_memory",
        "LAD_connection",
        "AI_hypotheses",
        "learner_load",
    }
)


class TestPromptConstantsExist:
    """3 段プロンプト定数が prompts/ パッケージに存在する。"""

    def test_student_model_prompt_is_non_empty(self) -> None:
        assert STUDENT_MODEL_PROMPT.strip()

    def test_pedagogical_model_prompt_is_non_empty(self) -> None:
        assert PEDAGOGICAL_MODEL_PROMPT.strip()

    def test_interface_model_prompt_is_non_empty(self) -> None:
        assert INTERFACE_MODEL_PROMPT.strip()


class TestPedagogicalPromptCoachMoves:
    """Pedagogical Model プロンプトに全 Coach Move が含まれる。"""

    def test_all_coach_moves_present_in_pedagogical_prompt(self) -> None:
        for move in DialogueMove:
            assert move.value in PEDAGOGICAL_MODEL_PROMPT, (
                f"{move.value} missing from pedagogical prompt"
            )

    def test_coach_move_count_matches_enum(self) -> None:
        present = sum(
            1 for move in DialogueMove if move.value in PEDAGOGICAL_MODEL_PROMPT
        )
        assert present == len(DialogueMove)


class TestStudentPromptStateCard:
    """Student Model プロンプトに State Card 見出しと 8 軸が含まれる。"""

    def test_interpretation_state_card_heading_present(self) -> None:
        assert "Interpretation State Card" in STUDENT_MODEL_PROMPT

    def test_all_state_card_fields_present(self) -> None:
        for field in _STATE_CARD_FIELDS:
            assert field in STUDENT_MODEL_PROMPT, (
                f"{field} missing from student prompt"
            )


class TestStudentPromptUtteranceTypes:
    """Student Model プロンプトに全 Utterance Type が含まれる。"""

    def test_all_utterance_types_present(self) -> None:
        for utterance_type in LearnerUtteranceType:
            assert utterance_type.value in STUDENT_MODEL_PROMPT


class TestLegacyKeywordCoverage:
    """分割後の 3 プロンプト合算で旧 SYSTEM_PROMPT の主要キーワードをカバーする。"""

    def test_combined_prompts_cover_legacy_keywords(self) -> None:
        combined = (
            STUDENT_MODEL_PROMPT + PEDAGOGICAL_MODEL_PROMPT + INTERFACE_MODEL_PROMPT
        )
        for keyword in _LEGACY_KEYWORDS:
            assert keyword in combined, f"{keyword} missing from split prompts"

    def test_system_prompt_still_covers_legacy_keywords(self) -> None:
        for keyword in _LEGACY_KEYWORDS:
            assert keyword in SYSTEM_PROMPT, f"{keyword} missing from SYSTEM_PROMPT"
