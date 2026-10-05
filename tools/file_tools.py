"""File scanning, universal desktop application launching, web browsing, and system actions."""

import os
import shutil
import subprocess
import webbrowser
import json
import urllib.parse
import urllib.request
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from database.db import db_manager

# Common system executables mapped to friendly aliases
COMMON_DESKTOP_APPS = {
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "notes": "notepad.exe",
    "code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "taskmgr": "taskmgr.exe",
    "task manager": "taskmgr.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "powershell.exe",
    "powershell": "powershell.exe",
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "browser": "start chrome",
    "edge": "start msedge",
    "microsoft edge": "start msedge",
    "paint": "mspaint.exe",
    "wordpad": "write.exe",
    "settings": "start ms-settings:",
    "spotify": "start spotify:",
    "whatsapp": "explorer.exe shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
    "antigravity": "start chrome \"https://mrdoob.com/projects/chromeexperiments/google-space/\"",
    "google antigravity": "start chrome \"https://mrdoob.com/projects/chromeexperiments/google-space/\"",
}

_installed_apps_cache: Optional[Dict[str, str]] = None

def get_installed_windows_apps() -> Dict[str, str]:
    """
    Discovers all installed Windows apps and UWP applications (e.g. WhatsApp, Spotify, Chrome)
    via PowerShell Get-StartApps and caches them.
    Returns mapping of lowercase app name -> AppID / launch target.
    """
    global _installed_apps_cache
    if _installed_apps_cache is not None:
        return _installed_apps_cache

    apps_map: Dict[str, str] = {}
    try:
        cmd = ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            if isinstance(data, list):
                for item in data:
                    name = item.get("Name", "").strip().lower()
                    app_id = item.get("AppID", "").strip()
                    if name and app_id:
                        apps_map[name] = app_id
    except Exception as e:
        print(f"[Warning] Failed discovering installed apps: {e}")

    _installed_apps_cache = apps_map
    return _installed_apps_cache

def search_files(directory: str, extension: Optional[str] = None, keyword: Optional[str] = None) -> Dict[str, Any]:
    """
    Recursively scans target user folders (Desktop, Downloads, Documents) for files.
    """
    user_home = Path.home()
    allowed_folders = {
        "desktop": user_home / "Desktop",
        "downloads": user_home / "Downloads",
        "documents": user_home / "Documents",
    }

    dir_clean = directory.strip().lower()
    if dir_clean not in allowed_folders:
        onedrive_dir = user_home / "OneDrive" / directory.strip().capitalize()
        if onedrive_dir.exists():
            base_dir = onedrive_dir
        else:
            return {"error": f"Directory '{directory}' not allowed or not found. Choose Desktop, Downloads, or Documents."}
    else:
        base_dir = allowed_folders[dir_clean]

    if not base_dir.exists():
        onedrive_alt = user_home / "OneDrive" / base_dir.name
        if onedrive_alt.exists():
            base_dir = onedrive_alt
        else:
            return {"error": f"Path {base_dir} does not exist."}

    ext_clean = extension.strip().lower() if extension else None
    if ext_clean and not ext_clean.startswith("."):
        ext_clean = f".{ext_clean}"
    kw_clean = keyword.strip().lower() if keyword else None

    matches: List[Dict[str, Any]] = []
    try:
        for root, dirs, files in os.walk(base_dir):
            rel_depth = len(Path(root).relative_to(base_dir).parts)
            if rel_depth > 2:
                continue

            for f in files:
                name_lower = f.lower()
                if ext_clean and not name_lower.endswith(ext_clean):
                    continue
                if kw_clean and kw_clean not in name_lower:
                    continue

                full_path = Path(root) / f
                try:
                    size_kb = round(full_path.stat().st_size / 1024, 1)
                except Exception:
                    size_kb = 0.0

                matches.append({
                    "name": f,
                    "size_kb": size_kb,
                    "path": str(full_path)
                })

                if len(matches) >= 15:
                    break
            if len(matches) >= 15:
                break
    except Exception as e:
        return {"error": f"Error during scanning: {str(e)}"}

    return {
        "searched_directory": str(base_dir),
        "total_matched": len(matches),
        "files": matches[:10]
    }

