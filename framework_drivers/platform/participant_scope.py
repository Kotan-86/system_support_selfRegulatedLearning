# 仕様: docs/spec/participant-login.md#3-参加者の特定fr-52
"""クライアントが送る participant_id の照合(ログインした本人との一致確認)。"""
from __future__ import annotations


def resolve_claimed_participant_id(claimed: object, logged_in_id: str) -> int | None:
    """送られた participant_id を、ログインした ID と照合する。

    戻り値: None=処理してよい(未送信・None・空文字・一致。数値は10進の文字列にして比較)
    / 403=不一致 / 400=真偽値・配列・オブジェクト・その他の型。
    空白のみの文字列は「空文字」ではないので比較し、不一致として 403 にする(保守的な扱い)。
    """
    if claimed is None or claimed == "":
        return None
    if isinstance(claimed, bool):
        return 400
    if isinstance(claimed, (str, int, float)):
        return None if str(claimed) == logged_in_id else 403
    return 400
