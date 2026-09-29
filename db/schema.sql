-- 対話履歴用 SQLite スキーマ（ADR 準拠）
-- sessions: 1 対話セッション = 1 行
-- messages: 各発言（user / assistant）

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    participant_id TEXT NOT NULL DEFAULT '',
    learning_session_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    utterance_type TEXT,
    dialogue_move TEXT,
    interpretation_state TEXT,
    responded_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 履歴取得: session_id で絞り込み + created_at 昇順のため複合インデックス
CREATE INDEX IF NOT EXISTS idx_messages_session_created
    ON messages(session_id, created_at);

-- 対話ログ: 1 対話セッション = 最大 1 行（session_id 主キーで upsert）
-- 仕様: docs/spec/dialog-log-save.md#tutordb-の表
-- 注: responded_at を参照するインデックスはここに書かない（旧経路 db/init_db.py も本ファイルを実行するため）
CREATE TABLE IF NOT EXISTS dialog_logs (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id),
    participant_id TEXT NOT NULL,
    lecture_id TEXT NOT NULL,
    learning_session_id TEXT NOT NULL,
    end_method TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    log_json TEXT NOT NULL
);
