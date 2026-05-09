import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".config" / "tool-audio" / "jobs.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db() -> None:
    now = datetime.now().isoformat()
    with _connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path  TEXT NOT NULL,
                file_hash  TEXT NOT NULL UNIQUE,
                status     TEXT NOT NULL DEFAULT 'processing',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error      TEXT
            )
        """)
        # Reset jobs stuck in 'processing' from a previous crashed run
        con.execute(
            "UPDATE jobs SET status='error', error='interrupted', updated_at=? WHERE status='processing'",
            (now,),
        )


def file_hash(path: Path) -> str:
    """SHA-256 of first 64 KB — fast dedup without reading the whole file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(65536))
    return h.hexdigest()


def is_processed(hash: str) -> bool:
    """True if file has been successfully processed or is currently in progress."""
    with _connect() as con:
        row = con.execute(
            "SELECT status FROM jobs WHERE file_hash = ?", (hash,)
        ).fetchone()
    return row is not None and row[0] in ("done", "processing")


def add_job(file_path: Path, hash: str) -> None:
    """Insert a new job record with status=processing, or re-queue an existing error."""
    now = datetime.now().isoformat()
    with _connect() as con:
        con.execute(
            "INSERT INTO jobs (file_path, file_hash, status, created_at, updated_at)"
            " VALUES (?, ?, 'processing', ?, ?)"
            " ON CONFLICT(file_hash) DO UPDATE SET"
            "   file_path=excluded.file_path,"
            "   status='processing',"
            "   updated_at=excluded.updated_at,"
            "   error=NULL"
            " WHERE status='error'",
            (str(file_path), hash, now, now),
        )


def mark_done(hash: str) -> None:
    now = datetime.now().isoformat()
    with _connect() as con:
        con.execute(
            "UPDATE jobs SET status='done', updated_at=? WHERE file_hash=?",
            (now, hash),
        )


def mark_error(hash: str, error: str) -> None:
    now = datetime.now().isoformat()
    with _connect() as con:
        con.execute(
            "UPDATE jobs SET status='error', error=?, updated_at=? WHERE file_hash=?",
            (error, now, hash),
        )
