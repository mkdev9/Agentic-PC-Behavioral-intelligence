"""
desktop_agent.reasoning.summarizer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Compresses session history so the LLM context window is used efficiently.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Summarizer:
    """Generates a rolling textual summary from recent snapshots."""

    def __init__(self, max_lines: int = 30) -> None:
        self._max_lines = max_lines

    def summarize(self, snapshots: list[dict[str, Any]]) -> str:
        """Build a compact summary string from a list of snapshot dicts.

        Each snapshot is compressed into a single line.  If the total
        exceeds *max_lines*, older entries are dropped.
        """
        if not snapshots:
            return "No previous activity recorded."

        lines: list[str] = []
        for snap in snapshots:
            ts = snap.get("timestamp", "?")
            app = snap.get("app_name", "unknown")
            act = snap.get("activity_type", "")
            title = snap.get("window_title", "")
            insight_short = (snap.get("insight") or "")[:120]
            line = f"[{ts}] {app} ({act}) — {title}"
            if insight_short:
                line += f" | insight: {insight_short}"
            lines.append(line)

        # Keep only the most recent entries
        if len(lines) > self._max_lines:
            lines = lines[-self._max_lines :]

        summary = "\n".join(lines)
        logger.debug("Summary built — %d lines", len(lines))
        return summary

    def compress_insight(self, insight: str, max_length: int = 500) -> str:
        """Trim an insight to *max_length* for storage efficiency."""
        if len(insight) <= max_length:
            return insight
        return insight[:max_length] + " …"
