"""SQLite FTS5 knowledge base for local meeting indexing and retrieval."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from voxlocal.transcription.whisper_engine import TranscriptSegment


@dataclass
class SearchResult:
    """Represents a matched dialogue turn or note excerpt."""

    meeting_id: int
    title: str
    date: str
    speaker: str
    start_sec: float
    end_sec: float
    text: str
    vault_file: str
    is_bookmarked: bool


class KnowledgeDB:
    """Manages local SQLite database with Full-Text Search (FTS5)."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            base_dir = Path.home() / ".voxlocal"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "knowledge.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create database tables and FTS5 virtual indices."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    date TEXT NOT NULL,
                    duration TEXT,
                    preset TEXT,
                    participants TEXT,
                    vault_file TEXT,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER NOT NULL,
                    start_sec REAL NOT NULL,
                    end_sec REAL NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL,
                    is_bookmarked INTEGER DEFAULT 0,
                    FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                );
            """)

            # FTS5 full-text search table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_segments USING fts5(
                    speaker,
                    text,
                    content='segments',
                    content_rowid='id'
                );
            """)

            # Triggers to keep FTS index synchronized with segments table
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS segments_ai AFTER INSERT ON segments BEGIN
                    INSERT INTO fts_segments(rowid, speaker, text) VALUES (new.id, new.speaker, new.text);
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS segments_ad AFTER DELETE ON segments BEGIN
                    INSERT INTO fts_segments(fts_segments, rowid, speaker, text) VALUES('delete', old.id, old.speaker, old.text);
                END;
            """)
            conn.commit()

    def index_meeting(
        self,
        title: str,
        date: str,
        duration: str,
        preset: str,
        participants: list[str],
        vault_file: Path,
        summary: str,
        segments: list[TranscriptSegment],
    ) -> int:
        """Index a completed meeting session into SQLite and FTS5."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO meetings (title, date, duration, preset, participants, vault_file, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    date,
                    duration,
                    preset,
                    ", ".join(participants),
                    str(vault_file),
                    summary,
                ),
            )
            meeting_id = cursor.lastrowid

            segment_rows = [
                (
                    meeting_id,
                    seg.start,
                    seg.end,
                    seg.speaker,
                    seg.text,
                    1 if getattr(seg, "is_bookmarked", False) else 0,
                )
                for seg in segments
            ]

            cursor.executemany(
                """
                INSERT INTO segments (meeting_id, start_sec, end_sec, speaker, text, is_bookmarked)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                segment_rows,
            )
            conn.commit()
            return meeting_id

    def search(self, query: str, limit: int = 15) -> list[SearchResult]:
        """Search meeting transcripts using FTS5 full-text matching."""
        import re

        tokens = [w for w in re.findall(r"\w+", query) if len(w) > 1]
        if not tokens:
            return []

        if query.startswith('"') and query.endswith('"'):
            safe_query = query
        else:
            safe_query = " OR ".join(tokens)

        sql = """
            SELECT 
                s.meeting_id,
                m.title,
                m.date,
                s.speaker,
                s.start_sec,
                s.end_sec,
                s.text,
                m.vault_file,
                s.is_bookmarked
            FROM fts_segments f
            JOIN segments s ON f.rowid = s.id
            JOIN meetings m ON s.meeting_id = m.id
            WHERE fts_segments MATCH ?
            ORDER BY rank
            LIMIT ?
        """

        results: list[SearchResult] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                rows = cursor.execute(sql, (safe_query, limit)).fetchall()
            except sqlite3.OperationalError:
                # Fallback to standard LIKE if query syntax fails
                like_sql = """
                    SELECT 
                        s.meeting_id,
                        m.title,
                        m.date,
                        s.speaker,
                        s.start_sec,
                        s.end_sec,
                        s.text,
                        m.vault_file,
                        s.is_bookmarked
                    FROM segments s
                    JOIN meetings m ON s.meeting_id = m.id
                    WHERE s.text LIKE ?
                    LIMIT ?
                """
                rows = cursor.execute(like_sql, (f"%{query}%", limit)).fetchall()

            for r in rows:
                results.append(
                    SearchResult(
                        meeting_id=r["meeting_id"],
                        title=r["title"],
                        date=r["date"],
                        speaker=r["speaker"],
                        start_sec=r["start_sec"],
                        end_sec=r["end_sec"],
                        text=r["text"],
                        vault_file=r["vault_file"],
                        is_bookmarked=bool(r["is_bookmarked"]),
                    )
                )
        return results

    def list_all_meetings(self) -> list[dict]:
        """Retrieve all recorded meetings with summary information."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT id, title, date, duration, preset, participants, vault_file FROM meetings ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]
