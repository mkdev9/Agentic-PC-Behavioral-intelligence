"""
desktop_agent.perception.screen_capture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
High-performance screen capture using the *mss* library.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import mss
import mss.tools
from PIL import Image

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures the primary monitor and returns a PIL Image."""

    def __init__(self, config: dict[str, Any]) -> None:
        cap_cfg = config.get("capture", {})
        self._monitor_index: int = cap_cfg.get("monitor", 1)
        self._downscale: int = cap_cfg.get("downscale", 2)

    async def capture(self) -> Image.Image:
        """Grab the screen in a thread and return a PIL Image.

        The capture itself is blocking (mss uses Win32/X11 APIs), so
        it is off-loaded to the default executor to keep the event loop
        responsive.
        """
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, self._grab)
        logger.debug(
            "Screen captured — %dx%d (downscaled %dx)",
            image.width,
            image.height,
            self._downscale,
        )
        return image

    def _grab(self) -> Image.Image:
        """Synchronous grab + optional down-scale."""
        with mss.mss() as sct:
            monitor = sct.monitors[self._monitor_index]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        if self._downscale > 1:
            new_size = (
                img.width // self._downscale,
                img.height // self._downscale,
            )
            img = img.resize(new_size, Image.LANCZOS)

        return img
