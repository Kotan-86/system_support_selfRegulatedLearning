"""
LLM チューター用 Flask アプリ（thin re-export）。

実装は framework_drivers/platform/ へ移行済み。
起動例: uv run flask --app framework_drivers.platform.main run
移行期間: uv run flask --app app.main run
"""
from framework_drivers.platform.main import app, create_app

__all__ = ["app", "create_app"]
