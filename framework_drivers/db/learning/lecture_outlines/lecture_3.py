# 仕様: docs/spec/framework-drivers-layer.md#db
"""lecture-3（3囚人問題）の講義構造メタデータ。"""
from __future__ import annotations

from domain.learning.lecture_outline import (
    InVideoExercise,
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)


def build_lecture_outline() -> LectureOutline:
    """lecture-3 の LectureOutline を構築する。"""
    return LectureOutline(
        sections=(
            LectureSection(
                id="intro",
                title="3囚人問題の設定",
                start_sec=0,
                end_sec=120,
                summary="3人の囚人と処刑・赦免の確率設定",
            ),
            LectureSection(
                id="prisoner-a-reasoning",
                title="囚人Aの誤った推論",
                start_sec=120,
                end_sec=300,
                summary="「Bは処刑される」情報を聞いた囚人Aの1/2勘違い",
            ),
            LectureSection(
                id="conditional-update",
                title="正しい条件付き確率",
                start_sec=300,
                end_sec=540,
                summary="看守の発言を条件とした確率更新",
            ),
            LectureSection(
                id="paradox",
                title="パラドックスの整理",
                start_sec=540,
                end_sec=720,
                summary="直感と正しい確率の乖離をまとめる",
            ),
        ),
        in_video_exercises=(
            InVideoExercise(
                id="ex-prisoner-a",
                title="囚人Aの確率予測",
                timestamp_sec=200,
                description="看守の発言後、囚人Aが自分の生存確率をどう更新するか考える",
                related_section_id="prisoner-a-reasoning",
            ),
            InVideoExercise(
                id="ex-correct-probability",
                title="正しい確率の計算",
                timestamp_sec=400,
                description="条件付き確率で各囚人の生存確率を再計算する",
                related_section_id="conditional-update",
            ),
        ),
        quiz_rubric_notes=(
            QuizRubricNote(
                question_index=1,
                note="囚人Aの1/2勘違い（初期1/3からの誤った更新）を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=2,
                note="看守の発言が与える情報の内容を正しく解釈しているかを問う",
            ),
            QuizRubricNote(
                question_index=3,
                note="条件付き確率の計算を追えているかを問う",
            ),
            QuizRubricNote(
                question_index=4,
                note="モンティ・ホール問題との類似・相違を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=5,
                note="パラドックスの本質（情報更新の誤り）を言語化できるかを問う",
            ),
        ),
    )