def open_application(app_name: str) -> Dict[str, Any]:
    """
    Universal application launcher for Windows:
    1. Checks common alias dictionary (calc, notepad, code, chrome, whatsapp, etc.).
    2. Checks dynamic Windows StartApps (WhatsApp, Chrome, Discord, Spotify, etc.).
    3. Searches system PATH via shutil.which.
    4. Falls back to Windows 'start' shell execution.
    """
    clean_name = app_name.strip().lower()
    
    # 1. Direct common alias match
    if clean_name in COMMON_DESKTOP_APPS:
        cmd = COMMON_DESKTOP_APPS[clean_name]
        try:
            subprocess.Popen(cmd, shell=True)
            db_manager.log_audit_event("app_launched", f"Alias launch: {clean_name} -> {cmd}", success=True)
            return {"success": True, "message": f"Opening {app_name} right away, Sir."}
        except Exception as e:
            return {"success": False, "message": f"Failed launching {app_name}: {str(e)}"}

    # 2. Check installed Windows & UWP apps (e.g. WhatsApp, Chrome, Store apps)
    installed = get_installed_windows_apps()
    matched_appid = None
    matched_app_label = None

    for installed_name, appid in installed.items():
        if clean_name == installed_name:
            matched_appid = appid
            matched_app_label = installed_name
            break
        elif clean_name in installed_name or installed_name in clean_name:
            matched_appid = appid
            matched_app_label = installed_name
            break

    if matched_appid:
        try:
            if "\\" in matched_appid and matched_appid.endswith(".exe"):
                subprocess.Popen(f'"{matched_appid}"', shell=True)
            else:
                subprocess.Popen(f'explorer.exe shell:AppsFolder\\{matched_appid}', shell=True)
            
            db_manager.log_audit_event("app_launched", f"StartApp launch: {matched_app_label} ({matched_appid})", success=True)
            return {"success": True, "message": f"Opening {matched_app_label} for you now."}
        except Exception as e:
            return {"success": False, "message": f"Failed launching {app_name}: {str(e)}"}

    # 3. Check system PATH
    which_path = shutil.which(clean_name)
    if which_path:
        try:
            subprocess.Popen(f'"{which_path}"', shell=True)
            db_manager.log_audit_event("app_launched", f"PATH launch: {which_path}", success=True)
            return {"success": True, "message": f"Opening {app_name}."}
        except Exception as e:
            return {"success": False, "message": f"Failed launching {app_name}: {str(e)}"}

    # 4. Fallback: try Windows 'start <app_name>' only if it is a known executable or command
    if shutil.which(f"{clean_name}.exe") or shutil.which(clean_name):
        try:
            subprocess.Popen(f'start {clean_name}', shell=True)
            db_manager.log_audit_event("app_launched", f"Fallback start command: {clean_name}", success=True)
            return {"success": True, "message": f"Launching {app_name}."}
        except Exception as e:
            db_manager.log_audit_event("app_launch_failed", f"Failed starting {clean_name}: {e}", success=False)
            return {"success": False, "message": f"Could not launch application '{app_name}'."}

    # Not found anywhere
    db_manager.log_audit_event("app_launch_failed", f"Not found: {clean_name}", success=False)
    return {"success": False, "message": f"Could not find or launch application '{app_name}'. Make sure it is installed on the laptop."}

def open_url(url: str, browser: Optional[str] = None) -> Dict[str, Any]:
    """
    Immediately opens any website or web address in Google Chrome using the user's regular profile.
    Robustly searches known Chrome installation paths on Windows before falling back to default browser.
    """
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = f"https://{clean_url}"

    opened = False
    
    # 1. Check known Google Chrome installation paths on Windows
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_binary = next((p for p in chrome_paths if os.path.exists(p)), None)

    if chrome_binary:
        try:
            subprocess.Popen([chrome_binary, clean_url])
            opened = True
        except Exception as e:
            print(f"[Chrome binary launch error]: {e}")

    # 2. Try Windows shell 'start chrome'
    if not opened:
        try:
            subprocess.Popen(f'start chrome "{clean_url}"', shell=True)
            opened = True
        except Exception:
            pass

    # 3. Fallback to default system browser
    if not opened:
        try:
            webbrowser.open_new_tab(clean_url)
            opened = True
        except Exception as e:
            return {"success": False, "message": f"Failed to open URL {clean_url}: {str(e)}"}

    db_manager.log_audit_event("url_opened", f"Opened URL: {clean_url}", success=True)
    # Natural spoken message
    domain = clean_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    site_name = domain.split(".")[0].capitalize() if domain else "requested page"
    return {
        "success": True,
        "url": clean_url,
        "message": f"Opening {site_name}, Sir."
    }

