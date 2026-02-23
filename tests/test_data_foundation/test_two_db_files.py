"""
Phase 1 Step 1.1: 対話用 DB と学習データ用 DB のファイルを分ける

- 対話用: db/data/tutor.db
- 学習データ用: db/data/learning.db（別ファイル）
- 学習データ用スキーマファイルが存在すること（db/schema_learning.sql 等）
"""
from pathlib import Path

import pytest


class TestStep1_1TwoDbPaths:
    """対話用と学習用でデフォルトパスが別であること。"""

    def test_default_tutor_db_path_is_under_db_data(
        self, default_tutor_db_path: Path, project_root: Path
    ) -> None:
        """デフォルトの対話用 DB は db/data/tutor.db である。"""
        assert default_tutor_db_path == project_root / "db" / "data" / "tutor.db"
        assert "tutor" in default_tutor_db_path.name

    def test_default_learning_db_path_is_under_db_data(
        self, default_learning_db_path: Path, project_root: Path
    ) -> None:
        """デフォルトの学習データ用 DB は db/data/learning.db である。"""
        assert default_learning_db_path == project_root / "db" / "data" / "learning.db"
        assert "learning" in default_learning_db_path.name.lower()

    def test_tutor_and_learning_paths_are_different(
        self, default_tutor_db_path: Path, default_learning_db_path: Path
    ) -> None:
        """対話用と学習用のデフォルトパスは異なる（2DB 分離）。"""
        assert default_tutor_db_path != default_learning_db_path


class TestStep1_1LearningSchemaFile:
    """学習データ用スキーマを定義するファイルが存在すること。"""

    def test_learning_schema_file_exists(self, learning_schema_path: Path) -> None:
        """学習データ用スキーマファイル（例: db/schema_learning.sql）が存在する。"""
        assert learning_schema_path.exists(), (
            "学習データ用スキーマファイルが存在すること "
            "（例: db/schema_learning.sql）"
        )
        assert learning_schema_path.is_file()
        assert learning_schema_path.suffix == ".sql"
