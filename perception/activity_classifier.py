"""
desktop_agent.perception.activity_classifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Rule-based classifier that maps process names and OCR keywords to
human-readable activity categories.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Category Definitions ────────────────────────────────────────────────────

_APP_CATEGORIES: dict[str, str] = {
    # Browsers
    "chrome": "browsing",
    "firefox": "browsing",
    "msedge": "browsing",
    "opera": "browsing",
    "brave": "browsing",
    "vivaldi": "browsing",
    # Coding
    "code": "coding",
    "pycharm": "coding",
    "idea": "coding",
    "webstorm": "coding",
    "notepad++": "coding",
    "sublime_text": "coding",
    "devenv": "coding",
    "vim": "coding",
    "nvim": "coding",
    "cursor": "coding",
    "windsurf": "coding",
    # Communication
    "teams": "communication",
    "slack": "communication",
    "discord": "communication",
    "zoom": "communication",
    "outlook": "communication",
    "thunderbird": "communication",
    "telegram": "communication",
    "whatsapp": "communication",
    # Documents / Office
    "winword": "document_editing",
    "excel": "document_editing",
    "powerpnt": "document_editing",
    "libreoffice": "document_editing",
    "notion": "document_editing",
    "obsidian": "note_taking",
    # Media
    "vlc": "media",
    "spotify": "media",
    "mpv": "media",
    "foobar2000": "media",
    # File management
    "explorer": "file_management",
    "totalcmd": "file_management",
    # Terminal
    "windowsterminal": "terminal",
    "cmd": "terminal",
    "powershell": "terminal",
    "wt": "terminal",
    "mintty": "terminal",
    "alacritty": "terminal",
    "wezterm": "terminal",
}

# OCR keyword → activity hint
_OCR_KEYWORDS: dict[str, str] = {
    r"\bgithub\.com\b": "browsing:github",
    r"\bstack\s?overflow\b": "browsing:stackoverflow",
    r"\byoutube\.com\b": "media:youtube",
    r"\bgmail\b": "communication:email",
    r"\bchatgpt\b": "browsing:ai_chat",
    r"\bgemini\b": "browsing:ai_chat",
    r"\bjupyter\b": "coding:notebook",
    r"\bdef\s+\w+\s*\(": "coding:python",
    r"\bfunction\s+\w+\s*\(": "coding:javascript",
    r"\bSELECT\b.*\bFROM\b": "coding:sql",
}


@dataclass
class ActivityInfo:
    """Structured activity classification result."""
    category: str = "unknown"
    subcategory: str = ""
    confidence: float = 0.0

    @property
    def label(self) -> str:
        if self.subcategory:
            return f"{self.category}:{self.subcategory}"
        return self.category


class ActivityClassifier:
    """Rule-based activity type classifier."""

    def classify(
        self,
        app_name: str,
        window_title: str,
        ocr_text: str,
    ) -> ActivityInfo:
        """Return an :class:`ActivityInfo` based on app name and OCR text."""
        info = ActivityInfo()

        # 1) Match by app name
        app_lower = app_name.lower().replace(".exe", "")
        if app_lower in _APP_CATEGORIES:
            info.category = _APP_CATEGORIES[app_lower]
            info.confidence = 0.9

        # 2) Refine with OCR keyword scan
        combined = f"{window_title}\n{ocr_text}"
        for pattern, label in _OCR_KEYWORDS.items():
            if re.search(pattern, combined, re.IGNORECASE):
                parts = label.split(":", 1)
                if len(parts) == 2:
                    # Only override category if we had no match yet
                    if info.category == "unknown":
                        info.category = parts[0]
                    info.subcategory = parts[1]
                    info.confidence = max(info.confidence, 0.7)
                break

        # 3) Fallback from window title
        if info.category == "unknown" and window_title:
            info.category = "other"
            info.confidence = 0.3

        logger.debug(
            "Classified activity: %s (conf=%.1f) for app=%s",
            info.label,
            info.confidence,
            app_name,
        )
        return info
