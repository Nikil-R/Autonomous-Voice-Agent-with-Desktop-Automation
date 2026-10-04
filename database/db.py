"""SQLite Database Engine with WAL mode connection management."""

import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.config import DB_PATH, SCHEMA_PATH

_lock = threading.Lock()

class DatabaseManager:
    """Thread-safe SQLite connection manager with WAL (Write-Ahead Logging) mode."""

    def __init__(self, db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Creates connection configured with WAL mode and fast pragmas."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable high-concurrency WAL mode & safety settings
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def init_db(self) -> None:
        """Initializes tables using schema.sql if not present."""
        if not self.schema_path.exists():
            return
        with _lock:
            with self.get_connection() as conn:
                with open(self.schema_path, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)
                conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes a read query and returns list of dictionaries."""
        with _lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

    def execute_write(self, statement: str, params: tuple = ()) -> int:
        """Executes an INSERT/UPDATE/DELETE statement and returns the lastrowid."""
        with _lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(statement, params)
                conn.commit()
                return cursor.lastrowid

    def log_telemetry_snapshot(self, cpu: float, ram_used: float, ram_total: float, disk_free: float, battery: Optional[float] = None) -> int:
        """Logs a single system telemetry snapshot."""
        sql = """
        INSERT INTO system_telemetry (cpu_percent, ram_used_gb, ram_total_gb, disk_free_gb, battery_percent)
        VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_write(sql, (cpu, ram_used, ram_total, disk_free, battery))

    def log_audit_event(self, event_type: str, details: str, success: bool = True) -> int:
        """Logs an audit event entry."""
        sql = """
        INSERT INTO audit_events (event_type, details, success)
        VALUES (?, ?, ?)
        """
        return self.execute_write(sql, (event_type, details, 1 if success else 0))

# Shared singleton instance
db_manager = DatabaseManager()
