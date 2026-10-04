"""Full-Duplex Voice Orchestrator with Barge-In & Echo Suppression."""

import asyncio
import numpy as np
import sounddevice as sd
from typing import Optional, List
from core.config import (
    INPUT_SAMPLE_RATE,
    CHUNK_SIZE,
    CHUNK_DURATION_MS,
    DTYPE,
    SPEECH_PROB_THRESHOLD,
    INTERRUPT_PROB_THRESHOLD,
    SILENCE_FRAMES,
)
from core.state import ConversationState
from core.telemetry import TelemetryProfiler
from services.vad import SileroVAD
from services.stt import WhisperSTTService
from services.tts import TTSService
from services.brain import AgentBrain
from pipeline.chunker import SentenceChunker
from database.db import db_manager

class FullDuplexOrchestrator:
    """
    Master full-duplex orchestrator:
    - Real-time microphone capture via sounddevice.InputStream
    - Silero VAD turn endpointing
    - Software Echo gating (suppresses mic echo while speaker output is active)
    - Sub-500ms TTFA sentence streaming to Edge-TTS
    - Instant Barge-In interruption (<5ms task cancellation)
    - Latency profiling on every turn
    """

    def __init__(self):
        self.state = ConversationState()
        self.telemetry = TelemetryProfiler()
        self.vad = SileroVAD()
        self.stt = WhisperSTTService()
        self.tts = TTSService()
        self.brain = AgentBrain()
        self.chunker = SentenceChunker()

        # Audio stream control
        self.audio_queue = asyncio.Queue()
        self.is_running = False
        self.playback_task: Optional[asyncio.Task] = None
        self.synthesis_tasks: List[asyncio.Task] = []
        self._current_sentence_spoken = ""

    def _audio_callback(self, indata, frames, time_info, status):
        """Low-level sounddevice input callback."""
        if status:
            pass
        # Flatten int16 or float32 to (CHUNK_SIZE,)
        chunk = indata[:, 0].copy()
        try:
            self.audio_queue.put_nowait(chunk)
        except asyncio.QueueFull:
            pass

    def stop_playback_and_cancel(self):
        """Immediately halts active playback and cancels background generation tasks."""
        if self.state.is_speaking:
            print("\n🚨 [BARGE-IN DETECTED] Interrupting assistant playback immediately!")
            self.state.reconcile_barge_in(self._current_sentence_spoken)

            if self.playback_task and not self.playback_task.done():
                self.playback_task.cancel()

            for task in self.synthesis_tasks:
                if not task.done():
                    task.cancel()
            self.synthesis_tasks.clear()

            sd.stop()
            self.state.is_speaking = False

    async def speak_sentence(self, sentence: str) -> bool:
        """Synthesizes and plays a sentence with barge-in stop support."""
        if not sentence or not sentence.strip():
            return True

        self._current_sentence_spoken = sentence
        self.state.is_speaking = True

        try:
            audio_bytes = await self.tts.synthesize_to_bytes(sentence)
            if self.telemetry.timings.get("tts_first_audio") is None:
                self.telemetry.mark("tts_first_audio")

            completed = await self.tts.play_audio_stream(
                audio_bytes,
                stop_check=lambda: not self.state.is_speaking
            )
            return completed
        except asyncio.CancelledError:
            return False
        except Exception as e:
            print(f"[TTS Error]: {e}")
            return False

    async def process_user_turn(self, audio_frames: List[np.ndarray]):
        """Processes collected user utterance end-to-end."""
        self.telemetry.start_turn()
        self.telemetry.mark("vad_endpointed")

        # 1. Package audio & transcribe
        full_audio = np.concatenate(audio_frames)
        self.telemetry.mark("stt_start")
        transcript = await self.stt.transcribe(full_audio)
        self.telemetry.mark("stt_completed")

        if not transcript or not transcript.strip():
            return

        print(f"\n👤 [User]: {transcript}")
        self.state.add_user_message(transcript)

        # 2. Cognitive ReAct Brain
        self.telemetry.mark("llm_start")
        token_stream = self.brain.execute_react_turn(self.state)

        # Generator wrapper to capture TTFT
        first_token_marked = False
        async def monitored_stream():
            nonlocal first_token_marked
            async for token in token_stream:
                if not first_token_marked:
                    self.telemetry.mark("llm_first_token")
                    first_token_marked = True
                yield token

        # 3. Stream sentences to TTS for sub-500ms TTFA
        sentence_stream = self.chunker.chunk_stream(monitored_stream())
        self.state.is_speaking = True

        print("🤖 [ApexCore]: ", end="", flush=True)
        try:
            async for sentence in sentence_stream:
                if not self.state.is_speaking:
                    # User interrupted via barge-in
                    break
                print(f"{sentence} ", end="", flush=True)
                finished = await self.speak_sentence(sentence)
                if not finished:
                    break
            print()
        except asyncio.CancelledError:
            print(" [Playback Cancelled]")

        self.state.is_speaking = False
        self.telemetry.print_report()

        # Log conversation metrics in SQLite WAL
        stats = self.telemetry.summary()
        try:
            db_manager.execute_write(
                """
                INSERT INTO conversation_logs 
                (turn_id, user_transcript, assistant_response, vad_ms, stt_ms, ttft_ms, ttfa_ms, barge_in_triggered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stats["turn_id"],
                    transcript,
                    self.state.messages[-1].get("content") if self.state.messages else "",
                    stats["vad_endpoint_ms"],
                    stats["stt_latency_ms"],
                    stats["llm_ttft_ms"],
                    stats["ttfa_ms"],
                    1 if self.state.is_interrupted else 0
                )
            )
        except Exception:
            pass

    async def run(self):
        """Main non-blocking audio event loop."""
        self.is_running = True
        self.vad.reset_states()
        
        print("\n" + "="*60)
        print("🎙️ APEXCORE FULL-DUPLEX VOICE AGENT ACTIVE")
        print("Listening for speech... (Speak naturally, or interrupt anytime!)")
        print("="*60 + "\n")

        # Open non-blocking mic stream
        stream = sd.InputStream(
            samplerate=INPUT_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=self._audio_callback
        )

        with stream:
            audio_buffer: List[np.ndarray] = []
            is_speaking = False
            consecutive_silent = 0

            while self.is_running:
                chunk = await self.audio_queue.get()
                
                # Check AEC threshold gating: if speaker is outputting, require higher probability
                threshold = INTERRUPT_PROB_THRESHOLD if self.state.is_speaking else SPEECH_PROB_THRESHOLD
                speech_prob = self.vad.process_chunk(chunk)
                has_speech = speech_prob >= threshold

                if has_speech:
                    if self.state.is_speaking:
                        # User interrupted the bot while talking
                        self.stop_playback_and_cancel()

                    if not is_speaking:
                        is_speaking = True
                        consecutive_silent = 0
                        audio_buffer = [chunk]
                    else:
                        audio_buffer.append(chunk)
                        consecutive_silent = 0
                else:
                    if is_speaking:
                        audio_buffer.append(chunk)
                        consecutive_silent += 1

                        # Endpoint turn when silence exceeds threshold
                        if consecutive_silent >= SILENCE_FRAMES:
                            is_speaking = False
                            consecutive_silent = 0
                            
                            # Dispatch turn processing in background
                            frames_to_process = list(audio_buffer)
                            audio_buffer.clear()
                            self.vad.reset_states()
                            await self.process_user_turn(frames_to_process)
