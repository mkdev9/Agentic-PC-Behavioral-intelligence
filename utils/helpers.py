"""
desktop_agent.utils.helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Configuration loading, image hashing, retry decorator, and timestamp helpers.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml
from PIL import Image

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and return the YAML configuration dictionary.

    Environment variable overrides:
        GEMINI_API_KEY  →  config["llm"]["api_key"]
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        config: dict[str, Any] = yaml.safe_load(fh)

    # API key: prefer YAML value, fall back to environment variable
    llm_cfg = config.setdefault("llm", {})
    yaml_key = llm_cfg.get("api_key", "")
    env_key = os.environ.get("GEMINI_API_KEY", "")
    llm_cfg["api_key"] = yaml_key if yaml_key else env_key

    logger.info("Configuration loaded from %s", config_path)
    return config


# ── Image Hashing (for change detection) ───────────────────────────────────

def perceptual_hash(image: Image.Image, hash_size: int = 8) -> str:
    """Compute a simple average‐hash of *image*.

    Returns a hex string.  Two hashes can be compared with
    :func:`hamming_distance` to decide whether a screen has meaningfully
    changed between captures.
    """
    # Resize to a small square and convert to greyscale
    img = image.resize((hash_size, hash_size), Image.LANCZOS).convert("L")
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p >= avg else "0" for p in pixels)
    return f"{int(bits, 2):0{hash_size * hash_size // 4}x}"


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Return the Hamming distance between two hex hash strings."""
    if len(hash_a) != len(hash_b):
        return max(len(hash_a), len(hash_b)) * 4  # worst case
    bin_a = bin(int(hash_a, 16))
    bin_b = bin(int(hash_b, 16))
    return sum(ca != cb for ca, cb in zip(bin_a, bin_b))


def text_similarity(a: str, b: str) -> float:
    """Quick Jaccard similarity on word sets (0‑1)."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# ── Content Hash ───────────────────────────────────────────────────────────

def content_hash(text: str) -> str:
    """SHA-256 of *text* for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Timestamps ─────────────────────────────────────────────────────────────

def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def utc_now_epoch() -> float:
    """Return the current UTC time as a UNIX epoch float."""
    return time.time()


# ── Retry Decorator ────────────────────────────────────────────────────────

def retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable:
    """Decorator that retries a function with exponential back‐off.

    Usage::

        @retry(max_attempts=5, exceptions=(ConnectionError, TimeoutError))
        async def call_api(): ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    wait = backoff_base ** attempt
                    logger.warning(
                        "Attempt %d/%d for %s failed (%s). Retrying in %.1fs …",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        wait,
                    )
                    await _async_sleep(wait)
            raise last_exc  # type: ignore[misc]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    wait = backoff_base ** attempt
                    logger.warning(
                        "Attempt %d/%d for %s failed (%s). Retrying in %.1fs …",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
            raise last_exc  # type: ignore[misc]

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


async def _async_sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)
