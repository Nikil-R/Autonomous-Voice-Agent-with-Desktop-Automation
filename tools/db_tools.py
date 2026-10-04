"""Database query tools for SQLite WAL mode."""

from typing import Dict, Any, List
from database.db import db_manager

def query_local_db(sql_query: str) -> Dict[str, Any]:
    """
    Safely executes a read-only SELECT query against SQLite in WAL mode.
    Rejects write/drop commands to prevent accidental corruption.
    """
    cleaned = sql_query.strip().lower()
    if not cleaned.startswith("select"):
        return {
            "success": False,
            "error": "Security constraint: Only read-only 'SELECT' queries are permitted."
        }

    # Forbidden modification keywords
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "create", "attach"]
    tokens = cleaned.split()
    for word in forbidden:
        if word in tokens:
            return {
                "success": False,
                "error": f"Security constraint: Statement contains prohibited keyword '{word}'."
            }

    try:
        rows: List[Dict[str, Any]] = db_manager.execute_query(sql_query)
        db_manager.log_audit_event("db_query", f"Query: {sql_query[:100]}", success=True)
        return {
            "success": True,
            "row_count": len(rows),
            "data": rows[:10]  # Limit to 10 rows for clean speech response
        }
    except Exception as e:
        db_manager.log_audit_event("db_query_error", f"Error on {sql_query}: {e}", success=False)
        return {
            "success": False,
            "error": f"SQL execution error: {str(e)}"
        }
