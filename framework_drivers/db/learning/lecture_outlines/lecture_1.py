# 仕様: docs/spec/framework-drivers-layer.md#db
"""lecture-1（球の表面積）の講義構造メタデータ。"""
from __future__ import annotations

from domain.learning.lecture_outline import (
    InVideoExercise,
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)


def build_lecture_outline() -> LectureOutline:
    """lecture-1 の LectureOutline を構築する。"""
    return LectureOutline(
        sections=(
            LectureSection(
                id="intro",
                title="球と円の面積の関係",
                start_sec=0,
                end_sec=180,
                summary="球の表面積が同じ半径の円の面積の4倍であることを紹介",
            ),
            LectureSection(
                id="approach-cylinder",
                title="円柱との等積アプローチ",
                start_sec=180,
                end_sec=420,
                summary="球の表面積を同じ半径・高さの円柱の側面積と等しいと説明",
            ),
            LectureSection(
                id="approach-projection",
                title="長方形近似と投影",
                start_sec=420,
                end_sec=660,
                summary="小さな長方形で球面を近似し、円柱へ投影する方法",
            ),
            LectureSection(
                id="approach-circles",
                title="4つの円を収める変形",
                start_sec=660,
                end_sec=900,
                summary="展開した円柱の中に4つの円をぴったり収めるための変形",
            ),
        ),
        in_video_exercises=(
            InVideoExercise(
                id="ex-cylinder",
                title="円柱との対応を確認",
                timestamp_sec=240,
                description="球の表面積と円柱の側面積が等しい理由を図で確認する",
                related_section_id="approach-cylinder",
            ),
            InVideoExercise(
                id="ex-projection",
                title="投影の幅と高さ",
                timestamp_sec=480,
                description="長方形を投影したとき幅と高さの変化が面積を保つことを確認",
                related_section_id="approach-projection",
            ),
        ),
        quiz_rubric_notes=(
            QuizRubricNote(
                question_index=1,
                note="球と円の面積の倍数関係（4倍）を正確に覚えているかを問う",
            ),
            QuizRubricNote(
                question_index=2,
                note="円柱との等積関係を図形的イメージで理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=3,
                note="投影による幅・高さの相殺を直感的に捉えているかを問う",
            ),
            QuizRubricNote(
                question_index=4,
                note="4つの円を収めるための変形（三角形）を記憶しているかを問う",
            ),
            QuizRubricNote(
                question_index=5,
                note="全体の証明の流れを統合的に理解しているかを問う",
            ),
        ),
    )
