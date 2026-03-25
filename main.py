"""
Desktop Observability Agent — Entry Point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Loads configuration, sets up logging, and starts the agent.

Usage::

    cd desktop_agent
    python main.py            # console mode
    python main.py --ui       # dashboard UI mode
    python main.py --config path/to/settings.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import threading
from pathlib import Path

# Ensure the project root is on sys.path so that absolute imports work
# regardless of where the user invokes `python main.py` from.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.loop import AgentLoop  # noqa: E402
from output.logger import setup_logging  # noqa: E402
from utils.helpers import load_config  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Desktop Observability Agent — local AI-powered desktop insights",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a custom settings.yaml (default: config/settings.yaml)",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        default=False,
        help="Launch the graphical dashboard instead of console output",
    )
    return parser.parse_args()


# ── Console Mode ────────────────────────────────────────────────────────────

def _run_console(config: dict) -> None:
    """Original headless / console mode."""
    agent = AgentLoop(config)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\n  ✔  Interrupted — shutting down.\n")


# ── Dashboard Mode ──────────────────────────────────────────────────────────

def _run_dashboard(config: dict) -> None:
    """Launch the tkinter dashboard on the main thread with the agent
    loop running in a background daemon thread."""
    from ui.dashboard import Dashboard

    dashboard = Dashboard()
    event_queue = dashboard.event_queue

    # The agent loop needs to run in its own thread with its own asyncio
    # event loop because tkinter must own the main thread.
    agent = AgentLoop(config, event_queue=event_queue)

    def _agent_thread() -> None:
        try:
            asyncio.run(agent.run(skip_consent=True))
        except Exception:
            pass

    thread = threading.Thread(target=_agent_thread, daemon=True, name="agent-loop")
    thread.start()

    # This blocks until the dashboard window is closed.
    try:
        dashboard.run()
    finally:
        agent.stop()


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    config = load_config(args.config)
    setup_logging(config)

    if args.ui:
        _run_dashboard(config)
    else:
        _run_console(config)


if __name__ == "__main__":
    main()
