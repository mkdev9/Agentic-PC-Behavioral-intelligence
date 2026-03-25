"""
desktop_agent.reasoning.prompt_builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Constructs structured high-quality prompts for the Gemini LLM.

The prompt is designed to elicit *insights*, not descriptions — the model
should infer user intent, detect inefficiencies, suggest optimisations, and
predict next actions.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── System Prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a desktop productivity analyst embedded in the user's workstation.
You observe the user's screen activity in real time and produce concise,
high-leverage insights — NOT surface-level descriptions.

Rules:
• Infer the user's underlying INTENT, not just what is visible.
• Detect inefficiencies in workflow, app switching, or repeated actions.
• Suggest concrete, actionable optimisations.
• Predict what the user is likely to do next or needs next.
• Never restate obvious information the user already knows.
• Keep each section to 1–3 sentences max.
• If activity is idle or screensaver, say so briefly.

You MUST respond in EXACTLY this format (keep the brackets and labels):

[ACTIVITY]
<what the user is doing right now — one line>

[INTENT]
<the probable goal or focus behind this activity>

[INEFFICIENCY]
<any friction, wasted time, or suboptimal pattern you notice — or "None detected.">

[OPTIMIZATION]
<a concrete, actionable suggestion to improve the workflow>

[PREDICTION]
<what the user is likely to do next, or what they might need>
"""

# ── Prompt Builder ──────────────────────────────────────────────────────────


class PromptBuilder:
    """Builds the full prompt from current perception context + history."""

    def build(
        self,
        *,
        app_name: str,
        window_title: str,
        activity_type: str,
        ocr_text: str,
        session_summary: str,
    ) -> str:
        """Return the assembled prompt string."""
        # Truncate OCR text to avoid blowing the context window
        max_ocr = 3000
        if len(ocr_text) > max_ocr:
            ocr_text = ocr_text[:max_ocr] + "\n… [truncated]"

        user_block = (
            f"### Current Observation\n"
            f"- **Application**: {app_name}\n"
            f"- **Window title**: {window_title}\n"
            f"- **Activity category**: {activity_type}\n\n"
            f"#### Visible Text (OCR)\n"
            f"```\n{ocr_text}\n```\n\n"
            f"### Recent Session History\n"
            f"```\n{session_summary}\n```\n"
        )

        prompt = f"{SYSTEM_PROMPT}\n\n---\n\n{user_block}"
        logger.debug("Prompt built — %d chars total", len(prompt))
        return prompt
