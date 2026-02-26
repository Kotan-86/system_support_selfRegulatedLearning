-- 学習データ用 SQLite スキーマ（ADR 準拠）
-- viewing_logs: 視聴イベント 1 件 = 1 行
-- quiz_attempts: 小テスト 1 回の受験 = 1 行
-- quiz_attempt_answers: 1 問 = 1 行（is_correct は INTEGER 0/1）

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS viewing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id TEXT NOT NULL,
    time_stamp DATETIME NOT NULL,
    "current_time" INTEGER NOT NULL,
    action TEXT NOT NULL,
    duration REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    score_numerator INTEGER NOT NULL,
    score_denominator INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_attempt_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    question_index INTEGER NOT NULL,
    selected_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(id)
);
