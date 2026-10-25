# 仕様: docs/spec/humanities-lectures.md#受入基準 AC9
# 仕様: docs/spec/framework-drivers-layer.md#db
"""lecture-4 の講義構造メタデータ（AI による案。PO が PO確認シートで確認する）。"""
from __future__ import annotations

from domain.learning.lecture_outline import (
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)


def build_lecture_outline() -> LectureOutline:
    """lecture-4 の LectureOutline を構築する。"""
    return LectureOutline(
        sections=(
            LectureSection(
                id="intro",
                title="律と令の概要",
                start_sec=0,
                end_sec=90,
                summary="律令とは何か。律は刑罰の決まり、令は行政法にあたる決まりであるという全体像",
            ),
            LectureSection(
                id="ritsu",
                title="律:罪と刑罰",
                start_sec=90,
                end_sec=240,
                summary="五刑(笞・杖・徒・流・死)など、悪事をした場合の罰し方と、国家や天皇への罪が重いこと",
            ),
            LectureSection(
                id="central",
                title="令:中央の政治機構",
                start_sec=240,
                end_sec=430,
                summary="二官八省一台五衛府など、中央の官司の役割と、政策が実施されるまでの流れ",
            ),
            LectureSection(
                id="local",
                title="令:地方行政",
                start_sec=430,
                end_sec=495,
                summary="国・郡・里の区分と七道など、地方の統治の仕組み",
            ),
            LectureSection(
                id="nobles",
                title="貴族と官位相当制",
                start_sec=495,
                end_sec=710,
                summary="位階の制度、官位相当制、位田・位封・位禄などの貴族の待遇",
            ),
            LectureSection(
                id="people",
                title="民衆の負担と税",
                start_sec=710,
                end_sec=892,
                summary="蔭位の制、租・調・庸、雑徭、運脚、防人などの民衆の負担とまとめ",
            ),
        ),
        in_video_exercises=(),
        quiz_rubric_notes=(
            QuizRubricNote(
                question_index=1,
                note="律(刑罰の決まり)と令(行政などの決まり)の違いを区別して理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=2,
                note="中央で政策が決まり実施される流れ(太政官の上位の貴族の合議、天皇の許可、八省の実務)を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=3,
                note="官位相当制(位に応じて就ける役職が対応すること)の意味を理解しているかを問う",
            ),
            QuizRubricNote(
                question_index=4,
                note="租・調・庸のそれぞれの内容を正しく対応づけて覚えているかを問う",
            ),
            QuizRubricNote(
                question_index=5,
                note="都まで品物を運び、食料も自己負担する運脚を、他の負担(雑徭・防人・衛士)と区別して判断できるかを問う",
            ),
        ),
    )
