"""System inspection and process management tools."""

import psutil
import shutil
from typing import Dict, Any, List
from database.db import db_manager

def get_system_vitals() -> Dict[str, Any]:
    """
    Retrieves real-time system performance metrics:
    CPU %, RAM utilized vs free (GB), Disk C: free space (GB), Battery %.
    Also persists a telemetry snapshot to SQLite WAL database.
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("C:\\")
    battery = psutil.sensors_battery()

    ram_used_gb = round((vm.total - vm.available) / (1024 ** 3), 2)
    ram_total_gb = round(vm.total / (1024 ** 3), 2)
    ram_percent = vm.percent

    disk_free_gb = round(disk.free / (1024 ** 3), 2)
    disk_total_gb = round(disk.total / (1024 ** 3), 2)

    battery_percent = round(battery.percent, 1) if battery else None
    power_plugged = battery.power_plugged if battery else None

    # Persist in SQLite WAL
    try:
        db_manager.log_telemetry_snapshot(
            cpu=cpu_percent,
            ram_used=ram_used_gb,
            ram_total=ram_total_gb,
            disk_free=disk_free_gb,
            battery=battery_percent
        )
    except Exception:
        pass

    return {
        "cpu_usage_percent": cpu_percent,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "ram_percent": ram_percent,
        "disk_c_free_gb": disk_free_gb,
        "disk_c_total_gb": disk_total_gb,
        "battery_percent": battery_percent,
        "power_plugged": power_plugged
    }

def get_top_processes(sort_by: str = "memory", count: int = 5) -> List[Dict[str, Any]]:
    """
    Enumerates running Windows processes sorted by memory consumption (RAM) or CPU usage.
    Filters out system idle and zero-value background processes.
    """
    count = min(max(1, count), 10)
    sort_key = "memory_percent" if sort_by.lower() == "memory" else "cpu_percent"
    
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'memory_percent', 'cpu_percent']):
        try:
            info = proc.info
            name = info.get('name') or ''
            if not name or name.lower() in ('system idle process', 'system', 'registry'):
                continue
            
            mem_mb = round(info['memory_info'].rss / (1024 * 1024), 1) if info.get('memory_info') else 0.0
            processes.append({
                "pid": info['pid'],
                "name": name,
                "memory_mb": mem_mb,
                "memory_percent": round(info.get('memory_percent') or 0.0, 1),
                "cpu_percent": round(info.get('cpu_percent') or 0.0, 1)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sort_by.lower() == "memory":
        processes.sort(key=lambda p: p['memory_mb'], reverse=True)
    else:
        processes.sort(key=lambda p: p['cpu_percent'], reverse=True)

    return processes[:count]
