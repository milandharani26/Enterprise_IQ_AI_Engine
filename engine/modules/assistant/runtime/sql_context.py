from typing import Any, Dict, Optional, Union
from uuid import UUID

def assistant_has_sql_tool(config_dict: Dict[str, Any]) -> bool:
    tools = config_dict.get("tools") or []
    return any(isinstance(t, dict) and (t.get("tool_id") == "sql_query" or t.get("id") == "sql_query") for t in tools)

SQL_WORKFLOW_INSTRUCTIONS = """
## SQL QUERY WORKFLOW

1. You MUST use the **sql_query** tool to answer ANY questions about database records, counts, tables, or structured data.
2. DO NOT just write the SQL query for the user. You MUST call the **sql_query** tool passing the user's natural language question so it can automatically run the query and give you the real data.
3. The tool will generate, validate, and execute the SQL query on your behalf and return the database results.
4. If the tool returns a GUARDRAIL_VIOLATION, inform the user that you cannot reveal that data.
5. Once you have the real data from the tool, use **emit_ui_blocks** to present it beautifully. If the data has multiple records or columns, you MUST emit a `table` block. If it is a single value (like a count), use a `markdown` block to answer in a natural sentence (e.g., "There are X users in the table.").
"""

def enrich_config_for_sql(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Appends nothing now because workflow is injected by simple_reactive.py."""
    return config_dict
