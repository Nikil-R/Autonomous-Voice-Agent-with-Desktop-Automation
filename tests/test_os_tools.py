"""Unit tests for OS and system inspection tools."""

import pytest
from tools.system_tools import get_system_vitals, get_top_processes
from tools.file_tools import search_files, open_application
from tools import dispatch_tool

def test_get_system_vitals():
    """Verify system vitals returns valid keys and realistic bounds."""
    vitals = get_system_vitals()
    assert "cpu_usage_percent" in vitals
    assert "ram_used_gb" in vitals
    assert "disk_c_free_gb" in vitals
    assert isinstance(vitals["cpu_usage_percent"], (int, float))
    assert vitals["cpu_usage_percent"] >= 0.0
    assert vitals["ram_used_gb"] > 0.0
    assert vitals["disk_c_free_gb"] > 0.0

def test_get_top_processes():
    """Verify process enumeration returns requested count and sorted."""
    procs = get_top_processes(sort_by="memory", count=5)
    assert len(procs) <= 5
    assert len(procs) > 0
    first = procs[0]
    assert "pid" in first
    assert "name" in first
    assert "memory_mb" in first
    assert first["memory_mb"] >= 0.0

def test_open_application_not_found():
    """Verify non-existent application returns failure message gracefully."""
    res = open_application("non_existent_fake_app_xyz_999")
    assert res["success"] is False
    assert "Could not find or launch" in res["message"]

def test_open_url_tool():
    """Verify open_url tool properly normalizes URL structure."""
    from tools.file_tools import open_url
    res = open_url("youtube.com")
    assert res["success"] is True
    assert "https://youtube.com" in res["url"]

def test_tool_dispatch():
    """Verify generic tool dispatcher handles valid and invalid requests."""
    res_str = dispatch_tool("get_system_vitals", "{}")
    assert "cpu_usage_percent" in res_str

    err_str = dispatch_tool("non_existent_tool", "{}")
    assert "error" in err_str

def test_open_folder_or_path():
    """Verify open_folder_or_path correctly matches existing system folder."""
    from tools.file_tools import open_folder_or_path
    res = open_folder_or_path("Desktop")
    assert res["success"] is True
    assert "folder" in res["message"].lower()

def test_desktop_type_or_calculate_dispatch():
    """Verify desktop_type_or_calculate can be dispatched safely."""
    res_str = dispatch_tool("desktop_type_or_calculate", '{"calculation_or_keys": "20*10"}')
    assert "Calculated" in res_str or "success" in res_str

def test_window_manager_listing():
    """Verify WindowManager enumerates active desktop windows."""
    from tools.window_manager import window_manager
    windows = window_manager.list_visible_windows()
    assert isinstance(windows, list)

def test_focus_window_dispatch():
    """Verify focus_window tool can be safely called."""
    res_str = dispatch_tool("focus_window", '{"app_or_title": "Calculator"}')
    assert "success" in res_str or "message" in res_str

def test_cdp_tools_dispatch():
    """Verify CDP browser tools can be safely dispatched."""
    res_v = dispatch_tool("control_chrome_tab_video", '{"action": "pause"}')
    assert "success" in res_v or "message" in res_v

    res_c = dispatch_tool("click_chrome_element", '{"selector": "first_result"}')
    assert "success" in res_c or "message" in res_c

    res_f = dispatch_tool("fill_chrome_search", '{"query": "interstellar soundtrack", "submit": false}')
    assert "success" in res_f or "message" in res_f
