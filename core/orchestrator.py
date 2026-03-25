"""
desktop_agent.core.orchestrator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Central coordinator that wires every module together and executes the
observation pipeline:

    CAPTURE → PERCEIVE → STRUCTURE → REASON → OUTPUT → STORE
"""

from __future__ import annotations

import logging
import queue
from typing import Any

from core.state_manager import StateManager
from output.narrator import Narrator
from output.overlay import Overlay
from perception.activity_classifier import ActivityClassifier
from perception.ocr_engine import OCREngine
from perception.screen_capture import ScreenCapture
from perception.window_tracker import WindowTracker
from reasoning.gemini_client import GeminiClient
from reasoning.prompt_builder import PromptBuilder
from reasoning.summarizer import Summarizer
from utils.helpers import content_hash, perceptual_hash
from utils.throttling import Throttler

logger = logging.getLogger(__name__)


class Orchestrator:
    """Initialises all subsystems and drives a single observation cycle."""

    def __init__(
        self,
        config: dict[str, Any],
        event_queue: queue.Queue[dict[str, Any]] | None = None,
    ) -> None:
        self._config = config
        self._event_queue = event_queue

        # ── Perception ──────────────────────────────────────────────────
        self._screen = ScreenCapture(config)
        self._ocr = OCREngine(config)
        self._window = WindowTracker()
        self._classifier = ActivityClassifier()

        # ── Reasoning ───────────────────────────────────────────────────
        self._gemini = GeminiClient(config)
        self._prompt_builder = PromptBuilder()
        self._summarizer = Summarizer()

        # ── Output ──────────────────────────────────────────────────────
        out_cfg = config.get("output", {})
        self._narrator = Narrator(enabled=out_cfg.get("narration", True))
        self._overlay = Overlay(enabled=out_cfg.get("overlay", False))

        # ── State & Throttling ──────────────────────────────────────────
        db_path = config.get("database", {}).get("path", "data/session.db")
        self._state = StateManager(db_path)

        thr_cfg = config.get("throttling", {})
        self._throttler = Throttler(
            min_interval=thr_cfg.get("min_interval", 30),
            change_threshold=thr_cfg.get("change_threshold", 5),
            text_similarity_skip=thr_cfg.get("text_similarity_skip", 0.95),
        )

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialise persistent resources (DB, overlay)."""
        await self._state.initialize()
        self._overlay.start()
        self._push_event({"type": "status", "message": "● Running"})
        logger.info("Orchestrator started.")

    async def stop(self) -> None:
        """Cleanly shut down resources."""
        self._overlay.stop()
        await self._state.close()
        self._push_event({"type": "status", "message": "● Stopped"})
        logger.info("Orchestrator stopped.")

    # ── Single Cycle ────────────────────────────────────────────────────

    async def run_cycle(self) -> None:
        """Execute one full CAPTURE → … → STORE pipeline iteration."""
        try:
            # 1. CAPTURE
            image = await self._screen.capture()

            # 2. PERCEIVE
            ocr_text = await self._ocr.extract_text(image)
            window_info = await self._window.get_active_window()
            activity = self._classifier.classify(
                app_name=window_info.app_name,
                window_title=window_info.window_title,
                ocr_text=ocr_text,
            )

            # 3. STRUCTURE — compute hashes for change detection
            img_hash = perceptual_hash(image)
            txt_hash = content_hash(ocr_text)

            # Push cycle data to the UI
            self._push_event({
                "type": "cycle_data",
                "app_name": window_info.app_name,
                "window_title": window_info.window_title,
                "activity_type": activity.label,
            })

            # 4. REASON (gated by throttler)
            insight = ""
            if self._throttler.should_call_llm(img_hash, ocr_text):
                # Build session context
                recent = await self._state.get_recent_snapshots(limit=15)
                session_summary = self._summarizer.summarize(recent)

                prompt = self._prompt_builder.build(
                    app_name=window_info.app_name,
                    window_title=window_info.window_title,
                    activity_type=activity.label,
                    ocr_text=ocr_text,
                    session_summary=session_summary,
                )

                insight = await self._gemini.generate(prompt)
                insight = self._summarizer.compress_insight(insight)

                # Record successful call in throttler
                self._throttler.record_call(img_hash, ocr_text)

                # 5. OUTPUT
                self._narrator.narrate(insight, app_name=window_info.app_name)
                self._overlay.update(insight)

                # Push insight to the UI
                self._push_event({
                    "type": "insight",
                    "insight": insight,
                    "app_name": window_info.app_name,
                })
            else:
                logger.debug("Cycle skipped reasoning (throttled).")

            # 6. STORE — always record the snapshot
            await self._state.save_snapshot(
                app_name=window_info.app_name,
                window_title=window_info.window_title,
                activity_type=activity.label,
                ocr_text_hash=txt_hash,
                ocr_text=ocr_text[:2000],  # cap storage size
                image_hash=img_hash,
                insight=insight,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("Cycle failed: %s", exc, exc_info=True)
            self._push_event({
                "type": "error",
                "message": str(exc),
            })
            # Force the throttler to allow next cycle in case the error
            # was transient and the screen has genuinely changed.
            self._throttler.force_next()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _push_event(self, event: dict[str, Any]) -> None:
        """Push an event to the UI queue (no-op if no queue)."""
        if self._event_queue is not None:
            try:
                self._event_queue.put_nowait(event)
            except queue.Full:
                pass
