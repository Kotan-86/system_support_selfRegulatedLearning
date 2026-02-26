"""
視聴ログを viewing_logs テーブルから TSV に出力する。
current_time は SQLite 予約語のため SELECT で "current_time" と引用する。
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db.config import get_learning_db_path

def main() -> None:
    path = get_learning_db_path()
    if not path.exists():
        print("learning.db がありません。", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(path))
    # current_time は SQLite の予約語なので二重引用符でカラムを指定する
    cur = conn.execute(
        '''SELECT id, participant_id, time_stamp, "current_time", action, duration
           FROM viewing_logs ORDER BY time_stamp ASC'''
    )
    rows = cur.fetchall()
    conn.close()
    out_path = Path(__file__).resolve().parent.parent / "viewing_logs.tsv"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("id\tparticipant_id\ttime_stamp\tcurrent_time\taction\tduration\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    print(f"{out_path} に {len(rows)} 件書き出しました。")


if __name__ == "__main__":
    main()
