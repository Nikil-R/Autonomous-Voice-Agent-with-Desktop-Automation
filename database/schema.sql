-- ApexCore SQLite Database Schema
-- Optimized for high-concurrency WAL mode

CREATE TABLE IF NOT EXISTS system_telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_percent REAL NOT NULL,
    ram_used_gb REAL NOT NULL,
    ram_total_gb REAL NOT NULL,
    disk_free_gb REAL NOT NULL,
    battery_percent REAL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    details TEXT,
    success INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS conversation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_transcript TEXT,
    assistant_response TEXT,
    vad_ms REAL,
    stt_ms REAL,
    ttft_ms REAL,
    ttfa_ms REAL,
    barge_in_triggered INTEGER DEFAULT 0
);

-- Indexing for rapid time-series analysis
CREATE INDEX IF NOT EXISTS idx_telemetry_time ON system_telemetry(recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);
