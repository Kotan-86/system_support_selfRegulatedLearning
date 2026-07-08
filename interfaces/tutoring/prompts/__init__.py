# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""ITS 3段プロンプトパッケージ。"""
from __future__ import annotations

from interfaces.tutoring.prompts.interface_model import INTERFACE_MODEL_PROMPT
from interfaces.tutoring.prompts.legacy_system_prompt import SYSTEM_PROMPT
from interfaces.tutoring.prompts.pedagogical_model import PEDAGOGICAL_MODEL_PROMPT
from interfaces.tutoring.prompts.student_model import STUDENT_MODEL_PROMPT

__all__ = [
    "INTERFACE_MODEL_PROMPT",
    "PEDAGOGICAL_MODEL_PROMPT",
    "STUDENT_MODEL_PROMPT",
    "SYSTEM_PROMPT",
]
