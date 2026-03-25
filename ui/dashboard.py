"""
desktop_agent.ui.dashboard
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Modern dark-themed tkinter dashboard that displays real-time agent output.

Architecture
────────────
• Tkinter runs on the **main thread** (OS requirement).
• The async agent loop runs in a **background daemon thread**.
• A ``queue.Queue`` transports ``UIEvent`` dicts from the agent → UI.
• The UI polls the queue every 200 ms via ``root.after()``.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from typing import Any

# ── Colour Palette (Catppuccin Mocha-inspired) ─────────────────────────────

_C = {
    "bg":           "#1e1e2e",
    "surface":      "#181825",
    "panel":        "#11111b",
    "border":       "#313244",
    "text":         "#cdd6f4",
    "subtext":      "#a6adc8",
    "dim":          "#585b70",
    "green":        "#a6e3a1",
    "red":          "#f38ba8",
    "yellow":       "#f9e2af",
    "blue":         "#89b4fa",
    "mauve":        "#cba6f7",
    "teal":         "#94e2d5",
    "peach":        "#fab387",
    "accent":       "#b4befe",
}

# Section label → colour
_SECTION_COLOURS: dict[str, str] = {
    "ACTIVITY":       _C["teal"],
    "INTENT":         _C["green"],
    "INEFFICIENCY":   _C["yellow"],
    "OPTIMIZATION":   _C["mauve"],
    "PREDICTION":     _C["blue"],
}

# ── Event types pushed by the orchestrator ─────────────────────────────────

EVENT_CYCLE_DATA  = "cycle_data"
EVENT_INSIGHT     = "insight"
EVENT_STATUS      = "status"
EVENT_ERROR       = "error"


class Dashboard:
    """Full-screen tkinter dashboard for the Desktop Agent.

    Call :meth:`create_queue` to get the thread-safe queue, then pass it
    to the agent.  Call :meth:`run` on the **main thread** to launch the
    UI — it blocks until the window is closed.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._root: tk.Tk | None = None
        self._running = False

        # Widget refs (assigned in _build)
        self._status_var:    tk.StringVar | None = None
        self._cycle_var:     tk.StringVar | None = None
        self._app_var:       tk.StringVar | None = None
        self._activity_var:  tk.StringVar | None = None
        self._insight_text:  tk.Text | None = None
        self._log_text:      tk.Text | None = None
        self._elapsed_var:   tk.StringVar | None = None
        self._cycle_count = 0
        self._insight_count = 0
        self._start_time = time.time()

    # ── Public API ──────────────────────────────────────────────────────

    @property
    def event_queue(self) -> queue.Queue[dict[str, Any]]:
        """Queue the agent pushes events into."""
        return self._queue

    def run(self) -> None:
        """Build and start the tkinter main loop (blocks)."""
        self._root = tk.Tk()
        self._root.title("Desktop Agent — Dashboard")
        self._root.configure(bg=_C["bg"])
        self._root.minsize(1000, 680)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Try to maximise
        try:
            self._root.state("zoomed")
        except tk.TclError:
            self._root.attributes("-zoomed", True)

        self._build()
        self._running = True
        self._poll_queue()
        self._tick_clock()
        self._root.mainloop()

    def request_stop(self) -> None:
        """Signal the dashboard to close (can be called from any thread)."""
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    # ── Build UI ────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = self._root
        assert root is not None

        # ── Fonts ───────────────────────────────────────────────────────
        title_font  = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        header_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        body_font   = tkfont.Font(family="Consolas", size=10)
        small_font  = tkfont.Font(family="Segoe UI", size=9)
        label_font  = tkfont.Font(family="Segoe UI", size=10)

        # ── StringVars ──────────────────────────────────────────────────
        self._status_var   = tk.StringVar(value="● Starting…")
        self._cycle_var    = tk.StringVar(value="0")
        self._app_var      = tk.StringVar(value="—")
        self._activity_var = tk.StringVar(value="—")
        self._elapsed_var  = tk.StringVar(value="00:00:00")

        # ═══════════════════════════════════════════════════════════════
        #  TOP BAR
        # ═══════════════════════════════════════════════════════════════
        top = tk.Frame(root, bg=_C["surface"], pady=12, padx=20)
        top.pack(fill="x")

        tk.Label(
            top, text="⬡  Desktop Agent", font=title_font,
            fg=_C["accent"], bg=_C["surface"],
        ).pack(side="left")

        # Status pill
        status_frame = tk.Frame(top, bg=_C["surface"])
        status_frame.pack(side="right")
        tk.Label(
            status_frame, textvariable=self._status_var, font=small_font,
            fg=_C["green"], bg=_C["surface"],
        ).pack(side="right", padx=(0, 8))

        # ═══════════════════════════════════════════════════════════════
        #  STATS ROW
        # ═══════════════════════════════════════════════════════════════
        stats = tk.Frame(root, bg=_C["bg"], pady=8, padx=20)
        stats.pack(fill="x")

        for label_text, var, color in [
            ("CYCLES", self._cycle_var, _C["blue"]),
            ("ACTIVE APP", self._app_var, _C["teal"]),
            ("ACTIVITY", self._activity_var, _C["mauve"]),
            ("UPTIME", self._elapsed_var, _C["peach"]),
        ]:
            card = tk.Frame(stats, bg=_C["surface"], padx=16, pady=8,
                            highlightbackground=_C["border"],
                            highlightthickness=1)
            card.pack(side="left", padx=(0, 10), fill="x", expand=True)
            tk.Label(
                card, text=label_text, font=small_font,
                fg=_C["dim"], bg=_C["surface"],
            ).pack(anchor="w")
            tk.Label(
                card, textvariable=var, font=header_font,
                fg=color, bg=_C["surface"],
            ).pack(anchor="w")

        # ═══════════════════════════════════════════════════════════════
        #  MAIN CONTENT — two panes
        # ═══════════════════════════════════════════════════════════════
        content = tk.PanedWindow(
            root, orient="horizontal", bg=_C["bg"],
            sashwidth=4, sashrelief="flat",
        )
        content.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        # ── LEFT: Insights ──────────────────────────────────────────────
        left = tk.Frame(content, bg=_C["panel"],
                        highlightbackground=_C["border"],
                        highlightthickness=1)
        content.add(left, minsize=500, stretch="always")

        tk.Label(
            left, text="  ✦  LIVE INSIGHTS", font=header_font,
            fg=_C["accent"], bg=_C["panel"], anchor="w", pady=8, padx=8,
        ).pack(fill="x")

        sep = tk.Frame(left, bg=_C["border"], height=1)
        sep.pack(fill="x")

        self._insight_text = tk.Text(
            left, bg=_C["panel"], fg=_C["text"], font=body_font,
            wrap="word", relief="flat", padx=12, pady=8,
            insertbackground=_C["text"], selectbackground=_C["border"],
            cursor="arrow", state="disabled",
        )
        self._insight_text.pack(fill="both", expand=True)

        # Configure tags for coloured sections
        for section, colour in _SECTION_COLOURS.items():
            self._insight_text.tag_configure(
                section,
                foreground=colour,
                font=tkfont.Font(family="Consolas", size=10, weight="bold"),
            )
        self._insight_text.tag_configure(
            "timestamp", foreground=_C["dim"],
            font=tkfont.Font(family="Consolas", size=9),
        )
        self._insight_text.tag_configure(
            "separator", foreground=_C["border"],
        )
        self._insight_text.tag_configure(
            "body", foreground=_C["text"],
        )
        self._insight_text.tag_configure(
            "error", foreground=_C["red"],
            font=tkfont.Font(family="Consolas", size=10, weight="bold"),
        )

        # ── RIGHT: Activity Log ─────────────────────────────────────────
        right = tk.Frame(content, bg=_C["panel"],
                         highlightbackground=_C["border"],
                         highlightthickness=1)
        content.add(right, minsize=320, stretch="never")

        tk.Label(
            right, text="  ◉  ACTIVITY LOG", font=header_font,
            fg=_C["subtext"], bg=_C["panel"], anchor="w", pady=8, padx=8,
        ).pack(fill="x")

        sep2 = tk.Frame(right, bg=_C["border"], height=1)
        sep2.pack(fill="x")

        self._log_text = tk.Text(
            right, bg=_C["panel"], fg=_C["subtext"], font=small_font,
            wrap="word", relief="flat", padx=10, pady=8,
            insertbackground=_C["subtext"], selectbackground=_C["border"],
            cursor="arrow", state="disabled",
        )
        self._log_text.pack(fill="both", expand=True)
        self._log_text.tag_configure("ts", foreground=_C["dim"])
        self._log_text.tag_configure("app", foreground=_C["teal"])
        self._log_text.tag_configure("act", foreground=_C["mauve"])

    # ── Queue Polling ───────────────────────────────────────────────────

    def _poll_queue(self) -> None:
        """Drain the queue and update widgets. Reschedules itself."""
        if not self._running:
            return
        try:
            while True:
                event = self._queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        if self._root:
            self._root.after(200, self._poll_queue)

    def _handle_event(self, event: dict[str, Any]) -> None:
        etype = event.get("type", "")

        if etype == EVENT_CYCLE_DATA:
            self._cycle_count += 1
            self._cycle_var.set(str(self._cycle_count))  # type: ignore[union-attr]
            self._app_var.set(event.get("app_name", "—"))  # type: ignore[union-attr]
            self._activity_var.set(event.get("activity_type", "—"))  # type: ignore[union-attr]
            self._status_var.set("● Running")  # type: ignore[union-attr]

            # Append to activity log
            self._append_log(event)

        elif etype == EVENT_INSIGHT:
            self._insight_count += 1
            self._append_insight(event.get("insight", ""), event.get("app_name", ""))

        elif etype == EVENT_STATUS:
            self._status_var.set(event.get("message", ""))  # type: ignore[union-attr]

        elif etype == EVENT_ERROR:
            self._append_insight(
                f"[ERROR] {event.get('message', 'Unknown error')}", "",
                is_error=True,
            )

    # ── Append helpers ──────────────────────────────────────────────────

    def _append_insight(
        self, insight: str, app_name: str, *, is_error: bool = False,
    ) -> None:
        widget = self._insight_text
        if widget is None:
            return

        widget.configure(state="normal")
        now = datetime.now().strftime("%H:%M:%S")

        # Separator
        widget.insert("end", f"{'─' * 55}\n", "separator")
        widget.insert("end", f"  [{now}]  ", "timestamp")
        if app_name:
            widget.insert("end", f"{app_name}\n", "body")
        else:
            widget.insert("end", "\n")

        if is_error:
            widget.insert("end", f"  {insight}\n\n", "error")
        else:
            # Parse [SECTION] lines and colour them
            for line in insight.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                tagged = False
                for section in _SECTION_COLOURS:
                    if stripped.startswith(f"[{section}]"):
                        widget.insert("end", f"  {stripped}\n", section)
                        tagged = True
                        break
                if not tagged:
                    widget.insert("end", f"    {stripped}\n", "body")
            widget.insert("end", "\n")

        widget.see("end")
        widget.configure(state="disabled")

    def _append_log(self, event: dict[str, Any]) -> None:
        widget = self._log_text
        if widget is None:
            return

        widget.configure(state="normal")
        now = datetime.now().strftime("%H:%M:%S")

        app = event.get("app_name", "—")
        act = event.get("activity_type", "—")
        title = event.get("window_title", "")
        # Truncate long titles
        if len(title) > 50:
            title = title[:47] + "…"

        widget.insert("end", f"[{now}] ", "ts")
        widget.insert("end", f"{app}", "app")
        widget.insert("end", f" ({act})", "act")
        widget.insert("end", f"\n  {title}\n\n")

        widget.see("end")
        widget.configure(state="disabled")

    # ── Clock ───────────────────────────────────────────────────────────

    def _tick_clock(self) -> None:
        if not self._running:
            return
        elapsed = int(time.time() - self._start_time)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        self._elapsed_var.set(f"{h:02d}:{m:02d}:{s:02d}")  # type: ignore[union-attr]
        if self._root:
            self._root.after(1000, self._tick_clock)

    # ── Close ───────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        self._running = False
        if self._root:
            self._root.destroy()
