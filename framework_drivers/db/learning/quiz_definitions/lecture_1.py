# 仕様: docs/spec/framework-drivers-layer.md#db
# 仕様: docs/spec/application-usecase.md#LectureCatalog
"""lecture-1（球の表面積）の小テスト定義。"""
from __future__ import annotations

from domain.learning.quiz_definition import Question, QuizDefinition

QUIZ_TITLE = "球の表面積に関する理解度テスト"
QUIZ_DESCRIPTION = (
    "動画で解説された球の表面積の性質に関する確認問題です。"
)


def build_quiz_definition() -> QuizDefinition:
    """lecture-1 の QuizDefinition を構築する。"""
    return QuizDefinition(
        questions=(
            Question(
                index=1,
                text=(
                    "動画の冒頭で紹介されている、球の表面積と"
                    "「同じ半径を持つ円の面積」の関係として正しいものはどれですか？"
                ),
                choices=(
                    "球の表面積は、円の面積の2倍である",
                    "球の表面積は、円の面積の3倍である",
                    "球の表面積は、円の面積の4倍である",
                    "球の表面積は、円の面積の8倍である",
                ),
                correct_answer="球の表面積は、円の面積の4倍である",
            ),
            Question(
                index=2,
                text=(
                    "動画の1つ目のアプローチで、球の表面積はどの図形の"
                    "側面積（上下のフタがない状態）と等しいと説明されていますか？"
                ),
                choices=(
                    "同じ半径と高さを持つ円柱",
                    "同じ底面と高さを持つ円錐",
                    "球をぴったり囲む立方体",
                    "同じ体積を持つ正四面体",
                ),
                correct_answer="同じ半径と高さを持つ円柱",
            ),
            Question(
                index=3,
                text=(
                    "球の表面をたくさんの小さな長方形で近似し、"
                    "それを外側の円柱に向かってまっすぐ投影する際、"
                    "長方形の幅と高さにはそれぞれどのような変化が起こりますか？"
                ),
                choices=(
                    "幅も高さも引き伸ばされ、面積が大きくなる",
                    "幅も高さも縮小され、面積が小さくなる",
                    "幅は引き伸ばされるが、高さは縮小され、その効果が完全に打ち消し合う",
                    "幅は縮小されるが、高さは引き伸ばされ、面積は2倍になる",
                ),
                correct_answer=(
                    "幅は引き伸ばされるが、高さは縮小され、その効果が完全に打ち消し合う"
                ),
            ),
            Question(
                index=4,
                text=(
                    "球の表面積と同じ面積を持つ長方形（展開した円柱）の中に、"
                    "4つの円をぴったり収めるために、"
                    "動画では円をどのような図形に変形させていますか？"
                ),
                choices=(
                    "正方形",
                    "三角形",
                    "台形",
                    "楕円",
                ),
                correct_answer="三角形",
            ),
            Question(
                index=5,
                text=(
                    "動画の最後で紹介されている、球体だけでなく"
                    "すべての3次元の凸図形に当てはまる影の面積と表面積の"
                    "一般的な関係について、正しいものはどれですか？"
                ),
                choices=(
                    "立体の表面積は、すべての向きの影の平均面積と等しい",
                    "立体の表面積は、すべての向きの影の平均面積の2倍になる",
                    "立体の表面積は、すべての向きの影の平均面積の3倍になる",
                    "立体の表面積は、すべての向きの影の平均面積のちょうど4倍になる",
                ),
                correct_answer=(
                    "立体の表面積は、すべての向きの影の平均面積のちょうど4倍になる"
                ),
            ),
        )
    )
