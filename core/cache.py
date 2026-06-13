import sqlite3
import hashlib
from pathlib import Path

class LocalAICache:
    def __init__(self, db_path=None):
        if db_path is None:
            project_dir = Path(__file__).resolve().parent.parent
            cache_dir = project_dir / ".cache"
            cache_dir.mkdir(exist_ok=True)
            self.db_path = cache_dir / "taiga_cache.db"
        else:
            self.db_path = Path(db_path)

        self._init_db()

    def _conn(self):
        """Returns a connection with WAL mode and busy timeout for concurrent access."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        try:
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS prompt_cache (
                        hash TEXT PRIMARY KEY,
                        model TEXT,
                        prompt TEXT,
                        response TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        messages TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception:
            pass

    def _get_hash(self, model, prompt):
        hasher = hashlib.sha256()
        hasher.update(model.encode("utf-8"))
        hasher.update(prompt.encode("utf-8"))
        return hasher.hexdigest()

    def get(self, model, prompt):
        query_hash = self._get_hash(model, prompt)
        try:
            with self._conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT response FROM prompt_cache WHERE hash = ?",
                    (query_hash,)
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass
        return None

    def set(self, model, prompt, response):
        query_hash = self._get_hash(model, prompt)
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO prompt_cache (hash, model, prompt, response)
                    VALUES (?, ?, ?, ?)
                    """,
                    (query_hash, model, prompt, response)
                )
                conn.execute(
                    """
                    DELETE FROM prompt_cache WHERE rowid NOT IN (
                        SELECT rowid FROM prompt_cache ORDER BY rowid DESC LIMIT 200
                    )
                    """
                )
                conn.commit()
        except Exception:
            pass
