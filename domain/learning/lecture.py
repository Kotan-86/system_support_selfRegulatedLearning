# 仕様: docs/spec/domain-model.md#Lecture（講義）
# 仕様: docs/spec/lecture-selection.md#1-選択肢
# 仕様: docs/spec/domain-implementation-plan.md Phase 2
"""Learning コンテキストの Lecture Entity。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.learning.lecture_outline import LectureOutline
from domain.learning.quiz_definition import QuizDefinition
from domain.shared.ids import LectureId


@dataclass(frozen=True)
class Lecture:
    """講義（動画・字幕・小テスト定義の単位）。"""

    id: LectureId
    title: str
    video_url: str
    srt_path: str
    quiz_definition: QuizDefinition
    outline: LectureOutline = LectureOutline.empty()
    track: str = ""
    """系統(「理系」または「文系」)。講義の選択の画面で表示する(仕様: lecture-selection.md#1-選択肢)。"""

    @classmethod
    def create(
        cls,
        *,
        id: LectureId,
        title: str,
        video_url: str,
        srt_path: str,
        quiz_definition: QuizDefinition,
        outline: LectureOutline | None = None,
        track: str = "",
    ) -> Lecture:
        if not video_url:
            raise ValueError("Lecture video_url must not be empty")
        return cls(
            id=id,
            title=title,
            video_url=video_url,
            srt_path=srt_path,
            quiz_definition=quiz_definition,
            outline=outline or LectureOutline.empty(),
            track=track,
        )
