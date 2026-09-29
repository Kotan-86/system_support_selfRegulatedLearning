# 仕様: docs/spec/dialog-log-save.md#保存-API
"""SaveDialogLog の Request / Response DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from domain.shared.ids import LearnerId, LectureId, TutorSessionId
from domain.tutoring.message import Message


class EndMethod(str, Enum):
    END_BUTTON = "end_button"
    PAGE_LEAVE = "page_leave"


@dataclass(frozen=True)
class SaveDialogLogRequest:
    learner_id: LearnerId
    lecture_id: LectureId
    end_method: EndMethod
    received_at: datetime


@dataclass(frozen=True)
class SaveDialogLogResponse:
    tutor_session_id: TutorSessionId
    ended_at: datetime
    end_method: EndMethod


@dataclass(frozen=True)
class DialogLog:
    participant_id: str
    lecture_id: str
    learning_session_id: str
    tutor_session_id: str
    ended_at: datetime
    end_method: EndMethod
    messages: tuple[Message, ...]
