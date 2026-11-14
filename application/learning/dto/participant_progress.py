# 仕様: docs/spec/multi-video-learning.md#1-協力者の進行状態
"""協力者の進行状態(共有IF。PBI-A が固定し、PBI-B・PBI-C が使う)。"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from domain.learning.learning_session import LearningSession
from domain.shared.ids import LearningSessionId, LectureId

TOTAL_ROUNDS = 3  # 回数は固定(Q11)


class ProgressState(StrEnum):
    WAITING = "waiting"  # n本目の選択待ち
    LEARNING = "learning"  # n本目の学習中
    FINISHED = "finished"  # 全体の終了


@dataclass(frozen=True)
class ParticipantProgress:
    """ログインした協力者の進行状態。

    round_number: 選択待ち・学習中の n(1〜3)。全体の終了では TOTAL_ROUNDS。
    current_*: 学習中の今の回(それ以外の状態では None / False)。
    current_has_records: 今の回の記録(視聴ログ・小テスト・対話セッション)が1件以上あるか。
    finished_lecture_ids: 終えた回の講義(回の順)。
    """

    state: ProgressState
    round_number: int
    current_lecture_id: LectureId | None = None
    current_learning_session_id: LearningSessionId | None = None
    current_has_records: bool = False
    finished_lecture_ids: tuple[LectureId, ...] = ()

    @property
    def can_reselect(self) -> bool:
        """今の回を選び直せるか(What 8節。学習中で、回の記録が1件もない)。"""
        return self.state is ProgressState.LEARNING and not self.current_has_records


def round_order(sessions: Iterable[LearningSession]) -> tuple[LearningSession, ...]:
    """「何本目」の定義: 学習セッションの開始時刻の昇順(同じなら ID の昇順)。先頭が1本目。

    仕様: docs/spec/multi-video-learning.md#制約関連機能(共有IF)
    """
    return tuple(sorted(sessions, key=lambda s: (s.started_at, str(s.id))))
