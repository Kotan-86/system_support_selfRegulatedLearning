# 仕様: docs/spec/framework-drivers-layer.md#db
"""lecture-2（モンティ・ホール問題）の講義構造メタデータ。"""
from __future__ import annotations

from domain.learning.lecture_outline import (
    InVideoExercise,
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)


def build_lecture_outline() -> LectureOutline:
    """lecture-2 の LectureOutline を構築する。"""
    return LectureOutline(
        sections=(
            LectureSection(
                id="intro",
                title="問題設定",
                start_sec=0,
                end_sec=120,
                summary="3つの扉と1つの当たり、司会者がハズレを1つ開ける設定",
            ),
            LectureSection(
                id="intuition-trap",
                title="直感の罠",
                start_sec=120,
                end_sec=300,
                summary="残り2扉が半々（1/2）に見える理由",
            ),
            LectureSection(
                id="conditional-probability",
                title="条件付き確率の説明",
                start_sec=300,
                end_sec=540,
                summary="司会者の行動を条件とした確率の再計算",
            ),
            LectureSection(
                id="conclusion",
                title="結論とまとめ",
                start_sec=540,
                end_sec=720,
                summary="扉を変える方が有利である理由の整理",
            ),
        ),
        in_video_exercises=(
            InVideoExercise(
                id="ex-intuition",
                title="直感チェック",
                timestamp_sec=180,
                description="残り2扉の確率を直感で予測し、結果と比較する",
                related_section_id="intuition-trap",
            ),
            InVideoExercise(
                id="ex-simulation",
                title="シミュレーション確認",
                timestamp_sec=420,
                description="多数試行で変える・変えないの勝率を比較する",
                related_section_id="conditional-probability",
            ),
        ),
        quiz_rubric_notes=(
            QuizRubricNote(
                question_index=1,
                note="1/2直感の原因（残り2扉の均等配分の誤解）を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=2,
                note="司会者の行動が情報を与えることを理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=3,
                note="条件付き確率の計算手順を追えているかを問う",
            ),
            QuizRubricNote(
                question_index=4,
                note="変える戦略の優位性を定量的に説明できるかを問う",
            ),
            QuizRubricNote(
                question_index=5,
                note="直感と論理のギャップを言語化できるかを問う",
            ),
        ),
    )
