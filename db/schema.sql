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
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 履歴取得: session_id で絞り込み + created_at 昇順のため複合インデックス
CREATE INDEX IF NOT EXISTS idx_messages_session_created
    ON messages(session_id, created_at);
