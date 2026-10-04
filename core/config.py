"""ApexCore Core Configuration and System Constants."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Audio Ingestion (Input Microphone)
INPUT_SAMPLE_RATE = 16000  # 16 kHz mono
CHANNELS = 1
CHUNK_DURATION_MS = 32     # 32 ms per frame
CHUNK_SIZE = int(INPUT_SAMPLE_RATE * (CHUNK_DURATION_MS / 1000.0))  # 512 samples
DTYPE = "int16"

# Audio Output (Speaker Playback)
OUTPUT_SAMPLE_RATE = 24000  # 24 kHz for high-fidelity speech
TTS_VOICE = "en-US-ChristopherNeural"  # Professional energetic neural voice

# Silero VAD Settings
VAD_MODEL_PATH = BASE_DIR / "models" / "silero_vad.onnx"
SPEECH_PROB_THRESHOLD = 0.55
INTERRUPT_PROB_THRESHOLD = 0.72  # Higher threshold when speaker is active (AEC gating)
SILENCE_DURATION_MS = 500         # 500ms trailing silence triggers turn end
SILENCE_FRAMES = int(SILENCE_DURATION_MS / CHUNK_DURATION_MS)

# Models
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
GROQ_LLM_MODEL = "qwen/qwen3.8-27b"

# Database Settings
DB_PATH = BASE_DIR / "database" / "apexcore.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
