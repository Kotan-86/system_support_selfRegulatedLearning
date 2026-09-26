# 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#修正方針
# 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準再発防止回帰テスト
"""LAD 応答用の全区間補完(services の純関数)の単体テスト。

対応 AC: AC1, AC2, AC3, AC4, AC6, AC7(区間の範囲と並び)、AC5(件数を捨てない)。
実装モジュールは、未作成でも個々のテストが失敗として報告されるよう、テスト内で import する。
"""
from __future__ import annotations

import importlib

import pytest

from domain.learning.viewing_event import ViewingAction
from interfaces.learning.services.viewing_behavior_metrics import VideoSegmentMetrics
from interfaces.learning.view_models.lad_dashboard import VideoSegmentViewModel

ALL_ACTION_KEYS = {action.value for action in ViewingAction}


def _series():
    return importlib.import_module("interfaces.learning.services.video_segment_series")


def _sparse(start: int, **counts: int) -> VideoSegmentMetrics:
    action_counts = {key: 0 for key in ALL_ACTION_KEYS}
    action_counts.update(counts)
    return VideoSegmentMetrics(segment_start_sec=start, action_counts=action_counts)


def _starts(segments) -> list[int]:
    return [segment.segment_start_sec for segment in segments]


def _total(segments) -> int:
    return sum(sum(segment.action_counts.values()) for segment in segments)


class TestLastSegmentStartSec:
    """最後の区間開始 = max(480, ceil(動画長/120)*120-120, 最後の操作を含む区間の開始秒)。"""

    @pytest.mark.parametrize(
        ("duration", "max_start", "expected"),
        [
            # 操作 0 件(境界の例の表)。AC6, AC7, AC4, AC1
            (300, None, 480),
            (600, None, 480),
            (601, None, 600),
            (720, None, 600),
            (721, None, 720),
            (818, None, 720),
            (840, None, 720),
            (841, None, 840),
            # 操作が動画長以内: 式の第 3 項が小さいので変わらない
            (600, 0, 480),
            (818, 720, 720),
            # 動画長ちょうど・動画長超の操作は、その区間まで延ばす。AC3, AC4
            (720, 720, 720),
            (818, 840, 840),
            (300, 600, 600),
        ],
    )
    def test_returns_max_of_three_terms(
        self, duration: int, max_start: int | None, expected: int
    ) -> None:
        result = _series().last_segment_start_sec(
            video_duration_sec=duration, max_segment_start_sec=max_start
        )

        assert result == expected

    @pytest.mark.parametrize("duration", [0, -1])
    def test_non_positive_duration_raises_value_error(self, duration: int) -> None:
        with pytest.raises(ValueError):
            _series().last_segment_start_sec(
                video_duration_sec=duration, max_segment_start_sec=None
            )


class TestBuildDenseVideoSegments:
    """疎な区間を 0 秒からの欠けのない全区間に補完する。"""

    def test_ac1_ac2_duration_818_with_600_and_720_segments(self) -> None:
        sparse = (_sparse(600, pause=1), _sparse(720, play=1))

        dense = _series().build_dense_video_segments(sparse, video_duration_sec=818)

        assert _starts(dense) == [0, 120, 240, 360, 480, 600, 720]
        by_start = {segment.segment_start_sec: segment for segment in dense}
        assert by_start[600].action_counts["pause"] == 1
        assert by_start[720].action_counts["play"] == 1
        for start in (0, 120, 240, 360, 480):
            assert by_start[start].action_counts == {key: 0 for key in ALL_ACTION_KEYS}
        assert _total(dense) == 2

    def test_ac3_position_beyond_duration_extends_to_840(self) -> None:
        sparse = (_sparse(840, play=1),)

        dense = _series().build_dense_video_segments(sparse, video_duration_sec=818)

        assert _starts(dense) == [0, 120, 240, 360, 480, 600, 720, 840]
        assert dense[-1].action_counts["play"] == 1
        assert _total(dense) == 1

    def test_ac4_duration_720_with_operation_at_720(self) -> None:
        dense = _series().build_dense_video_segments(
            (_sparse(720, play=1),), video_duration_sec=720
        )

        assert _starts(dense) == [0, 120, 240, 360, 480, 600, 720]
        assert dense[-1].action_counts["play"] == 1

    def test_ac4_duration_720_without_operations_has_six_segments(self) -> None:
        dense = _series().build_dense_video_segments((), video_duration_sec=720)

        assert _starts(dense) == [0, 120, 240, 360, 480, 600]

    def test_ac4_duration_601_without_operations_has_six_segments(self) -> None:
        dense = _series().build_dense_video_segments((), video_duration_sec=601)

        assert _starts(dense) == [0, 120, 240, 360, 480, 600]

    @pytest.mark.parametrize("duration", [600, 300])
    def test_ac6_short_video_keeps_five_segments(self, duration: int) -> None:
        dense = _series().build_dense_video_segments(
            (_sparse(120, play=1),), video_duration_sec=duration
        )

        assert _starts(dense) == [0, 120, 240, 360, 480]
        assert dense[1].action_counts["play"] == 1
        assert _total(dense) == 1

    def test_ac7_no_operations_returns_all_zero_segments(self) -> None:
        for duration, expected_count in ((600, 5), (818, 7)):
            dense = _series().build_dense_video_segments(
                (), video_duration_sec=duration
            )

            assert len(dense) == expected_count
            assert _starts(dense) == [120 * i for i in range(expected_count)]
            assert all(
                segment.action_counts == {key: 0 for key in ALL_ACTION_KEYS}
                for segment in dense
            )

    def test_returns_view_model_type_with_all_action_keys(self) -> None:
        dense = _series().build_dense_video_segments(
            (_sparse(120, play=2),), video_duration_sec=600
        )

        assert all(isinstance(segment, VideoSegmentViewModel) for segment in dense)
        assert all(set(segment.action_counts) == ALL_ACTION_KEYS for segment in dense)
        assert dense[1].action_counts["play"] == 2

    def test_ac5_copies_counts_without_changing_values(self) -> None:
        sparse = (
            _sparse(0, play=3, pause=1),
            _sparse(600, backward_skip=2, forward_seek=4),
            _sparse(960, pause=5),
        )

        dense = _series().build_dense_video_segments(sparse, video_duration_sec=818)

        assert _starts(dense) == [120 * i for i in range(9)]
        assert _total(dense) == sum(sum(s.action_counts.values()) for s in sparse)
        by_start = {segment.segment_start_sec: segment for segment in dense}
        for original in sparse:
            assert by_start[original.segment_start_sec].action_counts == original.action_counts

    def test_does_not_mutate_input(self) -> None:
        sparse = (_sparse(600, pause=1),)
        snapshot = (sparse[0].segment_start_sec, dict(sparse[0].action_counts))

        _series().build_dense_video_segments(sparse, video_duration_sec=818)

        assert len(sparse) == 1
        assert (sparse[0].segment_start_sec, dict(sparse[0].action_counts)) == snapshot
