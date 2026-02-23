"""
Step 2: DB ファイルの配置とパス方針

db/data/ が存在すること、.gitignore に db/data の DB ファイルを無視する
エントリがあることを検証する。
"""
from pathlib import Path

import pytest


class TestStep2DbDataDirectory:
    """db/data/ ディレクトリが存在する。"""

    def test_db_data_directory_exists(self, db_data_dir: Path) -> None:
        assert db_data_dir.exists(), "db/data/ が存在すること"
        assert db_data_dir.is_dir()


class TestStep2Gitignore:
    """.gitignore に db/data の DB ファイルを無視するエントリがある。"""

    def test_gitignore_exists(self, gitignore_path: Path) -> None:
        assert gitignore_path.exists(), ".gitignore が存在すること"

    def test_gitignore_ignores_db_data_files(self, gitignore_path: Path) -> None:
        content = gitignore_path.read_text(encoding="utf-8")
        # db/data/*.db または db/data/tutor.db に相当する行があること
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        ignored = [
            line
            for line in lines
            if not line.startswith("#")
            and ("db" in line and ("data" in line or ".db" in line))
        ]
        assert len(ignored) >= 1, (
            ".gitignore に db/data の .db ファイルを無視するエントリがあること "
            "(例: db/data/*.db または db/data/tutor.db)"
        )
