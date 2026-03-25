"""
desktop_agent.core.loop
~~~~~~~~~~~~~~~~~~~~~~~~
Async agent loop with graceful shutdown support.

This module is the runtime engine that repeatedly invokes the orchestrator
at the configured interval and handles OS signals for clean exit.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import signal
import sys
from typing import Any

from core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class AgentLoop:
    """Runs the observation pipeline on a fixed interval."""

    def __init__(
        self,
        config: dict[str, Any],
        event_queue: queue.Queue[dict[str, Any]] | None = None,
    ) -> None:
        self._config = config
        self._interval: float = config.get("agent", {}).get(
            "capture_interval", 5
        )
        self._orchestrator = Orchestrator(config, event_queue=event_queue)
        self._running = False

    # ── Public API ──────────────────────────────────────────────────────

    async def run(self, *, skip_consent: bool = False) -> None:
        """Start the agent loop (blocks until shutdown)."""
        if not skip_consent and not self._request_consent():
            logger.info("User declined consent. Exiting.")
            print("\n  ✖  Consent declined — exiting.\n")
            return

        self._running = True
        self._install_signal_handlers()

        await self._orchestrator.start()
        logger.info(
            "Agent loop started — interval=%.1fs", self._interval
        )
        print(
            f"\n  ✔  Desktop Agent is running "
            f"(capture every {self._interval}s). Press Ctrl+C to stop.\n"
        )

        try:
            cycle = 0
            while self._running:
                cycle += 1
                logger.info("── Cycle %d ──", cycle)
                await self._orchestrator.run_cycle()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            logger.info("Loop cancelled.")
        finally:
            await self._orchestrator.stop()
            logger.info("Agent loop shut down cleanly.")
            print("\n  ✔  Desktop Agent stopped.\n")

    def stop(self) -> None:
        """Request the loop to stop (thread-safe)."""
        self._running = False

    # ── Consent ─────────────────────────────────────────────────────────

    def _request_consent(self) -> bool:
        """Prompt the user for explicit consent to capture their screen."""
        require = (
            self._config.get("agent", {}).get("require_consent", True)
        )
        if not require:
            return True

        print()
        print("  ╔══════════════════════════════════════════════════════╗")
        print("  ║        DESKTOP OBSERVABILITY AGENT — CONSENT        ║")
        print("  ╠══════════════════════════════════════════════════════╣")
        print("  ║                                                      ║")
        print("  ║  This tool will periodically capture your screen,   ║")
        print("  ║  read visible text via OCR, and detect the active   ║")
        print("  ║  application. Data is processed locally and sent    ║")
        print("  ║  to the Google Gemini API for analysis.             ║")
        print("  ║                                                      ║")
        print("  ║  No data is stored externally. Session data is      ║")
        print("  ║  kept in a local SQLite database only.              ║")
        print("  ║                                                      ║")
        print("  ╚══════════════════════════════════════════════════════╝")
        print()

        try:
            answer = input("  Do you consent to screen observation? [y/N] > ")
        except (EOFError, KeyboardInterrupt):
            return False
        return answer.strip().lower() in ("y", "yes")

    # ── Signal Handling ─────────────────────────────────────────────────

    def _install_signal_handlers(self) -> None:
        """Register OS signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._handle_signal)
        else:
            # On Windows, signal handlers can't be set on the event loop;
            # Ctrl+C raises KeyboardInterrupt which asyncio already handles.
            pass

    def _handle_signal(self) -> None:
        logger.info("Shutdown signal received.")
        self._running = False

