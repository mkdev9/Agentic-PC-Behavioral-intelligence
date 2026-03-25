"""
desktop_agent.utils.throttling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Gate mechanism that prevents redundant LLM calls by enforcing both a
minimum time interval *and* a meaningful‐change threshold.
"""

from __future__ import annotations

import logging
import time

from utils.helpers import hamming_distance, text_similarity

logger = logging.getLogger(__name__)


class Throttler:
    """Decides whether the reasoning step should fire.

    Two independent checks are applied — *both* must pass:

    1. **Time gate** – at least ``min_interval`` seconds since the last
       approved call.
    2. **Change gate** – the perceptual hash distance between the current
       and previous frame exceeds ``change_threshold`` *or* OCR text
       similarity is below ``text_similarity_skip``.
    """

    def __init__(
        self,
        min_interval: float = 30.0,
        change_threshold: int = 5,
        text_similarity_skip: float = 0.95,
    ) -> None:
        self.min_interval = min_interval
        self.change_threshold = change_threshold
        self.text_similarity_skip = text_similarity_skip

        self._last_approved_time: float = 0.0
        self._last_image_hash: str = ""
        self._last_ocr_text: str = ""

    # ── Public API ──────────────────────────────────────────────────────

    def should_call_llm(
        self,
        current_image_hash: str,
        current_ocr_text: str,
    ) -> bool:
        """Return ``True`` if the LLM should be invoked this cycle."""
        now = time.time()

        # 1) Time gate
        elapsed = now - self._last_approved_time
        if elapsed < self.min_interval:
            logger.debug(
                "Throttler: time gate blocked (%.1fs / %.1fs elapsed)",
                elapsed,
                self.min_interval,
            )
            return False

        # 2) Change gate — image hash
        if self._last_image_hash:
            dist = hamming_distance(current_image_hash, self._last_image_hash)
            if dist < self.change_threshold:
                # If hash says "same", double‐check OCR text similarity
                sim = text_similarity(current_ocr_text, self._last_ocr_text)
                if sim >= self.text_similarity_skip:
                    logger.debug(
                        "Throttler: change gate blocked "
                        "(hash_dist=%d, text_sim=%.2f)",
                        dist,
                        sim,
                    )
                    return False

        logger.info("Throttler: LLM call approved.")
        return True

    def record_call(
        self,
        image_hash: str,
        ocr_text: str,
    ) -> None:
        """Record that an LLM call was made (update internal state)."""
        self._last_approved_time = time.time()
        self._last_image_hash = image_hash
        self._last_ocr_text = ocr_text

    def force_next(self) -> None:
        """Force the next call to be approved (useful after errors)."""
        self._last_approved_time = 0.0
        self._last_image_hash = ""
