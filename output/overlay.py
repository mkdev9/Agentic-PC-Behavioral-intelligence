"""
desktop_agent.output.overlay
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Optional minimal tkinter overlay that floats the latest insight on screen.

Disabled by default (config ``output.overlay: false``).
This module is intentionally lightweight — its purpose is to provide a
non-intrusive heads-up display, not a full GUI.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class Overlay:
    """Transparent floating label showing the latest insight.

    The overlay runs in its own daemon thread so it never blocks the
    async event loop.
    """

    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled
        self._thread: threading.Thread | None = None
        self._root: Any = None
        self._label: Any = None
        self._ready = threading.Event()

    # ── Lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch the overlay thread (no-op if disabled)."""
        if not self._enabled:
            return
        self._thread = threading.Thread(
            target=self._run_tk, daemon=True, name="overlay"
        )
        self._thread.start()
        self._ready.wait(timeout=5)
        logger.info("Overlay thread started.")

    def stop(self) -> None:
        """Close the overlay window."""
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:  # noqa: BLE001
                pass

    # ── Update ──────────────────────────────────────────────────────────

    def update(self, text: str) -> None:
        """Update the displayed text (thread-safe)."""
        if not self._enabled or self._root is None or self._label is None:
            return
        # Schedule on the Tk main-loop thread
        try:
            self._root.after(0, lambda: self._label.config(text=text[:300]))
        except Exception:  # noqa: BLE001
            pass

    # ── Internal ────────────────────────────────────────────────────────

    def _run_tk(self) -> None:
        """Create and run the tkinter event loop (runs in daemon thread)."""
        try:
            import tkinter as tk

            root = tk.Tk()
            root.title("Desktop Agent")
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.85)

            # Position at top-right
            screen_w = root.winfo_screenwidth()
            width, height = 420, 160
            x = screen_w - width - 20
            y = 30
            root.geometry(f"{width}x{height}+{x}+{y}")
            root.configure(bg="#1e1e2e")

            label = tk.Label(
                root,
                text="Desktop Agent\nWaiting for first insight…",
                font=("Consolas", 10),
                fg="#cdd6f4",
                bg="#1e1e2e",
                wraplength=width - 20,
                justify="left",
                anchor="nw",
                padx=10,
                pady=10,
            )
            label.pack(fill="both", expand=True)

            self._root = root
            self._label = label
            self._ready.set()
            root.mainloop()

        except Exception as exc:  # noqa: BLE001
            logger.warning("Overlay could not start: %s", exc)
            self._ready.set()
