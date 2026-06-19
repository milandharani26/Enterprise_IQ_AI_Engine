from typing import Any, Dict, Optional, Union
from uuid import UUID

def assistant_has_sql_tool(config_dict: Dict[str, Any]) -> bool:
    tools = config_dict.get("tools") or []
    return any(isinstance(t, dict) and t.get("tool_id") == "sql_query" for t in tools)

def enrich_config_for_sql(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Append SQL specific instructions to the system prompt if the tool is present."""
    cfg = dict(config_dict)
    instruction = (cfg.get("system_instruction") or "").strip()

    sql_instructions = """
## SQL QUERY WORKFLOW (required when sql_query is available)

1. Use the **sql_query** tool to answer questions about structured data in connected databases (e.g., records, sales, users, tables).
2. The tool automatically enforces all of your security guardrails, so you can safely pass the user's question to the tool.
3. The tool will generate, validate, and execute the SQL query on your behalf.
4. If the tool returns a GUARDRAIL_VIOLATION or tells you the query was blocked, inform the user that you cannot reveal that data.
5. Format the answer in markdown and call **emit_ui_blocks** once with the final text.
"""

    if "SQL QUERY WORKFLOW" not in instruction:
        cfg["system_instruction"] = f"{instruction}\n\n{sql_instructions}"
        
    return cfg
