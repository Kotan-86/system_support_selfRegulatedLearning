# 仕様: docs/spec/framework-drivers-layer.md#db
# 仕様: docs/spec/application-usecase.md#LectureCatalog
"""lecture-3（3囚人問題）の小テスト定義。"""
from __future__ import annotations

from domain.learning.quiz_definition import Question, QuizDefinition

QUIZ_TITLE = "3囚人問題：確率のパラドックスに挑戦"
QUIZ_DESCRIPTION = (
    "動画の内容を振り返り、確率の不思議を体験するクイズです。"
    "各問題の解説も併せて理解を深めましょう。"
)


def build_quiz_definition() -> QuizDefinition:
    """lecture-3 の QuizDefinition を構築する。"""
    return QuizDefinition(
        questions=(
            Question(
                index=1,
                text=(
                    "囚人Aは、看守から「Bは処刑される」と教えられました。"
                    "それを聞いた囚人Aは、自分が助かる確率が最初（1/3）から"
                    "「いくつ」に上がったと勘違いして喜んだでしょうか？"
                ),
                choices=(
                    "1/4",
                    "1/3のまま",
                    "1/2",
                    "2/3",
                ),
                correct_answer="1/2",
            ),
            Question(
                index=2,
                text=(
                    "看守から「Bは処刑される」と聞いた後、"
                    "実際の数学的な正解としては、"
                    "AとCが助かる確率はそれぞれどのようになりますか？"
                ),
                choices=(
                    "Aが1/2、Cが1/2",
                    "Aが1/3、Cが1/3",
                    "Aが1/3、Cが2/3",
                    "Aが2/3、Cが1/3",
                ),
                correct_answer="Aが1/3、Cが2/3",
            ),
            Question(
                index=3,
                text=(
                    "確率を「面積」で表した直感的な図解の説明がありました。"
                    "もし「Aが恩赦を受ける（助かる）」パターンの場合、"
                    "看守はどのような行動をとりますか？"
                ),
                choices=(
                    "必ず「Bが処刑される」と伝える",
                    "必ず「Cが処刑される」と伝える",
                    "誰が処刑されるか教えるのを拒否する",
                    "ランダムに（完全に半々の確率で）BかCのどちらかを選んで伝える",
                ),
                correct_answer="ランダムに（完全に半々の確率で）BかCのどちらかを選んで伝える",
            ),
            Question(
                index=4,
                text=(
                    "動画の後半では数式（ベイズの定理）を使った解説が行われます。"
                    "「もしBが助かるパターンの場合、看守が『Bが処刑される』と伝える確率」は"
                    "いくつとして計算されていますか？"
                ),
                choices=(
                    "0",
                    "1/3",
                    "1/2",
                    "1",
                ),
                correct_answer="0",
            ),
            Question(
                index=5,
                text=(
                    "同じように2人が残ったのに、なぜAの確率は上がらず、"
                    "Cの確率だけが跳ね上がったのでしょうか？"
                    "動画の最後で語られている、その「根本的な理由」として"
                    "正しいものはどれですか？"
                ),
                choices=(
                    "最初に質問をしたのがAだったため、Aにペナルティが課されたから",
                    "Cが看守に名指しされる可能性という「死線」をくぐり抜けたから",
                    "Cの方がもともと恩赦を受ける確率が高く設定されていたから",
                    "看守がBとCの名前を間違えて伝えてしまったから",
                ),
                correct_answer="Cが看守に名指しされる可能性という「死線」をくぐり抜けたから",
            ),
        )
    )
