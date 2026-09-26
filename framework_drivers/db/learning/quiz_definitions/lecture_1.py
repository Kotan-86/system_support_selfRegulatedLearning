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
                    "動画では、球の表面積は、同じ半径 r、高さ 2r の円柱のどの部分の面積と等しいと説明されていますか。"
                ),
                choices=(
                    "上面の円だけ",
                    "上面と下面の円"
                    "側面",
                    "上面・下面・側面の合計",
                ),
                correct_answer="側面",
            ),
            Question(
                index=2,
                text=(
                    "円柱の側面を広げると、横が 2πr、縦が 2r の長方形になります。この長方形の面積はどれですか。"
                ),
                choices=(
                    "2πr^2",
                    "4πr",
                    "πr^2",
                    "4πr^2",
                ),
                correct_answer="4πr^2",
            ),
            Question(
                index=3,
                text=(
                    "球面上の小さな長方形を円柱へ投影したとき、元の長方形と投影後の長方形の面積が等しくなる理由として、動画の説明に最も近いものはどれですか。"
                ),
                choices=(
                    "幅が広がる効果と、高さが縮む効果が打ち消し合うから",
                    "幅と高さが同じ割合で広がるから",
                    "幅と高さが同じ割合で縮むから",
                    "長方形を回転させると、常に面積が等しくなるから",
                ),
                correct_answer=(
                    "幅が広がる効果と、高さが縮む効果が打ち消し合うから"
                ),
            ),
            Question(
                index=4,
                text=(
                    "半径 r の円を細い同心円状の輪に分けて並べ替えると、動画では三角形として表されています。この三角形の底辺と高さの組み合わせはどれですか。"
                ),
                choices=(
                    "底辺 πr、高さ 2r",
                    "底辺 2πr、高さ 2r",
                    "底辺 πr、高さ r",
                    "底辺 2πr、高さ r",
                ),  
                correct_answer=(
                    "底辺 2πr、高さ r"
                ),
            ),
            Question(
                index=5,
                text=(
                    "動画では、球面を角度 θ ごとの細い輪に分けています。ある輪の半径が rsinθ と分かったとき、その輪の内側の円周はどれですか。"
                ),
                choices=(
                    "rsinθ",
                    "2πrcosθ",
                    "2πrsinθ",
                    "πr^2sinθ",
                ),
                correct_answer=(
                    "2πrsinθ"
                ),
            ),
        )
    )
