"""
desktop_agent.perception.window_tracker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Detects the currently active (foreground) window and its owning process.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """Structured representation of the active window."""

    app_name: str = "unknown"
    window_title: str = ""
    pid: int = 0
    process_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "window_title": self.window_title,
            "pid": self.pid,
            "process_name": self.process_name,
        }


class WindowTracker:
    """Cross-platform active-window detection (primary target: Windows)."""

    async def get_active_window(self) -> WindowInfo:
        """Return a :class:`WindowInfo` for the current foreground window."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._detect)

    @staticmethod
    def _detect() -> WindowInfo:
        info = WindowInfo()
        try:
            import pygetwindow as gw

            active = gw.getActiveWindow()
            if active is None:
                return info

            info.window_title = active.title or ""
            # pygetwindow does not expose PID directly on all platforms.
            # On Windows we can use the win32 handle → PID mapping.
            pid = _pid_from_hwnd(getattr(active, "_hWnd", 0))
            info.pid = pid
            if pid:
                try:
                    proc = psutil.Process(pid)
                    info.process_name = proc.name()
                    info.app_name = proc.name().replace(".exe", "")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    info.app_name = info.window_title.split(" - ")[-1].strip()
            else:
                info.app_name = info.window_title.split(" - ")[-1].strip()

        except Exception as exc:  # noqa: BLE001
            logger.warning("Window detection failed: %s", exc)

        return info


def _pid_from_hwnd(hwnd: int) -> int:
    """Use ctypes to resolve a Win32 window handle to a PID."""
    if not hwnd:
        return 0
    try:
        import ctypes
        import ctypes.wintypes

        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(  # type: ignore[attr-defined]
            ctypes.wintypes.HWND(hwnd),
            ctypes.byref(pid),
        )
        return pid.value
    except Exception:  # noqa: BLE001
        return 0
