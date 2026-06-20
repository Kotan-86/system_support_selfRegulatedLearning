# 仕様: docs/spec/domain-model.md#Learner（学習者）— Shared Kernel
# 仕様: docs/spec/domain-implementation-plan.md Phase 1
"""Shared Kernel の Learner Entity。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.shared.ids import LearnerId


@dataclass(frozen=True)
class Learner:
    """学習者を表す Shared Kernel Entity。"""

    id: LearnerId
