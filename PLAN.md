# 🚀 ApexCore: Voice-Activated OS Automation & Database Intelligence Agent
### Production Architectural Specification & Comprehensive Implementation Plan

**ApexCore** is an asynchronous, full-duplex Voice AI desktop agent designed to provide hands-free operating system telemetry, automated local task execution, and real-time database intelligence. 

It synthesizes **every single theoretical and practical module** from [VOICE_AGENT_NOTES.md](file:///C:/Users/nikil/OneDrive/Desktop/Voice%20Practise/VOICE_AGENT_NOTES.md):
- Digital audio PCM buffers (16kHz / 24kHz)
- Neural Silero VAD turn-taking with dynamic silence timeouts
- In-memory RAM audio packaging (.wav BytesIO)
- Sub-500ms TTFA token-to-sentence streaming
- Real-time Barge-In cancellation with context history reconciliation
- Acoustic Echo Cancellation (AEC) & feedback protection
- Jitter buffer audio pacing
- ACID SQLite transactions in WAL mode
- Millisecond latency telemetry profiler
- Live comparative benchmark: Cascade Pipeline vs Native Multimodal

---

## 🎯 Master System Architecture

```mermaid
flowchart TD
    subgraph 1. Audio Ingestion & Digital Signal Processing
        MIC[16kHz Mono PCM Mic Stream - sounddevice] --> VAD[Silero VAD ONNX Engine]
        VAD -->|Recurrent State Tracking| ENDPOINT[Turn Endpointing: 500ms Silence]
        SPEAKER_REF[Active Speaker Reference Signal] -.->|AEC Subtraction & Echo Suppression| MIC
    end

    subgraph 2. Recognition & Cognitive Core
        ENDPOINT --> STT[Whisper Large v3 Turbo via Groq LPU]
        STT -->|Transcript| BRAIN[Async ReAct Loop - Qwen 2.5 / Llama 3.3]
        BRAIN <-->|Strict JSON Tool Dispatch| TOOLS[Tool Dispatch Engine]
        TOOLS <-->|OS Vitals & Process Control| OS_LAYER[Local OS: psutil / subprocess]
        TOOLS <-->|SQL Queries & WAL Transactions| DB[(Local SQLite WAL Database)]
    end

    subgraph 3. Low-Latency Streaming Pipeline (TTFA Optimization)
        BRAIN -->|Token Stream Generator| CHUNKER[Adaptive Sentence Chunker]
        CHUNKER -->|Punctuation Boundary: Sentence #1| TTS[Edge-TTS Streaming Engine]
    end

    subgraph 4. Playback, Jitter Smoothing & Barge-In Cancellation
        TTS --> JITTER[Jitter Buffer Queue]
        JITTER --> PLAY[Async Speaker Worker - sounddevice]
        MIC -.->|VAD Detects User Voice During Playback| BARGE[Barge-In Engine]
        BARGE -->|1. Flush Jitter Buffer| PLAY
        BARGE -->|2. Cancel Tasks in <5ms| BRAIN
        BARGE -->|3. Reconcile Context History| BRAIN
    end

    subgraph 5. Real-Time Telemetry Profiler
        VAD -.->|VAD Endpointing: ~400ms| TELEMETRY[Live Telemetry Logger]
        STT -.->|STT Latency: ~140ms| TELEMETRY
        BRAIN -.->|TTFT: ~110ms| TELEMETRY
        TTS -.->|TTFA: <500ms| TELEMETRY
    end
---

## 🏆 Why This Plan Truly Puts You in the Top 1% of Applicants

Most candidates put on their resume: *"Built an AI voice assistant with LangChain/Vapi."*
A hiring manager knows that took 1 afternoon following a tutorial.

Here is why **ApexCore** is a **Top 1% engineering showcase**:
1. **Zero Framework Dependencies:** You didn't hide behind LangChain, Vapi, or LiveKit for the core loop. You wrote the asynchronous event-driven loop in pure Python.
2. **Hard Millisecond Performance Metrics:** You don't claim it's "fast"—you measure it live with built-in telemetry:
   - **VAD Inference:** $<1.0\text{ms}$ on CPU
   - **STT Transcription:** $\approx 140\text{ms}$ (Whisper LPU)
   - **TTFT (Time-to-First-Token):** $\approx 110\text{ms}$ (Groq LPU)
   - **TTFA (Time-to-First-Audio):** $<500\text{ms}$ (Sentence Chunker)
3. **Hardware-to-Database Concurrency:** Combines physical audio stream buffers with operating system inspection (`psutil`) and transactional database persistence (`SQLite WAL`).
4. **Resilience to Failure:** Implements real-time barge-in cancellation and acoustic echo protection so the bot never loops on its own audio.

---

## 🛠️ The Complete Technology Stack

| Layer | Technology / Library | Exact Version / Spec | Purpose in ApexCore |
| :--- | :--- | :--- | :--- |
| **Language & Concurrency** | **Python 3.11+ / 3.14** | `asyncio`, `threading` | Asynchronous non-blocking event loop, task scheduling & cancellation |
| **Audio I/O & Hardware** | **`sounddevice`** | `v0.5.6+` (PortAudio C binding) | Non-blocking input/output audio streaming, ring buffers, sample rate conversion |
| **Vector & Audio Math** | **`numpy`** | `v2.5+` | Real-time PCM waveform arrays, RMS energy computation, format normalization |
| **Turn-Taking & VAD** | **`onnxruntime` + Silero VAD** | Silero VAD v5 ONNX (~2.3MB) | Sub-millisecond neural voice activity detection & silence hangover endpointing |
| **In-Memory Audio Packaging** | **`io.BytesIO` + `wave`** | Python Standard Library | Zero-disk RAM WAV packaging for ultra-fast STT transmission |
| **Speech-to-Text (STT)** | **Groq Whisper Large v3 Turbo** | `groq-python` SDK | LPU-accelerated speech-to-text with ~140ms transcription latency |
| **Cognitive Agent Brain** | **Qwen 2.5 70B / Llama 3.3** via Groq | Groq Cloud API | Autonomous ReAct reasoning loop, JSON Schema function calling, tool dispatch |
| **Streaming Text-to-Speech** | **`edge-tts`** | Microsoft Azure Neural | Asynchronous WebSocket neural voice synthesis without API keys or costs |
| **Audio File Decoding** | **`soundfile`** | `libsndfile` C wrapper | In-memory decoding of compressed MP3/WAV chunks into float32 PCM arrays |
| **OS Automation & Telemetry** | **`psutil`** | `v5.9+` | Local CPU load, RAM usage, process enumeration, disk free space, battery |
| **Process Execution** | **`subprocess` + `os`** | Python Standard Library | Safe local application launching (Calculator, Notepad, VS Code) |
| **Database Engine** | **SQLite 3 (WAL Mode)** | `PRAGMA journal_mode=WAL` | High-concurrency ACID transactions, audit logs, and SQL analytics |
| **Environment & Secrets** | **`python-dotenv`** | `v1.2+` | Secure `.env` credential management (API keys) |
| **Testing & Quality** | **`pytest` + `pytest-asyncio`** | Standard testing suite | Automated unit tests for tools, database WAL, and sentence chunker |

---

## 📋 Comprehensive Concept Matrix: How Every Note Module is Implemented

| Module from Revision Notes | Implementation in ApexCore | Engineering Impact & Portfolio Highlight |
| :--- | :--- | :--- |
| **Module 1: ReAct Agent Loop** | Pure Python ReAct while-loop (`services/brain.py`), strict JSON Schema parameter validation, `tool_call_id` mapping. | No black-box frameworks; total control over agent reasoning. |
| **Module 2: Digital Audio Physics** | 16,000 Hz input, 24,000 Hz output, mono channels, 16-bit PCM (`int16`), 512-sample (32ms) chunk buffers, RMS calculation. | Shows deep understanding of audio hardware drivers and signal math. |
| **Module 3: Neural Silero VAD** | `services/vad.py` wraps `models/silero_vad.onnx` with recurrent hidden state tensor `(2, 1, 64)`. Automatically detects speech start and triggers turn completion on 500ms silence. | Replaces amateur hardcoded sleep timers with neural turn-taking. |
| **Module 4: In-Memory STT** | `services/stt.py` converts raw PCM into standard WAV bytes in RAM via `io.BytesIO()`. Transcribes in ~140ms using Groq Whisper Large v3 Turbo. | Zero disk I/O latency; leaves no temporary audio junk files. |
| **Module 5: Streaming TTS** | `services/tts.py` streams neural speech packets via Edge-TTS over WebSockets, accumulating in memory and playing via sounddevice. | Broadcast-grade human voice quality without paid API keys. |
| **Module 6: Conversational Memory** | `core/state.py` maintains multi-turn session history. Remembers previously inspected processes, files, or SQL results. | True multi-turn continuity across commands. |
| **Module 7: Modular SRP Architecture** | Single Responsibility Principle across `core/`, `database/`, `tools/`, `services/`, and `pipeline/`. | Enterprise code structure ready for GitHub and peer review. |
| **Module 8: TTFA Sentence Chunking** | `pipeline/chunker.py` uses regex punctuation boundary matching (`.`, `?`, `!`, `;`) to stream Sentence #1 to TTS while Sentence #2 is still generating. | Directly optimizes **Time-to-First-Audio (TTFA)** to $<500\text{ms}$. |
| **Module 8: Real-Time Barge-In** | When VAD fires while speaker output is active, `pipeline/orchestrator.py` cancels generation tasks in $<5\text{ms}$, flushes the speaker queue, and reconciles context history. | Natural human interruption handling; the bot immediately stops talking. |
| **Module 8: Echo & Feedback Suppression** | Software reference gating: drops or suppresses microphone frames while the speaker is outputting sound unless speech probability crosses a high interruption threshold. | Prevents self-triggering audio feedback loops. |
| **Module 8: Jitter Buffering** | Smooths out network arrival fluctuations with a 40ms audio queue, preventing audio buffer underruns and robotic stuttering. | Professional audio stream stability. |
| **Module 9: High-Concurrency SQL** | SQLite configured in **WAL mode** (`PRAGMA journal_mode=WAL`) with foreign keys and unique constraints. | Real ACID database operations without database lock timeouts. |
| **Module 9 & Telemetry Profiler** | `core/telemetry.py` logs real-time millisecond metrics on every turn: VAD delay, STT latency, TTFT, TTFA, and Barge-In events. | Provides hard benchmark evidence for your README and interviews. |
| **Dual Engine Benchmark Suite** | Includes `benchmarks/compare_cascade_vs_multimodal.py` measuring round-trip latency, reliability, and trade-offs against Gemini Live. | Demonstrates senior evaluation ability between architectures. |

---

## 🗂️ Complete Directory & File Blueprint

```text
ApexCore/
│
├── .env                              # API keys (GROQ_API_KEY, GEMINI_API_KEY)
├── README.md                         # Top-tier GitHub README with architecture diagrams & benchmarks
├── run.py                            # CLI interactive entry point
│
├── core/
│   ├── __init__.py
│   ├── config.py                     # Audio settings (16kHz, chunk size), model IDs, voice settings
│   ├── state.py                      # Multi-turn conversational memory & context reconciliation
│   └── telemetry.py                  # Real-time millisecond latency profiler (TTFA, STT, TTFT)
│
├── database/
│   ├── __init__.py
│   ├── schema.sql                    # System metrics history & audit event tables
│   └── db.py                         # SQLite engine in WAL mode with connection management
│
├── tools/
│   ├── __init__.py                   # Tool registry & dispatch dictionary
│   ├── schemas.py                    # OpenAI/Groq function calling JSON schemas
│   ├── system_tools.py               # get_system_vitals(), get_top_processes()
│   ├── file_tools.py                 # search_files(), organize_folder()
│   └── db_tools.py                   # query_local_db(), insert_audit_event()
│
├── services/
│   ├── __init__.py
│   ├── vad.py                        # Silero VAD ONNX engine wrapper (recurrent state tracking)
│   ├── stt.py                        # Whisper Large v3 Turbo in-memory WAV transcription
│   ├── tts.py                        # Edge-TTS streaming synthesis service
│   └── brain.py                      # Async ReAct loop with streaming token output & tool execution
│
├── pipeline/
│   ├── __init__.py
│   ├── chunker.py                    # Adaptive sentence boundary chunker (TTFA optimizer)
│   └── orchestrator.py               # Master full-duplex loop: VAD -> STT -> Brain -> TTS + Barge-In + AEC
│
└── benchmarks/
    ├── __init__.py
    └── compare_engines.py            # Latency & accuracy benchmark: Cascade vs Multimodal Live
```

---

## 🛠️ The 5 Core Tools Exposed to the Agent

### 1. `get_system_vitals()`
* **Implementation:** `psutil.cpu_percent()`, `psutil.virtual_memory()`, `shutil.disk_usage()`, `psutil.sensors_battery()`.
* **Returns:** CPU load %, RAM utilized vs free (GB), disk free space on Drive C (GB), battery percentage.

### 2. `get_top_processes(sort_by="memory", count=5)`
* **Implementation:** Iterates over running Windows processes via `psutil.process_iter()`, sorts by resident memory or CPU, filters out system idle.
* **Returns:** List of top 5 consuming apps with PIDs, names, and RAM in megabytes.

### 3. `search_files(directory, extension=None, keyword=None)`
* **Implementation:** Safe recursive scanning of target user folders (Desktop, Downloads, Documents) with path sanitization preventing directory traversal.
* **Returns:** Matched filenames, sizes, and file counts.

### 4. `query_local_db(sql_query)`
* **Implementation:** Executes read-only SQL aggregation against the local SQLite database in WAL mode.
* **Returns:** Formatted query result rows or aggregation counts.

### 5. `open_application(app_name)`
* **Implementation:** Launches desktop applications safely (Calculator, Notepad, VS Code) using `subprocess.Popen` without freezing the main event loop.
* **Returns:** Confirmation status and launched application name.

---

## 💬 Live Multi-Turn Dialogue & Interruption Walkthrough

### 🗣️ Turn 1: System Vitals & Low-Latency TTFA
* **User speaks:** *"Apex, how is my laptop running right now and what is my free disk space on Drive C?"*
* **Telemetry trace:**
  - VAD Endpointing Delay: `410ms`
  - STT Transcription (Whisper): `138ms`
  - LLM First Token (Groq): `112ms`
  - Sentence Chunker pipes sentence #1 directly to Edge-TTS: **TTFA = 465ms!**
* **ApexCore speaks:** *"Your CPU is at 14 percent, RAM is at 58 percent, and you have 138 gigabytes free on Drive C."*

### 🗣️ Turn 2: Database Query
* **User speaks:** *"Query the database: what was our highest recorded CPU load today?"*
* **Under the Hood:**
  - Brain generates SQL: `SELECT max(cpu_percent), recorded_at FROM system_telemetry WHERE date(recorded_at) = date('now');`
  - Executes safely against SQLite WAL database.
* **ApexCore speaks:** *"The peak CPU load today was 82 percent recorded at 2:15 PM."*

### 🗣️ Turn 3: The Showstopper — Self-Correction & Real-Time Barge-In
* **User speaks:** *"List the top memory consuming applications on my system."*
* **ApexCore begins speaking:** *"The top applications are Google Chrome using 1.4 gigabytes, Visual Studio Code using 850 megabytes..."*
* **User interrupts loudly:** *"Wait, cancel that! Open Calculator instead."*
* **Barge-In Orchestration in $<5\text{ms}$:**
  1. VAD detects user voice during active playback.
  2. Orchestrator flushes speaker jitter buffer immediately (sound stops mid-word).
  3. `asyncio.Task.cancel()` terminates running TTS and LLM generation streams.
  4. Context reconciler trims un-spoken words from conversation history.
  5. Collects new user utterance: *"Open Calculator instead."*
  6. Brain executes `open_application(app_name="calc")`.
* **ApexCore speaks:** *"Understood. Calculator is opened."*

---

## 🧪 Comprehensive Verification & Testing Suite

1. **Automated Unit Tests (`pytest`):**
   - `test_os_tools.py`: Tests `psutil` vital extractions and process sorting.
   - `test_db.py`: Tests SQLite WAL mode concurrency and SQL query safety.
   - `test_sentence_chunker.py`: Simulates streamed token generator; verifies chunker outputs clean sentences on punctuation boundaries.
2. **Automated Pipeline Latency Test:**
   - Runs simulated audio through VAD, STT, and Brain, asserting that TTFA stays under 600ms.
3. **Manual Voice Verification:**
   - Test hands-free turn taking without pressing any keys.
   - Test speaking over the bot mid-sentence to verify instant barge-in cut-off.
   - Check terminal output for the real-time latency telemetry report on every turn.
