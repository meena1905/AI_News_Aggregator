import sqlite3
import os
from pathlib import Path
DB_FILE = "articles.db"
def init_sqlite_db():
    """Create SQLite database with the same schema as Supabase."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        interests TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        source TEXT NOT NULL,
        summary TEXT,
        key_points TEXT DEFAULT '[]',
        sentiment TEXT,
        category TEXT,
        relevance_score REAL,
        published_at TIMESTAMP,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(url)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS digests (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        article_ids TEXT DEFAULT '[]',
        email_status TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, name, email, interests)
    VALUES ('00000000-0000-0000-0000-000000000001', 'Test User', 'test@example.com', '["AI", "Tech"]')
    """)
    conn.commit()
    conn.close()
    print(f"✅ SQLite database initialized at: {os.path.abspath(DB_FILE)}")
if __name__ == "__main__":
    init_sqlite_db()
