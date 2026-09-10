# Sorachio-STS

**Speech To Speech AI Companion & Agentic Robotics System**  
*Local-first, real-time voice AI companion powered by dual-LLM cognition, wake word detection, action engine, and SBC/ESP32 robotics architecture*

---

### System in Action (CLI Showcase)

Here is a preview of how the interactive CLI behaves in voice mode, showcasing the real-time **Cognitive Gateway Action Badges**, **Wake Word State Machine**, and state transitions.

#### 1. Full Voice/Run Mode (`python main.py run`)
In voice mode, the pipeline continuously monitors microphone input in **IDLE Mode** for wake word activation (`alexa`, `hey_jarvis`, `hey_mycroft`, or custom `hey_sorachio.onnx`). Upon detection, Sorachio emits an instant audio response ("Hey there!", "I'm listening!", "Hello!"), transitions to **ACTIVE Mode**, processes speech via STT, and uses LLM1 as an **Agentic Action Planner** to execute physical movements or web searches before routing to LLM2.

![Sorachio-STS Voice Mode](docs/ss-run.png)

#### 2. Interactive Text Mode (`python main.py text`)
In text mode, you can chat with the companion using keyboard inputs. Perfect for testing prompts, observing Cognitive Gateway JSON action decisions, and validating tool dispatching without a microphone.

