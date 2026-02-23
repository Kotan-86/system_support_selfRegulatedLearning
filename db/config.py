"""
DB パス設定（ADR 準拠）

TUTOR_DB_PATH / LEARNING_DB_PATH で上書き可能。
未設定時は db/data/tutor.db と db/data/learning.db をデフォルトとする。
"""
import os
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parent
_DEFAULT_TUTOR = _DB_DIR / "data" / "tutor.db"
_DEFAULT_LEARNING = _DB_DIR / "data" / "learning.db"


def get_tutor_db_path() -> Path:
    """対話用 DB のパス。TUTOR_DB_PATH が設定されていればその値、なければ db/data/tutor.db。"""
    path = os.environ.get("TUTOR_DB_PATH")
    return Path(path) if path else _DEFAULT_TUTOR


def get_learning_db_path() -> Path:
    """学習データ用 DB のパス。LEARNING_DB_PATH が設定されていればその値、なければ db/data/learning.db。"""
    path = os.environ.get("LEARNING_DB_PATH")
    return Path(path) if path else _DEFAULT_LEARNING
