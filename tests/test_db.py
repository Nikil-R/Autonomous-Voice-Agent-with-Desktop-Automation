"""Unit tests for SQLite WAL database manager and security constraints."""

import pytest
from database.db import DatabaseManager
from tools.db_tools import query_local_db

def test_database_wal_mode(tmp_path):
    """Verify SQLite database enables WAL mode and handles writes/reads."""
    db_file = tmp_path / "test_apex.db"
    schema_file = tmp_path / "test_schema.sql"
    schema_file.write_text(
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY, msg TEXT);"
    )

    db = DatabaseManager(db_path=db_file, schema_path=schema_file)
    
    # Check WAL mode
    with db.get_connection() as conn:
        res = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert res.lower() == "wal"

    # Test write & read
    db.execute_write("INSERT INTO test_table (msg) VALUES (?);", ("ApexCore test",))
    rows = db.execute_query("SELECT * FROM test_table;")
    assert len(rows) == 1
    assert rows[0]["msg"] == "ApexCore test"

def test_query_local_db_security():
    """Verify write or injection attempts are blocked by query_local_db."""
    # Attempting DROP
    res = query_local_db("DROP TABLE system_telemetry;")
    assert res["success"] is False
    assert "Security constraint" in res["error"]

    # Attempting INSERT
    res2 = query_local_db("INSERT INTO audit_events (event_type) VALUES ('hack');")
    assert res2["success"] is False
    assert "Security constraint" in res2["error"]

    # Valid SELECT
    res3 = query_local_db("SELECT 1 as num;")
    assert res3["success"] is True
    assert res3["data"][0]["num"] == 1
