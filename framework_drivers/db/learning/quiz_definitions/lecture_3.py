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
                    "A・B・Cのうち1人だけが恩赦を受けます。Aが恩赦を受ける場合、"
                    "BとCはどちらも処刑されます。Aから「BとCのうち処刑される人を"
                    "1人教えてほしい」と尋ねられた監守は、どのように答えますか？"
                ),
                choices=(
                    "必ず「Bが処刑される」と答える",
                    "必ず「Cが処刑される」と答える",
                    "BとCからランダムに選び、それぞれ1/2の確率で答える",
                    "Aが恩赦を受ける場合は質問に答えない",
                ),
                correct_answer=(
                    "BとCからランダムに選び、それぞれ1/2の確率で答える"
                ),
            ),
            Question(
                index=2,
                text=(
                    "監守から「Bが処刑される」と聞いたAは、"
                    "「残ったAとCのどちらかが助かるので、自分が助かる確率は1/2になった」"
                    "と考えました。実際の確率の組み合わせはどれですか？"
                ),
                choices=(
                    "Aが助かる確率は1/2、Cが助かる確率も1/2",
                    "Aが助かる確率は1/3、Cが助かる確率は2/3",
                    "Aが助かる確率は2/3、Cが助かる確率は1/3",
                    "Aが助かる確率は1/3、Cが助かる確率も1/3",
                ),
                correct_answer=(
                    "Aが助かる確率は1/3、Cが助かる確率は2/3"
                ),
            ),
            Question(
                index=3,
                text=(
                    "誰が恩赦を受けるかによって、監守が「Bは処刑される」と答える確率は"
                    "異なります。その組み合わせとして正しいものはどれですか？"
                ),
                choices=(
                    "Aが助かる場合は1、Bが助かる場合は0、Cが助かる場合は1/2",
                    "Aが助かる場合は1/2、Bが助かる場合は1、Cが助かる場合は0",
                    "Aが助かる場合は0、Bが助かる場合は1/2、Cが助かる場合は1",
                    "Aが助かる場合は1/2、Bが助かる場合は0、Cが助かる場合は1",
                ),
                correct_answer=(
                    "Aが助かる場合は1/2、Bが助かる場合は0、Cが助かる場合は1"
                ),
            ),
            Question(
                index=4,
                text=(
                    "最初はA・B・Cが助かる確率がそれぞれ1/3です。監守が「Bは処刑される」"
                    "と答える確率を考えると、「Aが助かり、Bと言われる」確率は1/6、"
                    "「Cが助かり、Bと言われる」確率は1/3になります。"
                    "Bと言われた場合にAが助かる確率はどれですか？"
                ),
                choices=(
                    "1/2",
                    "1/3",
                    "2/3",
                    "1/6",
                ),
                correct_answer=(
                    "1/3"
                ),
            ),
            Question(
                index=5,
                text=(
                    "質問を「A・B・Cのうち処刑される人を1人教えてほしい」に変更し、"
                    "監守が処刑される2人からランダムに1人を答えるとします。"
                    "この条件で監守が「Bは処刑される」と答えた場合、"
                    "AとCが助かる確率はどうなりますか？"
                ),
                choices=(
                    "Aが1/3、Cが2/3になる",
                    "Aが2/3、Cが1/3になる",
                    "Aが1/3、Cも1/3になる",
                    "Aが1/2、Cも1/2になる",
                ),
                correct_answer=(
                    "Aが1/2、Cも1/2になる"
                ),
            ),
        )
    )
