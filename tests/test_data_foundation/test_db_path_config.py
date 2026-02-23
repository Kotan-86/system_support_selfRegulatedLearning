"""
Phase 1 Step 1.4: DB パスを環境変数で切り替え可能にする

TUTOR_DB_PATH / LEARNING_DB_PATH が未設定時はデフォルトパスを返し、
設定時はその値が使われることを検証する。
"""
import os
from pathlib import Path

import pytest


class TestStep1_4DbPathConfigModule:
    """DB パス取得用のモジュールまたは関数が存在すること。"""

    def test_can_import_db_path_config(self) -> None:
        """DB パス取得処理を import できる（例: db.config や db.paths）。"""
        try:
            from db import config
        except ImportError:
            try:
                from db import paths
            except ImportError:
                pytest.skip("db.config または db.paths が未実装のためスキップ")

    def test_get_tutor_db_path_exists(self) -> None:
        """対話用 DB パスを返す関数が存在する。"""
        try:
            from db import config as db_config

            get_tutor = getattr(db_config, "get_tutor_db_path", None)
        except ImportError:
            try:
                from db import paths as db_paths
                get_tutor = getattr(db_paths, "get_tutor_db_path", None)
            except ImportError:
                pytest.skip("db のパス取得が未実装のためスキップ")
        assert get_tutor is not None and callable(get_tutor), (
            "get_tutor_db_path() が存在すること"
        )

    def test_get_learning_db_path_exists(self) -> None:
        """学習データ用 DB パスを返す関数が存在する。"""
        try:
            from db import config as db_config
            get_learning = getattr(db_config, "get_learning_db_path", None)
        except ImportError:
            try:
                from db import paths as db_paths
                get_learning = getattr(db_paths, "get_learning_db_path", None)
            except ImportError:
                pytest.skip("db のパス取得が未実装のためスキップ")
        assert get_learning is not None and callable(get_learning), (
            "get_learning_db_path() が存在すること"
        )


class TestStep1_4DefaultPathsWhenEnvUnset:
    """環境変数未設定時はデフォルトパスを返すこと。"""

    def test_get_tutor_db_path_returns_default_when_env_unset(
        self, env_tutor_db_path, env_learning_db_path, default_tutor_db_path: Path
    ) -> None:
        """TUTOR_DB_PATH 未設定時、get_tutor_db_path() は db/data/tutor.db を返す。"""
        env_tutor_db_path.delenv("TUTOR_DB_PATH", raising=False)
        env_learning_db_path.delenv("LEARNING_DB_PATH", raising=False)
        try:
            from db.config import get_tutor_db_path
        except ImportError:
            try:
                from db.paths import get_tutor_db_path
            except ImportError:
                pytest.skip("get_tutor_db_path が未実装のためスキップ")
        result = get_tutor_db_path()
        assert result is not None
        path = Path(result) if isinstance(result, str) else result
        assert path == default_tutor_db_path, (
            "TUTOR_DB_PATH 未設定時は db/data/tutor.db を返すこと"
        )

    def test_get_learning_db_path_returns_default_when_env_unset(
        self, env_tutor_db_path, env_learning_db_path, default_learning_db_path: Path
    ) -> None:
        """LEARNING_DB_PATH 未設定時、get_learning_db_path() は db/data/learning.db を返す。"""
        env_tutor_db_path.delenv("TUTOR_DB_PATH", raising=False)
        env_learning_db_path.delenv("LEARNING_DB_PATH", raising=False)
        try:
            from db.config import get_learning_db_path
        except ImportError:
            try:
                from db.paths import get_learning_db_path
            except ImportError:
                pytest.skip("get_learning_db_path が未実装のためスキップ")
        result = get_learning_db_path()
        assert result is not None
        path = Path(result) if isinstance(result, str) else result
        assert path == default_learning_db_path, (
            "LEARNING_DB_PATH 未設定時は db/data/learning.db を返すこと"
        )


class TestStep1_4PathsRespectEnvWhenSet:
    """環境変数設定時はその値が使われること。"""

    def test_get_tutor_db_path_uses_tutor_db_path_env(
        self, env_tutor_db_path, env_learning_db_path, tmp_path: Path
    ) -> None:
        """TUTOR_DB_PATH 設定時、get_tutor_db_path() はそのパスを返す。"""
        custom = tmp_path / "custom_tutor.db"
        env_tutor_db_path.setenv("TUTOR_DB_PATH", str(custom))
        env_learning_db_path.delenv("LEARNING_DB_PATH", raising=False)
        try:
            from db.config import get_tutor_db_path
        except ImportError:
            try:
                from db.paths import get_tutor_db_path
            except ImportError:
                pytest.skip("get_tutor_db_path が未実装のためスキップ")
        result = get_tutor_db_path()
        path = Path(result) if isinstance(result, str) else result
        assert path == custom, "TUTOR_DB_PATH が設定されているときその値を使うこと"

    def test_get_learning_db_path_uses_learning_db_path_env(
        self, env_tutor_db_path, env_learning_db_path, tmp_path: Path
    ) -> None:
        """LEARNING_DB_PATH 設定時、get_learning_db_path() はそのパスを返す。"""
        env_tutor_db_path.delenv("TUTOR_DB_PATH", raising=False)
        custom = tmp_path / "custom_learning.db"
        env_learning_db_path.setenv("LEARNING_DB_PATH", str(custom))
        try:
            from db.config import get_learning_db_path
        except ImportError:
            try:
                from db.paths import get_learning_db_path
            except ImportError:
                pytest.skip("get_learning_db_path が未実装のためスキップ")
        result = get_learning_db_path()
        path = Path(result) if isinstance(result, str) else result
        assert path == custom, "LEARNING_DB_PATH が設定されているときその値を使うこと"
