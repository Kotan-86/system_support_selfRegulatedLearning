# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""StudentModelPromptBuilder の Stage 1 プレースホルダ注入テスト。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from domain.learning.lecture import Lecture
from domain.learning.lecture_outline import (
    InVideoExercise,
    LectureOutline,
    LectureSection,
)
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    MessageId,
    ViewingEventId,
)
from domain.tutoring.message import Message, MessageRole
from interfaces.tutoring.context_formatters import EMPTY_PLACEHOLDER
from interfaces.tutoring.student_model_prompt_builder import StudentModelPromptBuilder

FIXED_NOW = datetime(2026, 2, 23, 11, 18, 42, tzinfo=timezone.utc)


def _lecture_with_outline() -> Lecture:
    outline = LectureOutline(
        sections=(
            LectureSection(
                id="sec-1",
                title="導入パート",
                start_sec=0,
                end_sec=120,
                summary="講義の導入",
            ),
        ),
        in_video_exercises=(
            InVideoExercise(
                id="ex-1",
                title="確認演習",
                timestamp_sec=60,
                description="基本概念の確認",
            ),
        ),
    )
    return Lecture.create(
        id=LectureId("lecture-1"),
        title="サンプル講義",
        video_url="https://example.com/video.mp4",
        srt_path="/path/to/missing.srt",
        quiz_definition=QuizDefinition(
            questions=(
                Question(
                    index=1,
                    text="問1",
                    choices=("A", "B"),
                    correct_answer="A",
                ),
            )
        ),
        outline=outline,
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


class TestStudentModelPromptBuilder:
    """Stage 1 プロンプトへのコンテキスト注入。"""

    def test_lecture_outline_in_student_prompt(self) -> None:
        builder = StudentModelPromptBuilder()
        prompt = builder.build(
            _empty_snapshot(),
            (),
            "振り返りをしたいです",
            _lecture_with_outline(),
        )

        assert "講義構造" in prompt
        assert "セクション: 導入パート" in prompt
        assert EMPTY_PLACEHOLDER not in prompt.split("講義構造")[-1][:200]

    def test_empty_outline_uses_placeholder(self) -> None:
        lecture = Lecture.create(
            id=LectureId("lecture-1"),
            title="サンプル講義",
            video_url="https://example.com/video.mp4",
            srt_path="/path/to/missing.srt",
            quiz_definition=QuizDefinition(
                questions=(
                    Question(
                        index=1,
                        text="問1",
                        choices=("A", "B"),
                        correct_answer="A",
                    ),
                )
            ),
        )
        prompt = StudentModelPromptBuilder().build(
            _empty_snapshot(),
            (),
            "質問です",
            lecture,
        )

        assert f"講義構造: {EMPTY_PLACEHOLDER}" in prompt

    def test_includes_standard_context_placeholders(self) -> None:
        messages = (
            Message.create(
                id=MessageId("msg-1"),
                role=MessageRole.USER,
                content="前の質問",
                created_at=FIXED_NOW,
            ),
        )
        prompt = StudentModelPromptBuilder().build(
            _empty_snapshot(),
            messages,
            "続きの質問",
            _lecture_with_outline(),
        )

        assert "user: 前の質問" in prompt
        assert "ユーザーの直近の発話: 続きの質問" in prompt
        assert "LADデータ（視聴ログ等）:" in prompt
        assert "テスト結果:" in prompt
        assert "講義字幕:" in prompt

    def test_lad_digest_in_student_prompt_when_viewing_events_exist(self) -> None:
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(
                ViewingEvent.create(
                    id=ViewingEventId("event-1"),
                    occurred_at=FIXED_NOW,
                    video_position=0,
                    action=ViewingAction.PLAY,
                    position_delta=0,
                ),
            ),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        prompt = StudentModelPromptBuilder().build(
            snapshot,
            (),
            "動画の最初の方を見ました",
            _lecture_with_outline(),
        )

        assert "## 視聴ログ要約" in prompt
        assert "再生開始" in prompt