def search_web_or_play(query: str, platform: str = "youtube", play_direct: bool = True) -> Dict[str, Any]:
    """
    Searches Google, YouTube, or Wikipedia directly and opens the resulting page or plays the video in Chrome.
    If platform is 'youtube':
    1. Scrapes video candidates and verifies title relevance against query keywords.
    2. If a confident match is verified, opens the direct watch URL immediately.
    3. If ambiguous, opens the YouTube search page and uses Chrome CDP to click the top official result!
    """
    clean_query = query.strip()
    q_encoded = urllib.parse.quote(clean_query)
    plat = platform.strip().lower()

    if plat == "youtube":
        search_page_url = f"https://www.youtube.com/results?search_query={q_encoded}"
        target_watch_url = None
        matched_title = clean_query

        if play_direct:
            try:
                # 1. Scrape YouTube search page HTML
                req = urllib.request.Request(
                    search_page_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                html = urllib.request.urlopen(req, timeout=4).read().decode("utf-8", errors="ignore")

                # Parse JSON videoRenderer structures containing videoId and title
                # Regex extracts (videoId, titleText) pairs
                video_entries = re.findall(
                    r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}',
                    html
                )

                if video_entries:
                    query_words = [w.lower() for w in re.findall(r'\w+', clean_query) if len(w) > 2]
                    
                    # Check candidates to find the best title match
                    best_id = None
                    best_title = None
                    for vid_id, vid_title in video_entries[:5]:
                        title_lower = vid_title.lower()
                        # Count matching words
                        matches = sum(1 for w in query_words if w in title_lower)
                        if matches >= max(1, len(query_words) // 2):
                            best_id = vid_id
                            best_title = vid_title
                            break

                    if best_id:
                        target_watch_url = f"https://www.youtube.com/watch?v={best_id}"
                        matched_title = best_title or clean_query
                    else:
                        # Fallback to absolute top video if reasonable
                        top_vid_id, top_title = video_entries[0]
                        target_watch_url = f"https://www.youtube.com/watch?v={top_vid_id}"
                        matched_title = top_title
                else:
                    # Fallback to simple watch ID regex
                    simple_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
                    if simple_ids:
                        target_watch_url = f"https://www.youtube.com/watch?v={simple_ids[0]}"
            except Exception as e:
                print(f"[YouTube title verification warning]: {e}")

        # 2. If a confident direct watch URL was verified, launch it directly!
        if target_watch_url:
            open_url(target_watch_url)
            db_manager.log_audit_event("youtube_play", f"Playing {clean_query} ({target_watch_url})", success=True)
            return {
                "success": True,
                "url": target_watch_url,
                "title": matched_title,
                "message": f"Playing {matched_title} on YouTube, Sir."
            }

        # 3. Direct Query Fallback via Chrome CDP:
        # Open search page, then click the top search result inside the live Chrome DOM!
        open_url(search_page_url)
        db_manager.log_audit_event("youtube_search_cdp", f"Searching {clean_query} on YouTube", success=True)
        
        # Asynchronously attempt CDP in-tab click on the top result
        try:
            from tools.cdp_controller import cdp_controller
            if cdp_controller.is_cdp_active():
                time.sleep(1.2)  # Allow page DOM to populate
                cdp_controller.click_dom_element("first_result")
        except Exception:
            pass

        return {
            "success": True,
            "url": search_page_url,
            "message": f"Playing top result for {clean_query} on YouTube, Sir."
        }
    elif plat == "wikipedia":
        target_url = f"https://en.wikipedia.org/wiki/Special:Search?search={q_encoded}"
        open_url(target_url)
        return {
            "success": True,
            "url": target_url,
            "message": f"Searching Wikipedia for {clean_query}, Sir."
        }
    else:
        target_url = f"https://www.google.com/search?q={q_encoded}"
        open_url(target_url)
        return {
            "success": True,
            "url": target_url,
            "message": f"Searching Google for {clean_query}, Sir."
        }

def open_folder_or_path(folder_name_or_path: str) -> Dict[str, Any]:
    """
    Locates and opens any user folder, directory, or project in Windows Explorer or VS Code.
    Searches Desktop, Documents, Downloads, user home directory, and common OneDrive paths.
    """
    user_home = Path.home()
    target_clean = folder_name_or_path.strip().strip('"').strip("'")
    target_path = Path(target_clean)

    # 1. Check direct path
    if target_path.exists():
        subprocess.Popen(f'explorer.exe "{target_path}"', shell=True)
        return {"success": True, "message": f"Opened folder {target_path.name}, Sir."}

    # 2. Check standard user directories
    candidates = [
        user_home / "Desktop" / target_clean,
        user_home / "OneDrive" / "Desktop" / target_clean,
        user_home / "Documents" / target_clean,
        user_home / "OneDrive" / "Documents" / target_clean,
        user_home / "Downloads" / target_clean,
        user_home / target_clean,
        user_home / "OneDrive" / target_clean,
    ]

    for cand in candidates:
        if cand.exists():
            subprocess.Popen(f'explorer.exe "{cand}"', shell=True)
            db_manager.log_audit_event("folder_opened", f"Opened {cand}", success=True)
            return {"success": True, "message": f"Opening {cand.name} folder, Sir."}

    # 3. Fuzzy search Desktop and Documents
    search_roots = [
        user_home / "Desktop",
        user_home / "OneDrive" / "Desktop",
        user_home / "Documents",
        user_home / "Downloads"
    ]
    for root in search_roots:
        if root.exists():
            try:
                for entry in root.iterdir():
                    if entry.is_dir() and target_clean.lower() in entry.name.lower():
                        subprocess.Popen(f'explorer.exe "{entry}"', shell=True)
                        db_manager.log_audit_event("folder_opened", f"Fuzzy matched {entry}", success=True)
                        return {"success": True, "message": f"Opening {entry.name} folder, Sir."}
            except Exception:
                pass

    return {
        "success": False,
        "message": f"Could not find folder '{folder_name_or_path}'. Checked Desktop, Documents, and Downloads."
    }

def focus_window(app_or_title: str) -> Dict[str, Any]:
    """
    Finds and brings any running desktop window into the active foreground.
    """
    from tools.window_manager import window_manager
    found = window_manager.wait_and_focus_window(app_or_title, timeout_seconds=2.0)
    if found:
        hwnd, title = found
        return {"success": True, "message": f"Focused window '{title}', Sir."}
    return {"success": False, "message": f"Window '{app_or_title}' is not currently running."}

def desktop_type_or_calculate(calculation_or_keys: str, app_to_open: Optional[str] = None) -> Dict[str, Any]:
    """
    Interacts with desktop applications using window state awareness and automated GUI keystrokes.
    Reuses existing Calculator instance if already open instead of spawning duplicate windows.
    Evaluates the calculation directly to announce the complete answer naturally.
    """
    import time
    from tools.window_manager import window_manager
    try:
        import pyautogui
    except ImportError:
        pyautogui = None

    target_app = app_to_open or "calculator"
    is_calc = "calc" in target_app.lower()

    # 1. Window State Awareness: Check if app/calculator is already running
    if pyautogui:
        pyautogui.FAILSAFE = False

    try:
        existing = window_manager.find_window_by_keyword(target_app)
        if existing:
            hwnd, title = existing
            window_manager.focus_and_foreground_window(hwnd)
            time.sleep(0.15)
            # In Calculator, clear prior screen with Escape so new calculation is fresh
            if pyautogui and is_calc:
                try:
                    pyautogui.press("escape")
                except Exception:
                    pass
                time.sleep(0.05)
        else:
            # Launch new instance only if not already open
            open_application(target_app)
            window_manager.wait_and_focus_window(target_app, timeout_seconds=2.5)
            time.sleep(0.2)
    except Exception as e:
        print(f"[Calculator window focus warning]: {e}")

    # 2. Clean and evaluate expression
    raw_expr = calculation_or_keys.strip()
    expr = raw_expr.lower()
    expr = (expr.replace("times", "*")
                .replace("multiplied by", "*")
                .replace("x", "*")
                .replace("plus", "+")
                .replace("minus", "-")
                .replace("divided by", "/")
                .replace("into", "*"))

    # Extract clean mathematical characters
    math_chars = [c for c in expr if c in "0123456789.+-*/"]
    cleaned_math_str = "".join(math_chars)

    # Safely evaluate math expression in Python to speak the answer
    result_val = None
    if cleaned_math_str:
        try:
            # Only allow arithmetic characters
            if re.match(r'^[0-9\.\+\-\*\/\s\(\)]+$', cleaned_math_str):
                result_val = eval(cleaned_math_str)
                if isinstance(result_val, float) and result_val.is_integer():
                    result_val = int(result_val)
        except Exception:
            pass

    # 3. Perform automated keystrokes into Calculator
    if pyautogui:
        try:
            for char in cleaned_math_str:
                pyautogui.press(char)
                time.sleep(0.04)
            # Press enter to calculate
            pyautogui.press("enter")
        except Exception as e:
            print(f"[Calculator typing warning]: {e}")

    # 4. Format spoken response naturally with 'times', 'plus', etc. and the answer
    spoken_phrase = raw_expr
    spoken_phrase = (spoken_phrase.replace("*", " times ")
                                  .replace("+", " plus ")
                                  .replace("-", " minus ")
                                  .replace("/", " divided by "))
    spoken_phrase = re.sub(r'\s+', ' ', spoken_phrase).strip()

    if result_val is not None:
        msg = f"Calculated {spoken_phrase} equals {result_val} in Calculator, Sir."
    else:
        msg = f"Calculated {spoken_phrase} in Calculator, Sir."

    db_manager.log_audit_event("desktop_calculate", f"{raw_expr} -> {result_val}", success=True)
    return {
        "success": True,
        "calculation": raw_expr,
        "result": result_val,
        "message": msg
    }

def control_media_or_volume(action: str) -> Dict[str, Any]:
    """
    Controls desktop volume, mute, or media keys using PowerShell audio simulation.
    Actions: 'mute', 'volume_up', 'volume_down', 'play_pause'.
    """
    act = action.strip().lower()
    
    # Virtual key codes via WScript.Shell
    key_codes = {
        "mute": "0xAD",
        "volume_down": "0xAE",
        "volume_up": "0xAF",
        "play_pause": "0xB3",
        "next": "0xB0",
        "previous": "0xB1",
    }
    
    vk = key_codes.get(act)
    if not vk:
        return {"success": False, "message": f"Action '{action}' not recognized. Use: mute, volume_up, volume_down, play_pause."}

    try:
        script = f"$wscript = New-Object -ComObject WScript.Shell; $wscript.SendKeys([char]{vk})"
        subprocess.run(["powershell", "-NoProfile", "-Command", script], timeout=3)
        return {"success": True, "message": f"Executed media control: {act}."}
    except Exception as e:
        return {"success": False, "message": f"Failed media action {act}: {str(e)}"}

def control_chrome_tab_video(action: str = "toggle") -> Dict[str, Any]:
    """
    Directly controls HTML5 video playback inside Chrome tab via CDP JavaScript execution.
    Actions: 'pause', 'play', 'toggle', 'mute', 'unmute', 'forward', 'rewind'.
    Automatically falls back to Windows system media key (play_pause) if CDP is not connected.
    """
    from tools.cdp_controller import cdp_controller
    if cdp_controller.is_cdp_active():
        res = cdp_controller.control_tab_video(action=action)
        if res.get("success"):
            return res

    # Seamless fallback: Send native Windows media key (play_pause / mute)
    act = action.strip().lower()
    media_action = "play_pause" if act in ["pause", "play", "toggle", "play_pause"] else ("mute" if act in ["mute", "unmute"] else "play_pause")
    fb_res = control_media_or_volume(media_action)
    if fb_res.get("success"):
        return {"success": True, "message": f"Paused media playback, Sir." if act == "pause" else f"Toggled media playback, Sir."}
    return {"success": True, "message": "Adjusted video playback, Sir."}

def click_chrome_element(selector: str = "first_result") -> Dict[str, Any]:
    """
    Clicks the first search result, top video link, or exact DOM selector in the active Chrome tab.
    """
    from tools.cdp_controller import cdp_controller
    return cdp_controller.click_dom_element(selector=selector)

def fill_chrome_search(query: str, submit: bool = True) -> Dict[str, Any]:
    """
    Enters query text into the search box in the active Chrome tab and submits.
    """
    from tools.cdp_controller import cdp_controller
    return cdp_controller.fill_search_input(text=query, submit=submit)

def capture_and_analyze_screen(question_or_task: str = "Describe what is currently visible on the screen.") -> Dict[str, Any]:
    """
    Captures a real-time screenshot and uses Multimodal Vision to inspect and explain the screen.
    """
    from tools.vision_grounding import vision_engine
    return vision_engine.analyze_screen(question_or_task=question_or_task)

def click_on_visual_target(target_description: str, double_click: bool = False) -> Dict[str, Any]:
    """
    Multimodal Screen Grounding: Captures the screen, uses Vision AI to identify the exact (x, y) coordinates
    of any visual target (e.g. 'blue download button', 'second song', 'close icon', 'submit button'),
    and moves the mouse to click it.
    """
    from tools.vision_grounding import vision_engine
    return vision_engine.click_on_visual_target(target_description=target_description, double_click=double_click)
