# 仕様: docs/spec/humanities-lectures.md#受入基準 AC9
# 仕様: docs/spec/framework-drivers-layer.md#db
"""lecture-6 の講義構造メタデータ（AI による案。PO が PO確認シートで確認する）。"""
from __future__ import annotations

from domain.learning.lecture_outline import (
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)


def build_lecture_outline() -> LectureOutline:
    """lecture-6 の LectureOutline を構築する。"""
    return LectureOutline(
        sections=(
            LectureSection(
                id="def",
                title="言語とは何か",
                start_sec=0,
                end_sec=190,
                summary="言語は記号の体系であり、音と意味が結びついたものであるという導入",
            ),
            LectureSection(
                id="arbitrary",
                title="恣意性",
                start_sec=190,
                end_sec=293,
                summary="音と意味の結びつきが必然ではなく約束ごとによること",
            ),
            LectureSection(
                id="features",
                title="線条性と二重分節",
                start_sec=293,
                end_sec=438,
                summary="音を時間軸に沿って順に並べる線条性と、文を語、語を音に分ける二重分節",
            ),
            LectureSection(
                id="phonetics",
                title="音声(調音)",
                start_sec=438,
                end_sec=540,
                summary="気流・声帯などによる音の作り方",
            ),
            LectureSection(
                id="phonology",
                title="音韻と音素",
                start_sec=540,
                end_sec=670,
                summary="音素は意味を持たないが語の意味を区別する働きを持つこと(サル/マルの例)",
            ),
            LectureSection(
                id="word",
                title="語とまとめ",
                start_sec=670,
                end_sec=785,
                summary="語のレベルの話と、感情の表出との違いなどのまとめ",
            ),
        ),
        in_video_exercises=(),
        quiz_rubric_notes=(
            QuizRubricNote(
                question_index=1,
                note="言語を記号の体系として捉えられるかを問う",
            ),
            QuizRubricNote(
                question_index=2,
                note="音と意味の結びつきが必然でなく約束ごとであること(恣意性)を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=3,
                note="線条性(音が時間軸に沿って順に並ぶこと)の意味を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=4,
                note="二重分節(文を語に、語を音に分ける)を具体例に当てはめて理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=5,
                note="最小対(さる/まる)の例から、音素自体に意味はなくても語の意味を区別する働きがあることを導けるかを問う",
            ),
        ),
    )
