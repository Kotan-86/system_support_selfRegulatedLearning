# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
# 仕様: docs/spec/domain-model.md#LectureOutline
"""プロンプト組み立て用のコンテキスト整形ユーティリティ。"""
from __future__ import annotations

import os
from pathlib import Path

from domain.learning.lecture import Lecture
from domain.learning.lecture_outline import LectureOutline
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.message import Message

from interfaces.learning.services.quiz_result_rows import build_quiz_result_rows
from interfaces.tutoring.srt import get_segments_for_times, parse_srt_file

EMPTY_PLACEHOLDER = "(なし)"
HISTORY_EMPTY_PLACEHOLDER = "(履歴なし)"


def format_timestamp(occurred_at) -> str:
    return occurred_at.replace(microsecond=0).isoformat()


def format_history(messages: tuple[Message, ...]) -> str:
    """対話履歴をプロンプト用の文字列に整形する。"""
    lines = [f"{message.role.value}: {message.content}" for message in messages]
    return "\n".join(lines)


def format_lecture_log(snapshot: LearningSnapshot) -> str:
    """視聴イベントを時系列で列挙する。データが無い場合は "(なし)"。"""
    if not snapshot.viewing_events:
        return EMPTY_PLACEHOLDER

    lines = []
    for event in snapshot.viewing_events:
        lines.append(
            f"{format_timestamp(event.occurred_at)} "
            f"action={event.action.value} "
            f"current_time={event.video_position} "
            f"duration={event.position_delta}"
        )
    return "\n".join(lines)


def format_quiz_result(snapshot: LearningSnapshot, lecture: Lecture) -> str:
    """最新小テストのスコアと各問詳細を列挙する。データが無い場合は "(なし)"。"""
    attempt = snapshot.latest_quiz_attempt
    answers = snapshot.quiz_answers
    if attempt is None and not answers:
        return EMPTY_PLACEHOLDER

    parts: list[str] = []
    if attempt is not None:
        parts.append(
            f"スコア: {attempt.score_numerator}/{attempt.score_denominator}"
        )

    questions_by_index = {
        question.index: question for question in lecture.quiz_definition.questions
    }
    rows = build_quiz_result_rows(answers, lecture.quiz_definition)
    for row in rows:
        question = questions_by_index.get(row.question_index)
        lines = [f"問{row.question_index}:", f"  問題文: {row.question_text}"]
        if question is not None:
            lines.append(f"  選択肢: {', '.join(question.choices)}")
        lines.append(f"  学習者の解答: {row.selected_choice}")
        if question is not None:
            lines.append(f"  正解選択肢: {question.correct_answer}")
        lines.append(f"  正解フラグ: {1 if row.is_correct else 0}")
        parts.append("\n".join(lines))

    return "\n".join(parts) if parts else EMPTY_PLACEHOLDER


def _format_timecode(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def _format_time_range(start_sec: int, end_sec: int | None) -> str:
    start = _format_timecode(start_sec)
    if end_sec is None:
        return start
    return f"{start}–{_format_timecode(end_sec)}"


def format_lecture_outline(outline: LectureOutline) -> str:
    """講義構造メタデータをプロンプト用に整形する。"""
    if outline.is_empty:
        return EMPTY_PLACEHOLDER

    parts: list[str] = ["## 講義構造"]

    for section in outline.sections:
        time_range = _format_time_range(section.start_sec, section.end_sec)
        parts.append(f"### セクション: {section.title} ({time_range})")
        if section.summary:
            parts.append(f"  概要: {section.summary}")

    for exercise in outline.in_video_exercises:
        timecode = _format_timecode(exercise.timestamp_sec)
        parts.append(f"### 演習: {exercise.title} ({timecode})")
        parts.append(f"  説明: {exercise.description}")

    if outline.quiz_rubric_notes:
        parts.append("### 小テスト採点意図")
        for note in outline.quiz_rubric_notes:
            parts.append(f"  問{note.question_index}: {note.note}")

    return "\n".join(parts)


def resolve_srt_path(lecture: Lecture) -> Path | None:
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


def format_lecture_transcript(snapshot: LearningSnapshot, lecture: Lecture) -> str:
    """視聴位置に対応する講義字幕を抽出する。SRT 未設定・なしの場合は "(なし)"。"""
    if snapshot.lecture_transcript_excerpts:
        text = "\n".join(snapshot.lecture_transcript_excerpts)
        return text if text else EMPTY_PLACEHOLDER

    srt_path = resolve_srt_path(lecture)
    if srt_path is None:
        return EMPTY_PLACEHOLDER

    try:
        segments = parse_srt_file(srt_path)
    except (OSError, ValueError):
        return EMPTY_PLACEHOLDER

    times = [event.video_position for event in snapshot.viewing_events]
    text = get_segments_for_times(segments, times)
    return text if text else EMPTY_PLACEHOLDER