![Sorachio-STS Text Mode](docs/ss-txt.png)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Data Flow](#3-data-flow)
4. [Folder Structure](#4-folder-structure)
5. [Threading & State Model](#5-threading--state-model)
6. [Installation](#6-installation)
7. [Model Setup](#7-model-setup)
8. [Wake Word & ONNX Models](#8-wake-word--onnx-models)
9. [Agentic Action Engine & Robotics](#9-agentic-action-engine--robotics)
10. [Running the System](#10-running-the-system)
11. [Configuration Guide](#11-configuration-guide)
12. [Cognitive Gateway & Action Planning](#12-cognitive-gateway--action-planning)
13. [Acoustic Intelligence Layer](#13-acoustic-intelligence-layer)
14. [Bilingual Language Routing](#14-bilingual-language-routing)
15. [Streaming Pipeline Explained](#15-streaming-pipeline-explained)
16. [Memory Architecture](#16-memory-architecture)
17. [CLI Reference](#17-cli-reference)
18. [MBG System](#18-mbg-system)
19. [Troubleshooting](#19-troubleshooting)
20. [Future Robotics Expansion & ESP32 Hardware](#20-future-robotics-expansion--esp32-hardware)

---

## 1. Project Overview

Sorachio-STS is a **complete, local-first, real-time Speech-to-Speech (STS) AI Companion & Autonomous Agent** system. It runs entirely on your local machine / SBC — no cloud APIs, no subscriptions, no data sent anywhere.

The system is designed from the ground up as a **scalable AI companion operating system** — with architecture that anticipates future expansion into robotics (Orange Pi 5 Pro 16GB + ESP32 actuators), multi-agent systems, cameras, sensors, and ROS2 integration.

### Key Properties

| Property | Detail |
|----------|--------|
| **Fully Local** | All inference runs on-device via llama.cpp + openwakeword + faster-whisper + Kokoro TTS / Piper TTS |
| **Real-Time Streaming** | TTS begins before LLM finishes generating |
| **Wake Word Engine** | OpenWakeWord detector (`alexa`, `hey_jarvis`, `hey_mycroft`, custom ONNX scanning) with state machine |
| **Instant Wake Response** | Zero-latency instant audio confirmation ("Hey there!", "I'm listening!", "Hello!") on wake trigger |
| **Two-LLM Architecture** | Agentic Action Planner (LLM #1) + Personality Core (LLM #2) |
| **Agentic Action Engine** | Autonomous function execution (`move`, `look`, `search`, `remember`, `multi`) via modular dispatcher |
| **Robotics Modular HAL** | Hardware Abstraction Layer with `MockRobotController` (laptop) and `ESP32RobotController` (Orange Pi + ESP32) |
| **Live Web Search** | Real-time instant web search via DuckDuckGo engine (`utils/web_search.py`) |
| **Model-Agnostic** | Auto-detects any GGUF model in `models/llm1/` and `models/llm2/` — drop & restart |
| **Vision Ready** | LLM #2 supports multimodal input via `mmproj` projector |
| **Bilingual** | Automatic English / Indonesian language detection & voice routing |
| **Interruptible** | VAD-based barge-in stops playback instantly; self-interrupt shielded |
| **Adaptive AEC** | Calibration-based room impulse response echo cancellation (3s chirp sweep + Wiener/LMS filter) |
| **Deep Buffer Reset** | OpenWakeWord preprocessor feature buffer clearing preventing ghost wake-word triggers |
| **Vector Memory** | ChromaDB semantic search + sentence-transformers embeddings for LTM |
| **Emotion Persistence** | Long-term mood trend detection and emotion pattern tracking |
| **Rich CLI UI** | Mode indicators, action status badges, transient spinners, and cognitive status pills |

### Current Model Configuration

| Slot | Model | Size | Role | Local Path |
|------|-------|------|------|------------|
| Wake Word | OpenWakeWord ONNX (`alexa`, `hey_jarvis`, etc.) | ~5 MB | Instant wake word detection | `models/wakeword/` |
| LLM #1 | Qwen2.5-Coder-0.5B-Instruct (Q8_0) | ~644 MB | Agentic Action Planner (JSON action router) | `models/llm1/` |
| LLM #2 | Qwen3.5-4B (Q4_K_M) | ~2.6 GB | Personality Core (conversation) + **Vision** | `models/llm2/` |
| STT | faster-whisper small | ~484 MB | Speech-to-Text (multilingual ID/EN) | `models/stt/` |
| TTS (EN) | Kokoro-82M (`af_heart`) | ~327 MB | English female voice — 24kHz native | `models/tts/kokoro/` |
| TTS (ID) | Piper `id_ID-news_tts-medium` | ~67 MB | Indonesian female voice — 22.05kHz→24kHz | `models/tts/` |
| Vector Embed | all-MiniLM-L6-v2 | ~90 MB | Semantic memory embeddings (offline) | `models/vector/all-MiniLM-L6-v2/` |

> **All model weights live inside the project** under `models/` — no cloud cache, no `~/.cache` writes. Everything is self-contained and portable.

---

## 2. Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            Sorachio-STS Pipeline                                  |
|                                                                                   |
|  +----------+    +-------------------------------------------+                    |
|  |Microphone|───>| Acoustic Gate (RMS/dBFS)                  |                    |
|  +----------+    +-------------------------------------------+                    |
|                                   |                                               |
|                                   v                                               |
|                  +-------------------------------------------+                    |
|                  | CalibrationAEC / SpectralSubAEC           |                    |
|                  | (3s chirp room calibration, Wiener/LMS)   |                    |
|                  +-------------------------------------------+                    |
|                                   |                                               |
|                                   v                                               |
|                  +-------------------------------------------+                    |
|                  | AudioCapture State Machine                |                    |
|                  | (IDLE vs ACTIVE + 2.5s Cooldown Guard)     |                    |
|                  +--------------------+----------------------+                    |
|                                       |                                           |
|            +--------------------------+--------------------------+                |
|            | IDLE Mode                                           | ACTIVE Mode    |
|            v                                                     v                |
|  +-------------------+                                   +---------------+        |
|  | WakeWordDetector  |                                   |  STT Queue     |        |
|  | (openwakeword)    |                                   | (asyncio)     |        |
|  +---------+---------+                                   +-------+-------+        |
|            | Trigger detected                                    |                |
|            v                                                     v                |
|  +-------------------+                                   +---------------+        |
|  | Instant TTS Audio |                                   | STT Worker    |        |
|  | ("Hey there!")    |                                   | (Whisper)     |        |
|  +-------------------+                                   +-------+-------+        |
|                                                                  | transcript     |
|                                                                  v                |
|                                                          +---------------+        |
|                                                          | ActionPlanner |        |
|                                                          | (LLM #1)      |        |
|                                                          +-------+-------+        |
|                                                                  | JSON action    |
|                                                                  v                |
|                                                          +---------------+        |
|                                                          | Action        |        |
|                                                          | Dispatcher    |        |
|                                                          +--+---+---+----+        |
|                                                             |   |   |             |
|                                      +----------------------+   |   +------+      |
|                                      |                          |          |      |
|                                      v                          v          v      |
|                            +-------------------+          +----------+ +----+     |
|                            | Actuators (HAL)   |          | WebSearch| |LTM |     |
|                            | Mock / ESP32      |          | (DuckDuck| |Vector    |
|                            | (Move/Look)       |          |  Go)     | |Memory    |
|                            +-------------------+          +----------+ +----+     |
|                                                                            |      |
|                                                                            v      |
|                                                          +---------------+        |
|                                                          | Personality   |        |
|                                                          | Worker        |        |
|                                                          | (LLM #2)      |        |
|                                                          +-------+-------+        |
|                                                                  | stream         |
|                                                                  v                |
|                                                          +---------------+        |
|                                                          | Hybrid TTS    |        |
|                                                          | Kokoro / Piper|        |
|                                                          +-------+-------+        |
|                                                                  | audio          |
|                                                                  v                |
|                                                              +-------+            |
|                                                              |Speaker|            |
|                                                              +-------+            |
+-----------------------------------------------------------------------------------+
```

---

## 3. Data Flow

```
[User speaks wake word: "Alexa" / "Hey Jarvis"]
    |
    v PCM bytes (16kHz, 16-bit mono)
[WakeWordDetector (OpenWakeWord)] -- confidence >= 0.50
    |
    +--> Plays Instant Confirmation ("Hey there!", "I'm listening!", "Hello!")
    +--> State transition: IDLE -> ACTIVE (15-second activity window)
    +--> Deep reset preprocessor buffers to prevent ghost triggers
    |
[User speaks command: "Turn left and search python news"]
    |
[Acoustic Gate & AEC] -- drops noise, cancels room echo
    |
[STT Worker: faster-whisper] -- transcribes audio to text transcript
    |
[Agentic Action Planner: LLM #1]
    |  JSON decision:
    |  {
    |    "action": "multi",
    |    "actions": [
    |      {"action": "move", "direction": "left", "angle_deg": 90},
    |      {"action": "search", "query": "python news"},
    |      {"action": "conversation"}
    |    ]
    |  }
    |
[Action Dispatcher]
    |--> RobotController (Mock / ESP32 over HTTP/Serial) -> Executes rotation
    |--> WebSearchEngine (DuckDuckGo) -> Fetches web snippets
    |--> Memory System & Emotion Tracker -> Injects context + search results
    |
[Context Manager & LLM #2 Personality Core]
    |  Generates natural speech output enriched with search & sensory context
    |
[Hybrid TTS Client (Kokoro / Piper)] -> Speaker
```

---

## 4. Folder Structure

```
Sorachio-STS/
|
+-- main.py                 # Entry point (MBG runs automatically)
+-- mbg.py                  # Master Bootstrap Guardian + Anteque Ashing quality checks
+-- pyproject.toml          # Ruff + pyrefly configuration
+-- README.md
|
+-- config/
|   +-- sorachio.yaml       # Master config (edit this!)
|   +-- settings.py         # Pydantic settings loader + model auto-scanner
|
+-- core/
|   +-- pipeline.py         # Master async pipeline (wake word callback, action dispatch)
|   +-- events.py           # Event bus (pub/sub)
|
+-- audio/
|   +-- capture.py          # Mic capture + VAD + wake word state machine + deep reset
|   +-- playback.py         # Interruptible playback queue
|   +-- wakeword.py         # OpenWakeWord wrapper + deep feature buffer clearing
|   +-- acoustic_gate.py    # Pre-VAD energy filter + silence sentinel injection
|   +-- echo_cancellation.py # CalibrationAEC (3s chirp sweep) + SpectralSubAEC + NullAEC
|
+-- actuators/
|   +-- robot_controller.py # Robot Hardware Abstraction Layer (Mock & ESP32 HTTP/Serial)
|
+-- cognition/
|   +-- cognitive_gateway.py  # Agentic Action Planner (JSON schema schema builder)
|   +-- action_dispatcher.py  # Action dispatcher (actuators, search, memory, LLM2)
|
+-- utils/
|   +-- web_search.py       # DuckDuckGo instant web search engine
|   +-- logging_setup.py    # Structured logging (Rich + file)
|   +-- chunk_assembler.py  # Token -> speech chunk converter
|   +-- rate_limiter.py     # Sliding window rate limiter
|
+-- vision/
|   +-- capture.py          # Webcam snapshot capture (OpenCV)
|
+-- stt/
|   +-- whisper_client.py   # faster-whisper in-process client
|
+-- tts/
|   +-- kokoro_client.py    # Hybrid Kokoro & Piper TTS client
|   +-- piper_client.py     # Piper ONNX fallback client (Indonesian TTS engine)
|
+-- llm/
|   +-- llama_client.py     # Async llama-server client (multimodal ready)
|   +-- model_scanner.py    # Auto-detect GGUF models + mmproj
|
+-- context/
|   +-- context_manager.py  # Prompt assembly + per-turn language directive injection
|
+-- memory/
|   +-- short_term.py       # Rolling conversation window
|   +-- long_term.py        # Hybrid LTM: JSON persistent storage + VectorStore integration
|   +-- vector_store.py     # ChromaDB vector store + sentence-transformers (all-MiniLM-L6-v2)
|   +-- emotion_tracker.py  # Rolling emotion history & mood trend detection
|
+-- personality/
|   +-- personality_core.py # Streaming conversation engine
|
+-- services/
|   +-- server_manager.py   # llama-server lifecycle
|
+-- cli/
|   +-- main.py             # Rich CLI UI (mode spinners, status badges)
|
+-- models/
|   +-- wakeword/           # OpenWakeWord ONNX models (.onnx + README)
|   +-- llm1/               # Drop any GGUF here for LLM1 Action Planner
|   +-- llm2/               # Drop any GGUF + optional mmproj here for LLM2 Personality
|   +-- stt/                # faster-whisper weights (auto-downloaded by MBG)
|   +-- tts/                # Piper & Kokoro TTS weights (auto-downloaded by MBG)
|   +-- vector/             # sentence-transformers embeddings (auto-downloaded by MBG)
|
+-- bin/
|   +-- llama-server        # llama-server binary (Vulkan support)
|
+-- data/
|   +-- memory/             # ltm.json + ChromaDB vector embeddings
|
+-- logs/                   # Log outputs
+-- venv_runtime/           # Managed virtual environment
```

---

## 5. Threading & State Model

```
Main Thread (asyncio event loop)
|
+-- [asyncio Task] Pipeline Loop        -- manages STT, Action Dispatcher, LLM2, TTS
+-- [asyncio Task] Cognitive Worker     -- LLM #1 Action Planner (JSON generation)
+-- [asyncio Task] Action Dispatcher    -- routes physical moves, web search & memory
+-- [asyncio Task] Personality Worker   -- LLM #2 streaming speech output
+-- [asyncio Task] TTS Worker           -- Kokoro/Piper audio synthesis
|
+-- [Thread] VAD & WakeWord Worker      -- audio capture loop
|   +-- Mode: IDLE   --> passes PCM to OpenWakeWord detector
|   +-- Mode: ACTIVE --> passes PCM to webrtcvad & STT queue
|
+-- [Thread Executor] Blocking ONNX/CTranslate2 (Whisper, Piper, OpenWakeWord)
```

---

## 6. Installation

### Path A — Linux / macOS (Recommended)

#### Step 1 — Install Prerequisites

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv git cmake build-essential libportaudio2
```

**Fedora / RHEL:**
```bash
sudo dnf install -y python3.12 git cmake gcc gcc-c++ portaudio-devel
```

#### Step 2 — Clone and Run

```bash
git clone https://github.com/izzulgod/sorachio-sts.git
cd sorachio-sts
python main.py run
```

MBG handles everything automatically:
- Creates `venv_runtime/` virtual environment
- Installs Python packages + Anteque Ashing verification (`ruff` + `pyrefly`)
- Compiles `llama.cpp` binary into `bin/` with Vulkan GPU acceleration
- Auto-downloads STT (Whisper), TTS (Kokoro/Piper), and Vector Embedding models

---

## 7. Model Setup

### Swapping LLM Models (Drop & Go)

1. **Download** any GGUF model from Hugging Face.
2. **Place GGUF files**:
   - `models/llm1/`: Cognitive Gateway Action Planner (recommended: `qwen2.5-coder-0.5b-instruct-q8_0.gguf`)
   - `models/llm2/`: Personality Core + Vision (recommended: `Qwen3.5-4B-Q4_K_M.gguf` + `mmproj-BF16.gguf`)
3. **Restart**: `python main.py run` (auto-detected!).

---

## 8. Wake Word & ONNX Models

Sorachio-STS uses **OpenWakeWord** for real-time wake word detection.

### Supported Wake Words Out-of-the-Box
- `alexa`
- `hey_jarvis`
- `hey_mycroft`

### Custom Wake Word Models (`hey_sorachio.onnx`)
Place custom OpenWakeWord `.onnx` models inside `models/wakeword/`:
```
models/wakeword/
+-- hey_sorachio.onnx
+-- README.md
```
Sorachio automatically scans `models/wakeword/*.onnx` on startup and activates custom wake words alongside built-in models!

### OpenWakeWord Deep Reset Mechanism
Standard OpenWakeWord `reset()` only clears score dictionaries. Sorachio implements a **Deep Reset** inside `WakeWordDetector.reset()` that zeroes out `raw_data_buffer`, `feature_buffer` `(116, 96)`, and `melspectrogram_buffer` `(76, 32)` to guarantee **zero ghost re-triggers** after active timeout.

---

## 9. Agentic Action Engine & Robotics

LLM #1 (Cognitive Gateway) acts as an **Agentic Action Planner**. Instead of producing conversational text, it emits a structured JSON action plan.

### JSON Action Schema
```json
{
  "action": "multi",
  "actions": [
    {
      "action": "move",
      "direction": "forward",
      "distance_cm": 50,
      "speed": 0.8
    },
    {
      "action": "search",
      "query": "cuaca hari ini"
    },
    {
      "action": "conversation"
    }
  ]
}
```

### Action Types & Handlers

| Action | Payload Parameters | Execution Handler |
|--------|-------------------|-------------------|
| `move` | `direction` (`forward`/`backward`/`left`/`right`), `distance_cm`, `angle_deg`, `speed` | `RobotController.move()` / `rotate()` |
| `look` | `direction` (`up`/`down`/`left`/`right`), `angle_deg` | `RobotController.look()` |
| `search` | `query` | `WebSearchEngine.search()` (DuckDuckGo snippets injected into LLM2) |
| `remember` | `fact`, `importance` | `LongTermMemory.store()` (JSON + ChromaDB) |
| `multi` | `actions: [...]` | Sequential execution of multiple tool calls |
| `conversation` | N/A | Default pass-through to LLM2 streaming |

---

## 10. Running the System

```bash
# Full voice mode (Wake Word + Action Engine + STT + Dual LLM + TTS)
python main.py run

# Interactive text mode (keyboard interface for prompt testing)
python main.py text

# Single query text mode
python main.py text --message "search python news"

# Component testing
python main.py test-stt
python main.py test-tts "Testing Kokoro TTS"
python main.py test-cognitive "Turn left and search weather"

# System status check
python mbg.py --check
```

---

## 11. Configuration Guide

All master configurations live in `config/sorachio.yaml`.

```yaml
# Wake Word Configuration
wakeword:
  enabled: true
  target_words: ["hey_sorachio", "alexa", "hey_jarvis", "hey_mycroft"]
  threshold: 0.50
  active_timeout_s: 15.0
  confirmation_sound: true
  model_dir: "models/wakeword"

# Robotics HAL Configuration
robot:
  controller_type: "mock"    # "mock" for laptop dev, "esp32" for production SBC + ESP32
  esp32_url: "http://192.168.1.100"
  serial_port: "/dev/ttyUSB0"
  baud_rate: 115200

# STT & Acoustic Settings
stt:
  model_size: "small"
  language: "auto"

audio:
  capture:
    sample_rate: 16000
    chunk_duration_ms: 30
    acoustic_gate:
      threshold_dbfs: -40.0
      enabled: true

# Memory & Vector Store
memory:
  long_term:
    use_vector_store: true
    vector_store_path: "data/memory/chroma"
```

---

## 12. Cognitive Gateway & Action Planning

LLM #1 is optimized for ultra-fast JSON decisions (<300ms latency).

### Example Terminal Status Badges

When LLM #1 issues action decisions, the Rich CLI displays dynamic status pills:

```
  >>> STATUS   ◕ happy      ✓ respond      ⚡ move: forward      ⚡ search      ○ memory       topic: robotics
```

---

## 13. Acoustic Intelligence Layer

1. **Acoustic Gate**: Drops audio frames below `-40.0 dBFS` to save compute.
2. **Pre-Trigger Ring Buffer**: 8-frame (~240ms) onset buffer preserves initial word consonants.
3. **Playback Gate Shield**: Dynamically raises gate threshold to `max(-15.0 dBFS, speaker_peak + 7.0 dB)` during TTS playback to prevent self-interruption.
4. **CalibrationAEC**: 3-second chirp room impulse calibration with LMS/Wiener filtering.

---

## 14. Bilingual Language Routing

1. **Audio Language Classifier**: faster-whisper probabilities with 3x Indonesian bias correction.
2. **Text-Level Verification**: `_verify_text_language()` checks text tokens to resolve Whisper "In-" word misclassifications.
3. **Per-Turn Directive**: Context Manager injects explicit `[Spoken Language: English / Indonesian]` prompt directives.
4. **Hybrid Voice Engine**:
   - English text -> Kokoro TTS (`af_heart`, 24kHz)
   - Indonesian text -> Piper TTS (`id_ID-news_tts-medium`, 22.05kHz -> 24kHz resampled)

---

## 15. Streaming Pipeline Explained

```
LLM #2 output:  "Hello " -> "there! " -> "I " -> "am " -> "ready."
                      |                          |
Chunk Assembler:   ["Hello there!"]           ["I am ready."]
                      |                          |
TTS Engine:        Synthesizing chunk 1       Synthesizing chunk 2
                      |                          |
Audio Playback:    Playing chunk 1 ---------> Playing chunk 2
```

First audio chunk is played within **0.5 – 1.2 seconds**.

---

## 16. Memory Architecture

- **Short-Term Memory (STM)**: Rolling 20-message in-memory deque.
- **Long-Term Memory (LTM)**: Persistent JSON fact database (`data/memory/ltm.json`).
- **Vector Store**: ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` semantic vector search.
- **Emotion Tracker**: Mood trend analysis and continuous personality adaptation.

---

## 17. CLI Reference

```bash
# Main Modes
python main.py run          # Voice Mode with Wake Word
python main.py text         # Keyboard CLI Mode

# MBG Management
python mbg.py --check       # System dependency check
python mbg.py --force       # Rebuild virtualenv & binaries
python mbg.py --models      # Download model weights only
```

---

## 18. MBG System

**MBG (Master Bootstrap Guardian)** automates system initialization:
- Python 3.10 – 3.12 environment verification & auto-relaunch
- Virtual environment creation (`venv_runtime/`)
- Quality Code Verification: Enforces `ruff check .` and `pyrefly check` on bootstrap (Anteque Ashing)
- Compiles `llama-server` with Vulkan GPU acceleration
- Auto-downloads faster-whisper, Kokoro, Piper, and all-MiniLM models

---

## 19. Troubleshooting

### Wake Word Ghost Re-triggering
Ensure `audio/wakeword.py` deep reset is active. Run `python main.py run` — `WakeWordDetector.reset()` clears all preprocessor buffers on active timeout.

### Active Timeout Too Fast
Active timeout countdown starts **after** TTS playback completes. If timeout occurs prematurely, check `capture.touch_active_time()` logs.

---

## 20. Future Robotics Expansion & ESP32 Hardware

Sorachio-STS is designed to run on a **Single Board Computer (Orange Pi 5 Pro 16GB)** connected to an **ESP32 microcontroller**:

```
+-------------------------------------------------------------+
|             Orange Pi 5 Pro (16GB RAM) - SBC                |
|                                                             |
|  - Sorachio-STS Main Runtime (Python 3.12)                  |
|  - llama-server (GGUF LLM1 & LLM2 with RKNN / NPU / Vulkan)  |
|  - OpenWakeWord + Whisper STT + Kokoro/Piper TTS            |
|  - Web Search & Vector Store                                |
+------------------------------+------------------------------+
                               |
                               | HTTP / Serial UART
                               v
+-------------------------------------------------------------+
|                   ESP32 Microcontroller                     |
|                                                             |
|  - Motor Drivers / Wheel Actuators (Rover Motion)           |
|  - Pan-Tilt Servo Head (Camera Tracking)                    |
|  - LED Ring Indicators (Emotional Mood Colors)              |
|  - Ultrasonic / ToF Distance Sensors                        |
+-------------------------------------------------------------+
```

### Hardware Abstraction Layer (HAL) Roadmap

- [x] `MockRobotController`: Software simulation for laptop development.
- [x] `ESP32RobotController`: HTTP/Serial JSON command protocol for ESP32 actuators.
- [ ] `sensors/camera.py`: Real-time camera frame provider for LLM2 vision.
- [ ] `actuators/led_ring.py`: WS2812B LED status ring controller.
- [ ] ROS2 Bridge (`core/ros2_bridge.py`): ROS2 node integration for navigation & SLAM.

---

## License

MIT License — see [LICENSE](LICENSE)

## Contributing

- Pull requests & issue reports welcome
- Hardware actuator drivers & ESP32 firmware contributions
- Custom wake word models (`models/wakeword/`)
- Vision & ROS2 integrations
