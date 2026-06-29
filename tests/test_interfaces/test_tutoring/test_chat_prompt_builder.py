# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""DefaultChatPromptBuilder の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.quiz_attempt import QuizAnswer, QuizAttempt
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    MessageId,
    QuizAttemptId,
    ViewingEventId,
)
from domain.tutoring.message import Message, MessageRole
from interfaces.tutoring.chat_prompt_builder import DefaultChatPromptBuilder

FIXED_NOW = datetime(2026, 2, 23, 11, 18, 42, tzinfo=timezone.utc)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LECTURE_1_SRT = PROJECT_ROOT / "lectures" / "lecture-1" / "subtitles.srt"


def _lecture(*, srt_path: str = "/path/to/missing.srt") -> Lecture:
    return Lecture.create(
        id=LectureId("lecture-1"),
        title="サンプル講義",
        video_url="https://example.com/video.mp4",
        srt_path=srt_path,
        quiz_definition=QuizDefinition(
            questions=(
                Question(
                    index=1,
                    text="問1の問題文",
                    choices=("A", "B"),
                    correct_answer="A",
                ),
                Question(
                    index=2,
                    text="問2の問題文",
                    choices=("A", "B", "C"),
                    correct_answer="A",
                ),
            )
        ),
    )


def _empty_snapshot() -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("session-1"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


def _viewing_event(
    *,
    video_position: int = 0,
    action: ViewingAction = ViewingAction.PLAY,
    position_delta: float = 0.0,
) -> ViewingEvent:
    return ViewingEvent.create(
        id=ViewingEventId("event-1"),
        occurred_at=FIXED_NOW,
        video_position=video_position,
        action=action,
        position_delta=position_delta,
    )


class TestDefaultChatPromptBuilder:
    """DefaultChatPromptBuilder の振る舞いを LearningSnapshot と Lecture で検証する。"""

    def test_empty_snapshot_uses_placeholders(self) -> None:
        builder = DefaultChatPromptBuilder()
        prompt = builder.build(
            _empty_snapshot(),
            (),
            "質問です",
            _lecture(),
        )

        assert "LADデータ（視聴ログ等）: (なし)" in prompt
        assert "テスト結果: (なし)" in prompt
        assert "講義字幕: (なし)" in prompt
        assert "会話履歴: (履歴なし)" in prompt
        assert "ユーザーの直近の発話: 質問です" in prompt

    def test_prompt_includes_viewing_log_lines(self) -> None:
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(_viewing_event(video_position=0),),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        prompt = DefaultChatPromptBuilder().build(
            snapshot,
            (),
            "再生位置について",
            _lecture(),
        )

        assert "action=play current_time=0 duration=0.0" in prompt
        assert "2026-02-23T11:18:42" in prompt

    def test_prompt_includes_quiz_result(self) -> None:
        answers = (
            QuizAnswer(question_index=1, selected_answer="A", is_correct=True),
            QuizAnswer(question_index=2, selected_answer="B", is_correct=False),
        )
        attempt = QuizAttempt.create(
            id=QuizAttemptId("attempt-1"),
            attempted_at=datetime(2026, 2, 23, 12, 0, 0, tzinfo=timezone.utc),
            score_numerator=4,
            score_denominator=5,
            answers=answers,
        )
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(),
            latest_quiz_attempt=attempt,
            quiz_answers=answers,
        )
        prompt = DefaultChatPromptBuilder().build(
            snapshot,
            (),
            "小テストの問2がわかりません",
            _lecture(),
        )

        assert "スコア: 4/5" in prompt
        assert "問1:" in prompt
        assert "問題文: 問1の問題文" in prompt
        assert "選択肢: A, B" in prompt
        assert "学習者の解答: A" in prompt
        assert "正解選択肢: A" in prompt
        assert "正解フラグ: 1" in prompt
        assert "問2:" in prompt
        assert "問題文: 問2の問題文" in prompt
        assert "選択肢: A, B, C" in prompt
        assert "学習者の解答: B" in prompt
        assert "正解フラグ: 0" in prompt

    def test_prompt_includes_message_history(self) -> None:
        messages = (
            Message.create(
                id=MessageId("msg-1"),
                role=MessageRole.USER,
                content="前の質問",
                created_at=FIXED_NOW,
            ),
            Message.create(
                id=MessageId("msg-2"),
                role=MessageRole.ASSISTANT,
                content="前の回答",
                created_at=FIXED_NOW,
            ),
        )
        prompt = DefaultChatPromptBuilder().build(
            _empty_snapshot(),
            messages,
            "続きの質問",
            _lecture(),
        )

        assert "user: 前の質問" in prompt
        assert "assistant: 前の回答" in prompt

    def test_prompt_uses_lecture_transcript_excerpts_when_present(self) -> None:
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(),
            latest_quiz_attempt=None,
            quiz_answers=(),
            lecture_transcript_excerpts=("線形代数の基礎", "ベクトルとは"),
        )
        prompt = DefaultChatPromptBuilder().build(
            snapshot,
            (),
            "字幕について",
            _lecture(),
        )

        assert "講義字幕: 線形代数の基礎\nベクトルとは" in prompt

    @pytest.mark.skipif(
        not LECTURE_1_SRT.is_file(), reason="lectures/lecture-1/subtitles.srt が無い"
    )
    def test_prompt_includes_srt_text_for_viewing_position(self) -> None:
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(_viewing_event(video_position=15),),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        prompt = DefaultChatPromptBuilder().build(
            snapshot,
            (),
            "このあたりの説明がわかりません",
            _lecture(srt_path=str(LECTURE_1_SRT)),
        )

        assert "講義字幕" in prompt
        assert "整数倍" in prompt
