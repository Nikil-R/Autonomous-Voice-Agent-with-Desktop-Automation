"""ApexCore Core Module."""

from core.config import (
    INPUT_SAMPLE_RATE,
    OUTPUT_SAMPLE_RATE,
    CHUNK_SIZE,
    CHUNK_DURATION_MS,
    DTYPE,
    TTS_VOICE,
    VAD_MODEL_PATH,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    GROQ_WHISPER_MODEL,
    GROQ_LLM_MODEL,
    DB_PATH,
    SCHEMA_PATH,
)
from core.state import ConversationState
from core.telemetry import TelemetryProfiler

__all__ = [
    "INPUT_SAMPLE_RATE",
    "OUTPUT_SAMPLE_RATE",
    "CHUNK_SIZE",
    "CHUNK_DURATION_MS",
    "DTYPE",
    "TTS_VOICE",
    "VAD_MODEL_PATH",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_WHISPER_MODEL",
    "GROQ_LLM_MODEL",
    "DB_PATH",
    "SCHEMA_PATH",
    "ConversationState",
    "TelemetryProfiler",
]
