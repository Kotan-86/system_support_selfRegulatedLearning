# 仕様: docs/spec/framework-drivers-layer.md#Composition-Root
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-2-Learning-Read
"""Learning Read 経路 — wiring.py への後方互換 re-export。"""
from framework_drivers.platform.wiring import (
    build_get_learning_snapshot_controller,
    build_video_duration_resolver,
)

__all__ = [
    "build_get_learning_snapshot_controller",
    "build_video_duration_resolver",
]
