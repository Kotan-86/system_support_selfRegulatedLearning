# 仕様: docs/spec/lecture-selection.md#受入基準 AC16(固定対応の廃止)
"""participant_id による講義の固定対応(1/2/3 → lecture-1/2/3、それ以外は lecture-1)の廃止。

旧: participant_id → lecture_id の固定マップと解決の優先順位を検証していた(FR-05)。
講義の選択(FR-60、#34)で置き換わったので、参加者の講義を participant_id から決める口は残らない。
モジュール自体を消すか、固定マップを持たないかのどちらでもよい。
"""
from __future__ import annotations

import importlib
import importlib.util

MODULE = "interfaces.common.learner_lecture_mapping"


def test_ac16_participant_to_lecture_fixed_map_is_gone() -> None:
    if importlib.util.find_spec(MODULE) is None:
        return  # モジュールごと廃止された
    module = importlib.import_module(MODULE)
    assert not hasattr(module, "NEAR_TERM_PARTICIPANT_LECTURE_MAP"), (
        "participant_id → lecture_id の固定マップが残っている"
    )
