"""Real-time millisecond latency telemetry and profiler."""

import time
from typing import Dict, Any, Optional

class TelemetryProfiler:
    """Tracks millisecond timings across every stage of the conversational turn."""

    def __init__(self):
        self.turn_id: int = 0
        self.timings: Dict[str, float] = {}
        self.active: bool = False

    def start_turn(self) -> None:
        """Starts timing a new conversational turn."""
        self.turn_id += 1
        self.timings = {"turn_start": time.perf_counter()}
        self.active = True

    def mark(self, event_name: str) -> float:
        """Records timestamp for an event and returns elapsed ms since turn start."""
        now = time.perf_counter()
        self.timings[event_name] = now
        elapsed_ms = (now - self.timings.get("turn_start", now)) * 1000.0
        return elapsed_ms

    def get_duration_ms(self, start_event: str, end_event: str) -> Optional[float]:
        """Calculates delta duration in milliseconds between two recorded events."""
        if start_event in self.timings and end_event in self.timings:
            return (self.timings[end_event] - self.timings[start_event]) * 1000.0
        return None

    def summary(self) -> Dict[str, Any]:
        """Generates a structured latency breakdown for logging and display."""
        vad_ms = self.get_duration_ms("vad_start", "vad_endpointed")
        stt_ms = self.get_duration_ms("stt_start", "stt_completed")
        ttft_ms = self.get_duration_ms("llm_start", "llm_first_token")
        ttfa_ms = self.get_duration_ms("turn_start", "tts_first_audio")
        total_pipeline_ms = self.get_duration_ms("turn_start", "tts_first_audio")

        return {
            "turn_id": self.turn_id,
            "vad_endpoint_ms": round(vad_ms, 1) if vad_ms is not None else None,
            "stt_latency_ms": round(stt_ms, 1) if stt_ms is not None else None,
            "llm_ttft_ms": round(ttft_ms, 1) if ttft_ms is not None else None,
            "ttfa_ms": round(ttfa_ms, 1) if ttfa_ms is not None else None,
            "total_turn_ms": round(total_pipeline_ms, 1) if total_pipeline_ms is not None else None,
        }

    def print_report(self) -> None:
        """Prints a high-visibility terminal telemetry box."""
        stats = self.summary()
        print("\n" + "="*50)
        print(f"📊 APEXCORE LATENCY TELEMETRY [Turn #{self.turn_id}]")
        print("="*50)
        if stats["vad_endpoint_ms"] is not None:
            print(f"  • VAD Endpoint Delay:  {stats['vad_endpoint_ms']} ms")
        if stats["stt_latency_ms"] is not None:
            print(f"  • STT Transcription:   {stats['stt_latency_ms']} ms")
        if stats["llm_ttft_ms"] is not None:
            print(f"  • LLM TTFT (Groq LPU): {stats['llm_ttft_ms']} ms")
        if stats["ttfa_ms"] is not None:
            print(f"  • Time-to-First-Audio: {stats['ttfa_ms']} ms  ⚡ (Target: <500ms)")
        print("="*50 + "\n")
