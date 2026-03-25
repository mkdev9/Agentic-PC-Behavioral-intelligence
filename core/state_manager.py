"""
desktop_agent.core.state_manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SQLite-backed session memory.

Stores every observation snapshot and the generated insight so that
the reasoning layer can access recent history for context-aware analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiosqlite

from utils.helpers import utc_now_iso

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT    NOT NULL,
    app_name      TEXT,
    window_title  TEXT,
    activity_type TEXT,
    ocr_text_hash TEXT,
    ocr_text      TEXT,
    image_hash    TEXT,
    insight       TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(timestamp);
"""


class StateManager:
    """Async wrapper around a SQLite database for session persistence."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection | None = None

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Open the database and ensure the schema exists."""
        self._conn = await aiosqlite.connect(str(self._db_path))
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()
        logger.info("StateManager initialised — %s", self._db_path)

    async def close(self) -> None:
        """Flush and close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("StateManager closed.")

    # ── Write ───────────────────────────────────────────────────────────

    async def save_snapshot(
        self,
        *,
        app_name: str = "",
        window_title: str = "",
        activity_type: str = "",
        ocr_text_hash: str = "",
        ocr_text: str = "",
        image_hash: str = "",
        insight: str = "",
    ) -> int:
        """Persist a single observation snapshot. Returns the row id."""
        assert self._conn is not None, "StateManager not initialised"
        cursor = await self._conn.execute(
            """
            INSERT INTO snapshots
                (timestamp, app_name, window_title, activity_type,
                 ocr_text_hash, ocr_text, image_hash, insight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                app_name,
                window_title,
                activity_type,
                ocr_text_hash,
                ocr_text,
                image_hash,
                insight,
            ),
        )
        await self._conn.commit()
        row_id = cursor.lastrowid or 0
        logger.debug("Snapshot saved — id=%d, app=%s", row_id, app_name)
        return row_id

    # ── Read ────────────────────────────────────────────────────────────

    async def get_recent_snapshots(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return the *limit* most recent snapshots as dicts."""
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def get_session_summary(self, limit: int = 20) -> str:
        """Build a condensed textual summary of recent activity."""
        snapshots = await self.get_recent_snapshots(limit)
        if not snapshots:
            return "No previous activity recorded."

        lines: list[str] = []
        for snap in reversed(snapshots):
            ts = snap.get("timestamp", "?")
            app = snap.get("app_name", "unknown")
            act = snap.get("activity_type", "")
            title = snap.get("window_title", "")
            lines.append(f"[{ts}] {app} ({act}) — {title}")
        return "\n".join(lines)
