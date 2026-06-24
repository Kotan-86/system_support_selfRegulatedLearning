# 仕様: docs/spec/interfaces-layer.md#LastUpdatedViewModel
"""GetLearningSnapshot の結果から最終更新時刻 ViewModel を生成する。"""
from __future__ import annotations

from application.learning.dto.get_learning_snapshot import GetLearningSnapshotResponse

from interfaces.learning.view_models.last_updated import LastUpdatedViewModel


class LastUpdatedPresenter:
    """content_updated_at のみを LastUpdatedViewModel へ抽出する。"""

    def present(self, response: GetLearningSnapshotResponse) -> LastUpdatedViewModel:
        return LastUpdatedViewModel(last_updated=response.content_updated_at)
