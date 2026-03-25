# Desktop Observability Agent

A modular Python system that observes your desktop session (with explicit user consent) and generates structured, real-time insights about what you're doing — and how to do it better — using Google Gemini.

---

## What This Actually Does

Most tools log activity. This one **interprets** it.

- Watches your screen (interval-based, not invasive streaming)
- Extracts text + context from what you're doing
- Infers intent and workflow patterns
- Identifies inefficiencies
- Suggests optimizations in real time
- Stores history for longitudinal reasoning

You end up with something closer to a **personal workflow analyst** than a tracker.

---

## Core Loop

```
CAPTURE → PERCEIVE → STRUCTURE → REASON → OUTPUT → STORE → REPEAT
```

This is deliberate. Each stage is isolated so you can replace or extend it without breaking the system.

---

## Architecture

```
desktop_agent/
├── core/               # Orchestration, loop control, session lifecycle
├── perception/         # Raw signal extraction (screen, OCR, app context)
├── reasoning/          # LLM interaction + prompt construction
├── output/             # Human-facing feedback (console / overlay)
├── config/             # Runtime configuration
├── utils/              # Shared primitives (throttling, hashing, etc.)
├── ui/                 # Dashboard interface
├── data/               # SQLite persistence layer
└── main.py             # Entry point
```

## Why This Exists

If you can't observe your workflow at a systems level, you can't improve it.

This project is built around a simple assumption:

> Most productivity loss is not from lack of effort, but from **invisible inefficiencies**.

This agent makes those inefficiencies explicit.

---

## Prerequisites

| Dependency | Why it exists |
|---|---|
| Python 3.11+ | Runtime |
| [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) | Converts pixels → text |
| Gemini API key | Converts context → reasoning |

### Install Tesseract (Windows)

1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to `PATH`
3. Verify:

```bash
tesseract --version
```

---

## Setup

```bash
# Clone the repo
cd desktop_agent

# Create environment
python -m venv .venv
.venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Set API key
set GEMINI_API_KEY=your_api_key_here

# Run (console mode)
python main.py

# Run (dashboard UI)
python main.py --ui
```

---

## Configuration

Edit `config/settings.yaml`.

Key controls:

| Setting | What it controls |
|---|---|
| `capture_interval` | How often the system observes your screen. Lower = more responsive, higher cost. |
| `min_interval` | Hard throttle on LLM calls. Prevents useless repeated reasoning. |
| `change_threshold` | Defines what "meaningful change" means. Critical for cost vs signal quality. |
| `model` | Gemini model selection |
| `overlay` | Enables/disables real-time UI layer |

If you ignore this file, the system will work — just inefficiently.

---

## How It Works (Concrete Flow)

1. Screen is captured using `mss`
2. OCR extracts visible text
3. Active window + process are identified
4. Activity is classified (coding, browsing, etc.)
5. A perceptual hash detects meaningful change
6. If change passes threshold:
   - Context is built (current + history)
   - Prompt is constructed
   - Gemini is queried
   - Output is structured into:
     - **Activity**
     - **Intent**
     - **Inefficiency**
     - **Optimization**
     - **Prediction**
7. Insight is displayed + stored

---

## Output Example

```
[ACTIVITY] Debugging Python code in VS Code
[INTENT] Fixing runtime error in data pipeline
[INEFFICIENCY] Re-reading logs without isolating failure point
[OPTIMIZATION] Add targeted logging or breakpoint inspection
[PREDICTION] Will continue trial-and-error debugging
```

If your outputs look generic, your prompts or thresholds are wrong.

---

## Design Constraints (Important)

- **Not real-time streaming** → interval-based by design
- **LLM calls are expensive** → aggressively throttled so use only when you needed to check something.
- **OCR is noisy** → system relies on aggregation, not single frames
- **Privacy-first assumption** → nothing leaves your machine except prompts

If you try to turn this into a continuous surveillance system, you'll break both cost and signal quality.

---

## What This Is NOT

- Not a keylogger
- Not spyware
- Not a generic "AI assistant"
- Not production-hardened for enterprise deployment

It's a **foundation system** for building workflow intelligence. where its logs your activities and give insight on your behavioral process.

---

## Where This Can Go (If You Push It)

If you extend this properly, you get:

- Long-term behavioral modeling
- Productivity scoring systems
- Autonomous workflow suggestions
- Context-aware automation triggers

Most people won't build that far. That's where the leverage is.

---

## License

Private / Internal use.
