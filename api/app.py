"""FastAPI Application Server for ApexCore."""

import os
import sys
import base64
import time
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("api")

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import GROQ_API_KEY, TTS_VOICE
from core.state import ConversationState
from core.telemetry import TelemetryProfiler
from database.db import db_manager
from tools.system_tools import get_system_vitals, get_top_processes
from tools.file_tools import search_files, open_application, open_url
from tools.db_tools import query_local_db
from services.brain import AgentBrain
from services.tts import TTSService
from pipeline.chunker import SentenceChunker

# Create FastAPI app
app = FastAPI(
    title="ApexCore Voice AI Engine",
    description="High-performance asynchronous desktop automation & database intelligence voice platform.",
    version="1.0.0"
)

# Enable CORS for browser integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount React frontend build directory if available, else static
REACT_DIST_DIR = BASE_DIR / "frontend" / "dist"
STATIC_DIR = BASE_DIR / "static"

if REACT_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(REACT_DIST_DIR / "assets")), name="assets")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shared backend instances
state = ConversationState()
brain = AgentBrain()
tts = TTSService()
chunker = SentenceChunker()
telemetry = TelemetryProfiler()

# Request Models
class ChatRequest(BaseModel):
    prompt: str

class SQLRequest(BaseModel):
    sql_query: str

class AppLaunchRequest(BaseModel):
    app_name: str

class URLRequest(BaseModel):
    url: str
    browser: Optional[str] = "chrome"

class FileSearchRequest(BaseModel):
    directory: str
    extension: Optional[str] = None
    keyword: Optional[str] = None

