# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""ChatPromptBuilder Port の具象実装（app/main.py の _format_* 移行先）。"""
from __future__ import annotations

import os
from pathlib import Path

from app.srt import get_segments_for_times, parse_srt_file
from application.tutoring.ports.chat_prompt_builder import ChatPromptBuilder
from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.message import Message

from interfaces.tutoring.prompts import SYSTEM_PROMPT

_EMPTY_PLACEHOLDER = "(なし)"
_HISTORY_EMPTY_PLACEHOLDER = "(履歴なし)"


def _format_timestamp(occurred_at) -> str:
    return occurred_at.replace(microsecond=0).isoformat()


def _format_history(messages: tuple[Message, ...]) -> str:
    """対話履歴をプロンプト用の文字列に整形する。"""
    lines = [f"{message.role.value}: {message.content}" for message in messages]
    return "\n".join(lines)


def _format_lecture_log(snapshot: LearningSnapshot) -> str:
    """視聴イベントを時系列で列挙する。データが無い場合は "(なし)"。"""
    if not snapshot.viewing_events:
        return _EMPTY_PLACEHOLDER

    lines = []
    for event in snapshot.viewing_events:
        lines.append(
            f"{_format_timestamp(event.occurred_at)} "
            f"action={event.action.value} "
            f"current_time={event.video_position} "
            f"duration={event.position_delta}"
        )
    return "\n".join(lines)


def _format_quiz_result(snapshot: LearningSnapshot) -> str:
    """最新小テストのスコアと各問正誤を列挙する。データが無い場合は "(なし)"。"""
    attempt = snapshot.latest_quiz_attempt
    answers = snapshot.quiz_answers
    if attempt is None and not answers:
        return _EMPTY_PLACEHOLDER

    parts: list[str] = []
    if attempt is not None:
        parts.append(
            f"スコア: {attempt.score_numerator}/{attempt.score_denominator}"
        )
    for answer in answers:
        result = "正解" if answer.is_correct else "不正解"
        parts.append(f"問{answer.question_index}: {result}")

    return "\n".join(parts) if parts else _EMPTY_PLACEHOLDER


def _resolve_srt_path(lecture: Lecture) -> Path | None:
    """講義の SRT パスを解決する。存在しない場合は None。"""
    if lecture.srt_path:
        path = Path(lecture.srt_path)
        if path.exists():
            return path

    srt_path_str = os.environ.get("LECTURE_SRT_PATH")
    if srt_path_str:
        path = Path(srt_path_str)
        if path.exists():
            return path

    return None


def _build_lecture_transcript(snapshot: LearningSnapshot, lecture: Lecture) -> str:
    """視聴位置に対応する講義字幕を抽出する。SRT 未設定・なしの場合は "(なし)"。"""
    if snapshot.lecture_transcript_excerpts:
        text = "\n".join(snapshot.lecture_transcript_excerpts)
        return text if text else _EMPTY_PLACEHOLDER

    srt_path = _resolve_srt_path(lecture)
    if srt_path is None:
        return _EMPTY_PLACEHOLDER

    try:
        segments = parse_srt_file(srt_path)
    except (OSError, ValueError):
        return _EMPTY_PLACEHOLDER

    times = [event.video_position for event in snapshot.viewing_events]
    text = get_segments_for_times(segments, times)
    return text if text else _EMPTY_PLACEHOLDER


class DefaultChatPromptBuilder(ChatPromptBuilder):
    """LearningSnapshot と対話履歴から LLM プロンプト文字列を組み立てる。"""

    def build(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        history_str = _format_history(messages)
        lecture_log_str = _format_lecture_log(snapshot)
        quiz_result_str = _format_quiz_result(snapshot)
        lecture_transcript_str = _build_lecture_transcript(snapshot, lecture)

        return SYSTEM_PROMPT.format(
            history=history_str or _HISTORY_EMPTY_PLACEHOLDER,
            user_message=user_message,
            lecture_log=lecture_log_str,
            quiz_result=quiz_result_str,
            lecture_transcript=lecture_transcript_str,
        )
