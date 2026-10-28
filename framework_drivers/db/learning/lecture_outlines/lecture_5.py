# 仕様: docs/spec/humanities-lectures.md#受入基準 AC9
# 仕様: docs/spec/framework-drivers-layer.md#db
"""lecture-5 の講義構造メタデータ（AI による案。PO が PO確認シートで確認する）。"""
from __future__ import annotations

from domain.learning.lecture_outline import (
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)


def build_lecture_outline() -> LectureOutline:
    """lecture-5 の LectureOutline を構築する。"""
    return LectureOutline(
        sections=(
            LectureSection(
                id="intro",
                title="臨床心理学とカウンセリング",
                start_sec=0,
                end_sec=195,
                summary="臨床心理学が患者を対象とし、その心理を扱うこと、カウンセリングや心理臨床面接の位置づけ",
            ),
            LectureSection(
                id="attitude",
                title="面接での関わり方",
                start_sec=195,
                end_sec=300,
                summary="ロジャーズの非指示的・支持的な関わり方と、相談者と支援者の信頼関係(ラポール)",
            ),
            LectureSection(
                id="structure",
                title="治療構造",
                start_sec=300,
                end_sec=420,
                summary="時間・頻度・場所・料金などの枠組みを決め、できるだけ守ることの意味",
            ),
            LectureSection(
                id="continuity",
                title="面接の継続と療法の種類",
                start_sec=420,
                end_sec=547,
                summary="年単位で続く面接を継続するための条件や、精神分析的精神療法などの療法の種類",
            ),
            LectureSection(
                id="flow",
                title="治療の流れと形態",
                start_sec=547,
                end_sec=739,
                summary="治療の流れと面接の形態についての補足と、まとめ",
            ),
        ),
        in_video_exercises=(),
        quiz_rubric_notes=(
            QuizRubricNote(
                question_index=1,
                note="臨床心理学が一般の心理学と違い、主に患者を対象としてその心理を扱うことを理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=2,
                note="非指示的・支持的という関わり方を、相談者が自分で考えることを支える姿勢として言い換えられるかを問う",
            ),
            QuizRubricNote(
                question_index=3,
                note="ラポール(相談者と支援者の信頼関係)の意味を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=4,
                note="治療構造(時間・頻度・場所・料金などの枠組み)を決めて守る意義を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=5,
                note="面接時間が一定でないという事例から、治療構造の問題点を見抜き、まず見直すべき点を判断できるかを問う",
            ),
        ),
    )
