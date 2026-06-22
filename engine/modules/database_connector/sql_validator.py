import sqlparse
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SqlValidatorService:
    # SQL operations that mutate data or schema, or execute functions
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 
        'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL', 
        'MERGE', 'REPLACE'
    }

    # Internal tables that should not be queried
    FORBIDDEN_TABLES = {
        'information_schema', 'pg_catalog', 'pg_toast', 'mysql', 
        'sys', 'performance_schema'
    }

    @classmethod
    def validate_sql(cls, sql_string: str) -> Tuple[bool, Optional[str]]:
        """
        Validates an LLM-generated SQL query for safety.
        Returns (is_valid, error_message).
        """
        if not sql_string or not sql_string.strip():
            return False, "Generated SQL is empty."

        # Check for guardrail violation signal from the generator
        if "GUARDRAIL_VIOLATION" in sql_string:
            return False, "This query was blocked by the assistant's security guardrails."

        # Strip out code blocks if the LLM hallucinated them despite instructions
        if sql_string.startswith("```"):
            lines = sql_string.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            sql_string = "\n".join(lines).strip()

        try:
            parsed = sqlparse.parse(sql_string)
            if not parsed:
                return False, "Could not parse SQL."

            # Reject multiple statements
            if len(parsed) > 1:
                return False, "Multiple SQL statements are not allowed."

            statement = parsed[0]
            stmt_type = statement.get_type().upper()

            # 1. Enforce SELECT or WITH
            if stmt_type not in ('SELECT', 'UNKNOWN'): 
                # sqlparse sometimes categorizes WITH queries as UNKNOWN
                # We do a secondary keyword check below
                pass

            # 2. Check all tokens
            for token in statement.flatten():
                if token.is_keyword:
                    kw = token.value.upper()
                    if kw in cls.FORBIDDEN_KEYWORDS:
                        return False, f"Forbidden SQL operation detected: {kw}"
                
                # Check for forbidden tables (simple substring match for safety)
                val = token.value.lower()
                for forbidden in cls.FORBIDDEN_TABLES:
                    if forbidden in val:
                        return False, "Access to system tables is forbidden."
            
            # Simple keyword scan as fallback
            upper_sql = sql_string.upper()
            for kw in cls.FORBIDDEN_KEYWORDS:
                if f" {kw} " in upper_sql or upper_sql.startswith(f"{kw} "):
                    return False, f"Forbidden SQL operation detected: {kw}"

            return True, None

        except Exception as e:
            logger.error(f"SQL validation error: {e}")
            return False, "An error occurred during SQL validation."
