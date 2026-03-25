"""
desktop_agent.perception.ocr_engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Text extraction from screen captures via Tesseract OCR.

Gracefully degrades if Tesseract is not installed — logs a warning
and returns empty text so the rest of the agent pipeline still works.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

# Attempt to import pytesseract; it may fail at call-time if the
# Tesseract binary is not installed.
try:
    import pytesseract

    _HAS_PYTESSERACT = True
except ImportError:
    _HAS_PYTESSERACT = False


def _tesseract_available() -> bool:
    """Check whether the Tesseract binary is reachable."""
    if not _HAS_PYTESSERACT:
        return False
    # pytesseract looks for 'tesseract' on PATH or at its configured cmd
    cmd = getattr(pytesseract, "tesseract_cmd", "tesseract")
    return shutil.which(cmd) is not None


class OCREngine:
    """Extracts readable text from PIL images using pytesseract."""

    def __init__(self, config: dict[str, Any]) -> None:
        ocr_cfg = config.get("ocr", {})
        self._lang: str = ocr_cfg.get("lang", "eng")
        self._available = _tesseract_available()

        if not self._available:
            logger.warning(
                "Tesseract OCR is NOT installed or not on PATH. "
                "OCR will be skipped — the agent will still run but "
                "insights will rely only on window/app metadata. "
                "Install Tesseract from: "
                "https://github.com/UB-Mannheim/tesseract/wiki"
            )

    async def extract_text(self, image: Image.Image) -> str:
        """Run OCR on *image* in a thread and return cleaned text."""
        if not self._available:
            return ""

        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(None, self._run_ocr, image)
        cleaned = self._clean(raw)
        logger.debug(
            "OCR extracted %d chars (cleaned from %d)",
            len(cleaned),
            len(raw),
        )
        return cleaned

    def _run_ocr(self, image: Image.Image) -> str:
        """Blocking Tesseract call."""
        try:
            return pytesseract.image_to_string(image, lang=self._lang)
        except Exception as exc:
            logger.error("Tesseract error: %s", exc)
            return ""

    @staticmethod
    def _clean(text: str) -> str:
        """Remove excessive whitespace and control characters."""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[^\S\n]+", " ", text)
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines).strip()
        return text
