"""Tools registry and dispatcher for ApexCore."""

import json
from typing import Dict, Any, Callable
from tools.schemas import TOOL_SCHEMAS
from tools.system_tools import get_system_vitals, get_top_processes
from tools.file_tools import (
    search_files,
    open_application,
    open_url,
    search_web_or_play,
    control_media_or_volume,
    open_folder_or_path,
    desktop_type_or_calculate,
    focus_window,
    control_chrome_tab_video,
    click_chrome_element,
    fill_chrome_search,
    capture_and_analyze_screen,
    click_on_visual_target
)
from tools.db_tools import query_local_db

TOOL_REGISTRY: Dict[str, Callable] = {
    "get_system_vitals": get_system_vitals,
    "get_top_processes": get_top_processes,
    "search_files": search_files,
    "open_application": open_application,
    "open_url": open_url,
    "search_web_or_play": search_web_or_play,
    "control_media_or_volume": control_media_or_volume,
    "open_folder_or_path": open_folder_or_path,
    "desktop_type_or_calculate": desktop_type_or_calculate,
    "focus_window": focus_window,
    "control_chrome_tab_video": control_chrome_tab_video,
    "click_chrome_element": click_chrome_element,
    "fill_chrome_search": fill_chrome_search,
    "capture_and_analyze_screen": capture_and_analyze_screen,
    "click_on_visual_target": click_on_visual_target,
    "query_local_db": query_local_db,
}

def dispatch_tool(name: str, arguments_str: str) -> str:
    """
    Parses arguments and safely calls the registered tool function.
    Returns the stringified JSON result.
    """
    func = TOOL_REGISTRY.get(name)
    if not func:
        return json.dumps({"error": f"Tool '{name}' not found in registry."})

    try:
        kwargs = json.loads(arguments_str) if arguments_str else {}
        if not isinstance(kwargs, dict):
            kwargs = {}
    except Exception as e:
        return json.dumps({"error": f"Invalid JSON arguments: {str(e)}"})

    try:
        result = func(**kwargs)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})

__all__ = ["TOOL_SCHEMAS", "TOOL_REGISTRY", "dispatch_tool"]
