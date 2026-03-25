"""
desktop_agent.output.narrator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Formats and prints LLM insights to the console with color and structure.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from colorama import Fore, Style

logger = logging.getLogger(__name__)

# Section → color
_SECTION_COLORS: dict[str, str] = {
    "ACTIVITY": Fore.CYAN + Style.BRIGHT,
    "INTENT": Fore.GREEN + Style.BRIGHT,
    "INEFFICIENCY": Fore.YELLOW + Style.BRIGHT,
    "OPTIMIZATION": Fore.MAGENTA + Style.BRIGHT,
    "PREDICTION": Fore.BLUE + Style.BRIGHT,
}


class Narrator:
    """Pretty-prints insights to the console."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    def narrate(self, insight: str, app_name: str = "") -> None:
        """Print *insight* with colored section headers."""
        if not self._enabled or not insight.strip():
            return

        now = datetime.now().strftime("%H:%M:%S")
        separator = f"{Fore.WHITE}{Style.DIM}{'─' * 60}{Style.RESET_ALL}"

        print(f"\n{separator}")
        print(
            f"{Fore.WHITE}{Style.DIM}[{now}]{Style.RESET_ALL}  "
            f"{Fore.WHITE}{Style.BRIGHT}Desktop Agent Insight{Style.RESET_ALL}"
            f"  {Fore.WHITE}{Style.DIM}({app_name}){Style.RESET_ALL}"
        )
        print(separator)

        # Parse and colorise each [SECTION]
        for line in insight.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # Check if line is a section header like [ACTIVITY]
            match = re.match(r"^\[(\w+)](.*)$", stripped)
            if match:
                section = match.group(1).upper()
                rest = match.group(2).strip()
                color = _SECTION_COLORS.get(section, Fore.WHITE)
                print(f"  {color}[{section}]{Style.RESET_ALL} {rest}")
            else:
                # Continuation line
                print(f"    {Fore.WHITE}{stripped}{Style.RESET_ALL}")

        print(separator)
        print()