@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the modern Jarvis Dynamic Notch React UI."""
    if REACT_DIST_DIR.exists() and (REACT_DIST_DIR / "index.html").exists():
        return FileResponse(REACT_DIST_DIR / "index.html")
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/health")
async def health_check():
    """Returns engine health status and key configuration."""
    return {
        "status": "online",
        "engine": "ApexCore Full-Duplex AI",
        "groq_configured": bool(GROQ_API_KEY),
        "database_wal": True,
        "voice": TTS_VOICE,
    }

@app.get("/api/tools/vitals")
async def api_get_vitals():
    """Fetches real-time OS performance vitals."""
    return get_system_vitals()

@app.get("/api/tools/processes")
async def api_get_processes(sort_by: str = "memory", count: int = 5):
    """Enumerates top consuming running processes."""
    return get_top_processes(sort_by=sort_by, count=count)

@app.post("/api/tools/search-files")
async def api_search_files(req: FileSearchRequest):
    """Searches user folders with path traversal security."""
    return search_files(directory=req.directory, extension=req.extension, keyword=req.keyword)

@app.post("/api/tools/open-app")
async def api_open_app(req: AppLaunchRequest):
    """Safely executes desktop applications."""
    return open_application(req.app_name)

@app.post("/api/tools/open-url")
async def api_open_url(req: URLRequest):
    """Opens any website URL or tab in Google Chrome or default browser."""
    return open_url(url=req.url, browser=req.browser)

@app.post("/api/tools/search-play")
async def api_search_play(query: str, platform: str = "youtube"):
    """Searches YouTube, Google, or Wikipedia and opens in Chrome."""
    from tools.file_tools import search_web_or_play
    return search_web_or_play(query=query, platform=platform)

@app.post("/api/tools/media")
async def api_media_control(action: str):
    """Controls system volume or playback (mute, volume_up, volume_down, play_pause)."""
    from tools.file_tools import control_media_or_volume
    return control_media_or_volume(action=action)

@app.post("/api/tools/open-folder")
async def api_open_folder(folder_name: str):
    """Opens target user directory or project folder in Windows Explorer."""
    from tools.file_tools import open_folder_or_path
    return open_folder_or_path(folder_name)

@app.post("/api/tools/desktop-calculate")
async def api_desktop_calculate(calculation: str, app: Optional[str] = "calculator"):
    """Performs automated GUI typing into desktop calculator."""
    from tools.file_tools import desktop_type_or_calculate
    return desktop_type_or_calculate(calculation_or_keys=calculation, app_to_open=app)

@app.post("/api/tools/focus-window")
async def api_focus_window(title: str):
    """Finds and foregrounds an active desktop window."""
    from tools.file_tools import focus_window
    return focus_window(title)

@app.post("/api/tools/chrome-video")
async def api_chrome_video(action: str = "toggle"):
    """Controls HTML5 video inside active Chrome tab via CDP."""
    from tools.file_tools import control_chrome_tab_video
    return control_chrome_tab_video(action=action)

@app.post("/api/tools/chrome-click")
async def api_chrome_click(selector: str = "first_result"):
    """Clicks DOM element or top search result inside Chrome via CDP."""
    from tools.file_tools import click_chrome_element
    return click_chrome_element(selector=selector)

@app.post("/api/tools/chrome-fill-search")
async def api_chrome_fill_search(query: str, submit: bool = True):
    """Fills search box in active Chrome tab via CDP."""
    from tools.file_tools import fill_chrome_search
    return fill_chrome_search(query=query, submit=submit)

@app.post("/api/tools/vision-analyze")
async def api_vision_analyze(question: str = "Describe what is on screen"):
    """Uses Multimodal Vision to inspect and describe the desktop screen."""
    from tools.file_tools import capture_and_analyze_screen
    return capture_and_analyze_screen(question_or_task=question)

@app.post("/api/tools/vision-click")
async def api_vision_click(target: str, double_click: bool = False):
    """Uses Multimodal Vision grounding to find and click any visual element on screen."""
    from tools.file_tools import click_on_visual_target
    return click_on_visual_target(target_description=target, double_click=double_click)

@app.post("/api/tools/query-db")
async def api_query_db(req: SQLRequest):
    """Executes safe read-only SQL queries against SQLite WAL tables."""
    return query_local_db(req.sql_query)

@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """
    Executes an end-to-end ReAct reasoning turn:
    Runs tool calls if necessary, synthesizes voice, and returns response + audio bytes.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    telemetry.start_turn()
    telemetry.mark("llm_start")

    state.add_user_message(req.prompt)

    # 1. Execute ReAct brain turn
    tokens = []
    first_token_marked = False
    
    async for token in brain.execute_react_turn(state):
        if not first_token_marked:
            telemetry.mark("llm_first_token")
            first_token_marked = True
        tokens.append(token)

    full_response = "".join(tokens).strip()

    # 2. Synthesize audio via Edge-TTS
    audio_base64 = None
    try:
        telemetry.mark("tts_first_audio")
        audio_bytes = await tts.synthesize_to_bytes(full_response)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[TTS Error in API]: {e}")

    stats = telemetry.summary()

    # 3. Log to SQLite WAL
    try:
        db_manager.execute_write(
            """
            INSERT INTO conversation_logs 
            (turn_id, user_transcript, assistant_response, vad_ms, stt_ms, ttft_ms, ttfa_ms, barge_in_triggered)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stats["turn_id"],
                req.prompt,
                full_response,
                0.0,
                0.0,
                stats["llm_ttft_ms"],
                stats["ttfa_ms"],
                0
            )
        )
    except Exception:
        pass

    return {
        "prompt": req.prompt,
        "response": full_response,
        "telemetry": stats,
        "audio_base64": audio_base64
    }

@app.post("/api/chat/clear")
async def api_clear_chat():
    """Resets conversational history."""
    state.clear()
    return {"status": "cleared", "messages": len(state.messages)}

@app.get("/api/telemetry/history")
async def api_get_telemetry_history(limit: int = 20):
    """Retrieves recent conversation telemetry logs from SQLite."""
    sql = "SELECT * FROM conversation_logs ORDER BY id DESC LIMIT ?;"
    return db_manager.execute_query(sql, (limit,))

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    Enterprise Full-Duplex Binary Audio & Token WebSocket Pipeline.
    1. Receives user text / voice transcript JSON: {"prompt": "..."}
    2. Streams LLM tokens incrementally via JSON frames: {"type": "token", "content": "..."}
    3. Concurrently chunks punctuated sentences via SentenceChunker.
    4. Streams binary MP3 audio chunks via binary WebSocket frames for sub-300ms TTFA!
    5. Supports instant client barge-in cancel frame: {"type": "interrupt"}
    """
    await websocket.accept()
    current_cancel_event = asyncio.Event()

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg_data = json.loads(raw_msg)
            except Exception:
                msg_data = {"prompt": raw_msg}

            # Handle instant client interruption
            if msg_data.get("type") == "interrupt":
                current_cancel_event.set()
                await websocket.send_json({"type": "interrupted"})
                continue

            user_prompt = msg_data.get("prompt", "").strip()
            if not user_prompt:
                continue

            current_cancel_event.clear()
            telemetry.start_turn()
            telemetry.mark("llm_start")
            state.add_user_message(user_prompt)

            # Queue for feeding tokens from ReAct brain to SentenceChunker
            token_queue = asyncio.Queue()
            full_tokens = []
            first_audio_sent = False

            async def token_feeder():
                """Consumes ReAct turn tokens and puts them into the queue."""
                try:
                    async for token in brain.execute_react_turn(state):
                        if current_cancel_event.is_set():
                            break
                        full_tokens.append(token)
                        await websocket.send_json({"type": "token", "content": token})
                        await token_queue.put(token)
                finally:
                    await token_queue.put(None)  # Sentinel to mark completion

            async def token_generator():
                """Async generator that yields tokens from the queue for SentenceChunker."""
                while True:
                    token = await token_queue.get()
                    if token is None:
                        break
                    yield token

            async def audio_streamer():
                """Chunks sentences and streams complete sentence MP3 audio frames to client."""
                nonlocal first_audio_sent
                async for sentence in chunker.chunk_stream(token_generator()):
                    if current_cancel_event.is_set():
                        break
                    
                    # Synthesize clean audio for this complete sentence
                    sentence_audio = await tts.synthesize_to_bytes(sentence)
                    if sentence_audio:
                        if not first_audio_sent:
                            telemetry.mark("tts_first_audio")
                            first_audio_sent = True
                        # Send the complete sentence MP3 frame directly over WebSocket
                        await websocket.send_bytes(sentence_audio)

            # Run token generation and concurrent TTS streaming together
            feeder_task = asyncio.create_task(token_feeder())
            audio_task = asyncio.create_task(audio_streamer())

            await asyncio.gather(feeder_task, audio_task)

            if not current_cancel_event.is_set():
                stats = telemetry.summary()
                full_text = "".join(full_tokens).strip()
                await websocket.send_json({
                    "type": "done",
                    "full_response": full_text,
                    "ttfa_ms": stats.get("ttfa_ms", 0.0)
                })
    except WebSocketDisconnect:
        current_cancel_event.set()
    except Exception as e:
        logger.error(f"WebSocket stream error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
