"""SQLite 数据层：建表 + FTS5 全文索引（方案 A：仅存文本数据）。"""
import sqlite3
from pathlib import Path

from . import config


def get_conn() -> sqlite3.Connection:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表（幂等）。chunks 入库时需同步写 chunks_fts，删除时同步删除。"""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS papers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        authors     TEXT DEFAULT '',
        abstract    TEXT DEFAULT '',
        source_note TEXT DEFAULT '',
        raw_text    TEXT NOT NULL,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS chunks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id    INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        content     TEXT NOT NULL,
        page        INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS highlights (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id        INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        type            TEXT NOT NULL,          -- term / key_point / conclusion
        content         TEXT NOT NULL,
        source_chunk_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS questions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id   INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        question   TEXT NOT NULL,
        answer     TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        content,
        content='chunks',
        content_rowid='id'
    );

    -- chunks 与 fts 同步触发器
    CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
    END;
    CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', old.id, old.content);
    END;
    """)
    conn.commit()
    conn.close()