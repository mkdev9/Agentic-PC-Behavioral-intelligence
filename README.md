# Desktop Observability Agent

A production-grade, modular Python system that continuously observes your desktop session (with explicit consent) and generates real-time AI-powered insights about your activity using Google Gemini.

## Architecture

```
CAPTURE → PERCEIVE → STRUCTURE → REASON → OUTPUT → STORE → REPEAT
```

```
desktop_agent/
├── core/               # Agent loop, orchestrator, session state
│   ├── loop.py
│   ├── orchestrator.py
│   └── state_manager.py
├── perception/         # Screen capture, OCR, window tracking
│   ├── screen_capture.py
│   ├── ocr_engine.py
│   ├── window_tracker.py
│   └── activity_classifier.py
├── reasoning/          # LLM client, prompt engineering, summarization
│   ├── gemini_client.py
│   ├── prompt_builder.py
│   └── summarizer.py
├── output/             # Logging, console narration, optional overlay
│   ├── logger.py
│   ├── narrator.py
│   └── overlay.py
├── config/
│   └── settings.yaml
├── utils/              # Config loader, hashing, throttling, retry
│   ├── helpers.py
│   └── throttling.py
├── data/               # SQLite DB (created at runtime)
├── main.py
├── requirements.txt
└── README.md
```

## Prerequisites

| Dependency | Purpose |
|---|---|
| Python 3.11+ | Runtime |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Text extraction from screenshots |
| Google Gemini API key | LLM reasoning |

### Install Tesseract (Windows)

1. Download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install and add the install directory (e.g. `C:\Program Files\Tesseract-OCR`) to your system `PATH`.
3. Verify: `tesseract --version`

## Setup

```bash
# 1. Clone / navigate to the project
cd desktop_agent

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux / macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Gemini API key
set GEMINI_API_KEY=your_api_key_here        # Windows CMD
# $env:GEMINI_API_KEY="your_api_key_here"   # PowerShell
# export GEMINI_API_KEY=your_api_key_here   # Bash

# 5. Run the agent
python main.py
```

## Configuration

Edit `config/settings.yaml` to tune:

- **`agent.capture_interval`** — seconds between capture cycles (default `5`)
- **`throttling.min_interval`** — minimum seconds between LLM calls (default `30`)
- **`throttling.change_threshold`** — perceptual hash distance to consider the screen "changed"
- **`llm.model`** — Gemini model identifier (default `gemini-2.0-flash`)
- **`output.overlay`** — set to `true` to enable the floating HUD window

## How It Works

1. **ScreenCapture** grabs the primary monitor using `mss`.
2. **OCREngine** extracts visible text with Tesseract.
3. **WindowTracker** identifies the active app and process.
4. **ActivityClassifier** maps the app/text to a category (coding, browsing, etc.).
5. **Throttler** checks whether the screen has changed enough to warrant an LLM call.
6. **PromptBuilder** assembles context (current + historical) into a structured prompt.
7. **GeminiClient** sends the prompt and receives an insight structured as:
   - `[ACTIVITY]` — what the user is doing
   - `[INTENT]` — inferred goal
   - `[INEFFICIENCY]` — detected friction
   - `[OPTIMIZATION]` — actionable suggestion
   - `[PREDICTION]` — what comes next
8. **Narrator** prints the insight to the console with colour.
9. **StateManager** persists the snapshot to SQLite for future context.

## Stopping the Agent

Press **Ctrl+C** for a graceful shutdown. The database is flushed and all resources are released.

## License

Private / Internal use.
