"""File scanning, universal desktop application launching, web browsing, and system actions."""

import os
import shutil
import subprocess
import webbrowser
import json
import urllib.parse
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
    Opens any website or web address in Google Chrome or default browser.
    """
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = f"https://{clean_url}"

    opened_with_chrome = False
    try:
        installed = get_installed_windows_apps()
        has_chrome = any("chrome" in k for k in installed.keys())
        if has_chrome or (browser and "chrome" in browser.lower()):
            subprocess.Popen(f'start chrome "{clean_url}"', shell=True)
            opened_with_chrome = True
    except Exception:
        opened_with_chrome = False

    if not opened_with_chrome:
        try:
            webbrowser.open_new_tab(clean_url)
        except Exception as e:
            return {"success": False, "message": f"Failed to open URL {clean_url}: {str(e)}"}

    db_manager.log_audit_event("url_opened", f"Opened URL: {clean_url}", success=True)
    return {
        "success": True,
        "url": clean_url,
        "message": f"Opening {clean_url} in your browser."
    }

def search_web_or_play(query: str, platform: str = "youtube") -> Dict[str, Any]:
    """
    Searches Google, YouTube, or Wikipedia directly and opens the resulting page/video in Chrome.
    Example: search_web_or_play(query="Interstellar soundtrack", platform="youtube")
    """
    q_encoded = urllib.parse.quote(query.strip())
    plat = platform.strip().lower()

    if plat == "youtube":
        target_url = f"https://www.youtube.com/results?search_query={q_encoded}"
        label = f"Searching YouTube for '{query}'"
    elif plat == "wikipedia":
        target_url = f"https://en.wikipedia.org/wiki/Special:Search?search={q_encoded}"
        label = f"Searching Wikipedia for '{query}'"
    else:
        target_url = f"https://www.google.com/search?q={q_encoded}"
        label = f"Searching Google for '{query}'"

    return open_url(target_url)

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
