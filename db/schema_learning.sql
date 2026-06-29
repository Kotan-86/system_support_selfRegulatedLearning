-- 学習データ用 SQLite スキーマ（framework-drivers-persistence.md 確定版）
-- learning_sessions: 学習セッション（集約ルート）1 件 = 1 行
-- viewing_logs: 視聴イベント 1 件 = 1 行
-- quiz_attempts: 小テスト 1 回の受験 = 1 行
-- quiz_attempt_answers: 1 問 = 1 行（is_correct は INTEGER 0/1）
-- 仕様: docs/spec/framework-drivers-persistence.md

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS learning_sessions (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    lecture_id TEXT NOT NULL,
    started_at DATETIME NOT NULL,
    UNIQUE (learner_id, lecture_id)
);

CREATE TABLE IF NOT EXISTS viewing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learning_session_id TEXT NOT NULL,
    time_stamp DATETIME NOT NULL,
    "current_time" INTEGER NOT NULL,
    action TEXT NOT NULL,
    duration REAL NOT NULL,
    FOREIGN KEY (learning_session_id) REFERENCES learning_sessions(id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learning_session_id TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    score_numerator INTEGER NOT NULL,
    score_denominator INTEGER NOT NULL,
    FOREIGN KEY (learning_session_id) REFERENCES learning_sessions(id)
);

CREATE TABLE IF NOT EXISTS quiz_attempt_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    question_index INTEGER NOT NULL,
    selected_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(id)
);

CREATE INDEX IF NOT EXISTS idx_viewing_logs_session
    ON viewing_logs(learning_session_id);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_session
    ON quiz_attempts(learning_session_id);
