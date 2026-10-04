"""
Chrome DevTools Protocol (CDP) Controller for ApexCore.
Enables real-time in-tab browser automation:
- Controlling HTML5 video playback (pause, play, toggle, mute, seek)
- Clicking exact DOM elements and search results without guessing coordinates
- Filling web search boxes and form inputs
- Inspecting active page DOM, titles, and URLs
"""

import os
import json
import time
import subprocess
import urllib.request
import asyncio
import logging
from typing import Dict, Any, List, Optional
import websockets

logger = logging.getLogger("cdp_controller")


class ChromeCDPController:
    """Manages connection to Google Chrome via Chrome DevTools Protocol (CDP on port 9222)."""

    def __init__(self, port: int = 9222, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.base_url = f"http://{self.host}:{self.port}"
        self.profile_dir = os.path.expanduser("~/.apex_chrome_profile")

    def is_cdp_active(self) -> bool:
        """Checks if Chrome is actively listening with remote debugging enabled."""
        try:
            res = urllib.request.urlopen(f"{self.base_url}/json/version", timeout=1.0)
            return res.getcode() == 200
        except Exception:
            return False

    def ensure_chrome_cdp(self, initial_url: Optional[str] = None) -> bool:
        """
        Launches Google Chrome with --remote-debugging-port=9222 if not already active.
        Uses an isolated user profile so it never conflicts with regular Chrome sessions.
        """
        if self.is_cdp_active():
            return True

        os.makedirs(self.profile_dir, exist_ok=True)
        target = initial_url or "https://www.google.com"
        cmd = f'start chrome --remote-debugging-port={self.port} --user-data-dir="{self.profile_dir}" "{target}"'
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            logger.error(f"Failed to start Chrome with CDP: {e}")
            return False

        # Wait up to 5 seconds for CDP socket to become ready
        for _ in range(10):
            time.sleep(0.5)
            if self.is_cdp_active():
                return True

        return False

    def list_tabs(self) -> List[Dict[str, Any]]:
        """Retrieves list of active tabs from Chrome CDP endpoint."""
        try:
            res = urllib.request.urlopen(f"{self.base_url}/json", timeout=2.0)
            data = json.loads(res.read().decode("utf-8", errors="ignore"))
            return [t for t in data if t.get("type") == "page"]
        except Exception as e:
            logger.error(f"Error listing CDP tabs: {e}")
            return []

    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Returns the most relevant page tab (e.g. YouTube if available, else first page)."""
        tabs = self.list_tabs()
        if not tabs:
            return None

        # Prefer YouTube or media tab if available
        for t in tabs:
            url = t.get("url", "").lower()
            title = t.get("title", "").lower()
            if "youtube" in url or "youtube" in title or "watch" in url:
                return t

        return tabs[0]

    async def execute_js(self, expression: str, tab_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes arbitrary JavaScript in the target or active tab via CDP Runtime.evaluate WebSocket.
        """
        if not self.ensure_chrome_cdp():
            return {"success": False, "message": "Chrome CDP is not active and could not be launched."}

        tabs = self.list_tabs()
        if not tabs:
            return {"success": False, "message": "No open browser tabs found in Chrome."}

        target_tab = None
        if tab_id:
            for t in tabs:
                if t.get("id") == tab_id:
                    target_tab = t
                    break

        if not target_tab:
            target_tab = self.get_active_tab()

        if not target_tab or "webSocketDebuggerUrl" not in target_tab:
            return {"success": False, "message": "Could not acquire WebSocket debugger URL for tab."}

        ws_url = target_tab["webSocketDebuggerUrl"]

        try:
            async with websockets.connect(ws_url, close_timeout=3.0) as ws:
                payload = {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expression,
                        "returnByValue": True,
                        "awaitPromise": True
                    }
                }
                await ws.send(json.dumps(payload))
                response_raw = await ws.recv()
                data = json.loads(response_raw)

                result_container = data.get("result", {})
                eval_result = result_container.get("result", {})

                if "value" in eval_result:
                    val = eval_result["value"]
                    return {"success": True, "value": val, "tab": target_tab.get("title")}
                elif "description" in eval_result:
                    return {"success": True, "value": eval_result["description"], "tab": target_tab.get("title")}
                else:
                    return {"success": True, "result": eval_result, "tab": target_tab.get("title")}
        except Exception as e:
            return {"success": False, "message": f"CDP WebSocket execution error: {str(e)}"}

    def run_js_sync(self, expression: str) -> Dict[str, Any]:
        """Synchronous wrapper for execute_js to integrate with synchronous tools."""
        try:
            return asyncio.run(self.execute_js(expression))
        except RuntimeError:
            # Handle case where an event loop is already running
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.execute_js(expression))

    # --- High-Level In-Tab Actions ---

    def control_tab_video(self, action: str = "toggle") -> Dict[str, Any]:
        """
        Controls HTML5 video inside the active Chrome tab.
        Actions: 'play', 'pause', 'toggle', 'mute', 'unmute', 'forward', 'rewind'.
        """
        act = action.strip().lower()
        js_code = f"""
        (() => {{
            const v = document.querySelector('video');
            if (!v) return {{ error: 'No video element found in current tab.' }};
            
            const act = '{act}';
            if (act === 'pause') {{
                v.pause();
                return {{ status: 'paused', title: document.title }};
            }} else if (act === 'play') {{
                v.play();
                return {{ status: 'playing', title: document.title }};
            }} else if (act === 'toggle' || act === 'play_pause') {{
                if (v.paused) {{ v.play(); return {{ status: 'playing', title: document.title }}; }}
                else {{ v.pause(); return {{ status: 'paused', title: document.title }}; }}
            }} else if (act === 'mute') {{
                v.muted = true;
                return {{ status: 'muted', title: document.title }};
            }} else if (act === 'unmute') {{
                v.muted = false;
                return {{ status: 'unmuted', title: document.title }};
            }} else if (act === 'forward') {{
                v.currentTime = Math.min(v.duration, v.currentTime + 10);
                return {{ status: 'forwarded_10s', currentTime: Math.round(v.currentTime) }};
            }} else if (act === 'rewind') {{
                v.currentTime = Math.max(0, v.currentTime - 10);
                return {{ status: 'rewound_10s', currentTime: Math.round(v.currentTime) }};
            }}
            return {{ error: 'Unknown video action: ' + act }};
        }})()
        """
        res = self.run_js_sync(js_code)
        if res.get("success") and isinstance(res.get("value"), dict):
            val = res["value"]
            if "error" in val:
                return {"success": False, "message": val["error"]}
            status = val.get("status", "executed")
            return {"success": True, "message": f"Video in Chrome is now {status}, Sir."}
        return res

    def click_dom_element(self, selector: str = "first_result") -> Dict[str, Any]:
        """
        Finds and clicks an exact DOM element or top search result on YouTube/Google.
        Selectors:
        - 'first_result': Automatically detects top YouTube video card, link, or Google result.
        - CSS selector: e.g. '#search-icon-legacy', 'a#video-title', 'button[aria-label="Play"]'.
        """
        js_code = f"""
        (() => {{
            const sel = '{selector}';
            let target = null;
            
            if (sel === 'first_result' || sel === 'top_result') {{
                // YouTube video link
                target = document.querySelector('ytd-video-renderer a#video-title, ytd-compact-video-renderer a#video-title, #contents a#video-title, #rso a h3');
                if (target) {{
                    target = target.closest('a') || target;
                }}
            }} else {{
                target = document.querySelector(sel);
            }}

            if (!target) {{
                return {{ error: 'Element matching selector \"' + sel + '\" was not found in the active tab.' }};
            }}

            target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            target.click();
            return {{
                clicked: true,
                tag: target.tagName,
                text: (target.innerText || target.textContent || '').trim().substring(0, 60),
                href: target.href || null
            }};
        }})()
        """
        res = self.run_js_sync(js_code)
        if res.get("success") and isinstance(res.get("value"), dict):
            val = res["value"]
            if "error" in val:
                return {"success": False, "message": val["error"]}
            text = val.get("text") or "target element"
            return {"success": True, "message": f"Clicked '{text}' in Chrome, Sir."}
        return res

    def fill_search_input(self, text: str, submit: bool = True) -> Dict[str, Any]:
        """
        Locates the primary search input on the active page (YouTube, Google, Wikipedia)
        and enters the text, optionally pressing Enter to submit.
        """
        escaped_text = json.dumps(text)
        js_code = f"""
        (() => {{
            const query = {escaped_text};
            const inputs = [
                'input[name="search_query"]', // YouTube
                'textarea[name="q"]',         // Google
                'input[name="q"]',            // Google fallback
                'input[type="search"]',       // Generic search
                'input[type="text"]'          // Fallback text input
            ];

            let inputEl = null;
            for (const s of inputs) {{
                const el = document.querySelector(s);
                if (el && el.offsetParent !== null) {{
                    inputEl = el;
                    break;
                }}
            }}

            if (!inputEl) {{
                return {{ error: 'Could not find an active search input on the current page.' }};
            }}

            inputEl.focus();
            inputEl.value = query;
            inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
            inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));

            if ({str(submit).lower()}) {{
                // Submit form or press Enter
                const enterEvent = new KeyboardEvent('keydown', {{
                    bubbles: true,
                    cancelable: true,
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13
                }});
                inputEl.dispatchEvent(enterEvent);
                if (inputEl.form) inputEl.form.submit();
            }}

            return {{ filled: true, query: query, title: document.title }};
        }})()
        """
        res = self.run_js_sync(js_code)
        if res.get("success") and isinstance(res.get("value"), dict):
            val = res["value"]
            if "error" in val:
                return {"success": False, "message": val["error"]}
            return {"success": True, "message": f"Entered '{text}' into Chrome search, Sir."}
        return res


cdp_controller = ChromeCDPController()
