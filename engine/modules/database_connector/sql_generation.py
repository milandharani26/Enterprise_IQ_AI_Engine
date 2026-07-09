import logging
from typing import Optional, Dict, Any
from uuid import UUID

from langchain_core.prompts import PromptTemplate
from engine.modules.assistant.runtime.llm_initializer import initialize_llm

logger = logging.getLogger(__name__)


def _extract_text(content) -> str:
    """
    Safely extract a plain string from an LLM result's content field.

    Newer versions of LangChain return `result.content` as a list of content
    blocks when using Anthropic models, e.g.:
        [{"type": "text", "text": "SELECT ..."}]

    Older versions (and OpenAI-backed chains) return a plain string.
    This helper handles both shapes so the rest of the code can always call
    .strip() on a string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


class SqlGenerationService:
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        if llm_config is None:
            llm_config = {}
        llm_config.setdefault("max_tokens", 1024)
        self.llm_config = llm_config
        self.llm = initialize_llm(llm_config)

    async def pre_generate_guardrail_check(
        self, question: str, guardrails: str
    ) -> bool:
        """
        Fast pass to check if the question violates the assistant's specific guardrails
        before we even attempt to write SQL.
        """
        if not guardrails or not guardrails.strip():
            return True

        import re

        question_lower = question.lower()
        question_clean = re.sub(r"[^a-z0-9\s]", " ", question_lower)
        question_words = set(question_clean.split())

        def matches_keyword(word: str, keyword: str) -> bool:
            if word == keyword:
                return True
            if word + "s" == keyword or keyword + "s" == word:
                return True
            if keyword.endswith("y") and word == keyword[:-1] + "ies":
                return True
            if word.endswith("y") and keyword == word[:-1] + "ies":
                return True
            return False

        stopwords = {
            "do", "not", "give", "any", "information", "about", "table",
            "database", "show", "disclose", "list", "view", "get", "retrieve",
            "select", "a", "an", "the", "of", "in", "on", "with", "from",
            "to", "for", "please", "strict", "block", "rule", "rules", "must",
            "adhere", "strictly", "should", "only", "never", "cannot", "can",
            "could", "would", "will", "no", "yes", "details", "detail", "data",
            "record", "records", "row", "rows", "column", "columns", "field",
            "fields", "value", "values",
        }

        lines = guardrails.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            clean_line = re.sub(r"^[-*#\s\d\.]+", "", line)
            clean_line = re.sub(r"^\[.*?\]\s*", "", clean_line)
            clean_line = re.sub(r"^\(.*?\)\s*:\s*", "", clean_line)
            clean_line = re.sub(r"^:\s*", "", clean_line)
            words = re.sub(r"[^a-z0-9\s]", " ", clean_line.lower()).split()
            keywords = [w for w in words if w not in stopwords and len(w) > 1]
            if not keywords:
                continue
            for kw in keywords:
                for qw in question_words:
                    if matches_keyword(qw, kw):
                        logger.warning(
                            f"Guardrail violation detected (keyword '{kw}'): "
                            f"rule='{line}', question='{question}'"
                        )
                        return False

        return True

    async def generate_sql(
        self,
        question: str,
        schema_context: str,
        database_type: str,
        guardrails: Optional[str] = None,
        conversation_history: Optional[list] = None,
        org_id: Optional[UUID] = None,
    ) -> str:
        """
        Generates an accurate SQL query from a natural language question.
        conversation_history provides recent turns so the LLM can resolve
        follow-up references like 'whose details is this?' or 'my role'.
        """
        llm = self.llm
        if org_id:
            try:
                llm = initialize_llm(self.llm_config, org_id)
            except Exception as e:
                logger.error(f"[SqlGeneration] Failed to initialize dynamic LLM: {e}")

        system_instructions = (
            "You are an expert {database_type} SQL query writer.\n"
            "Your ONLY job is to output a single, correct, read-only SQL SELECT query.\n"
            "Use ONLY the tables, columns, and relationships provided in the SCHEMA CONTEXT below.\n\n"

            # ----------------------------------------------------------------
            # SCHEMA
            # ----------------------------------------------------------------
            "SCHEMA CONTEXT:\n{schema_context}\n\n"
        )

        if guardrails:
            system_instructions += (
                "SECURITY GUARDRAILS:\n"
                "If the question asks for data that violates any rule below, "
                "output the exact string GUARDRAIL_VIOLATION and nothing else.\n"
                "{guardrails}\n\n"
            )

        system_instructions += (
            # ----------------------------------------------------------------
            # CORE OUTPUT RULES
            # ----------------------------------------------------------------
            "OUTPUT RULES:\n"
            "1. Output ONLY the raw SQL query — no markdown, no backticks, no explanation.\n"
            "2. SELECT only — never INSERT, UPDATE, DELETE, DROP, or TRUNCATE.\n"
            "3. Default LIMIT 15 unless the user specifies a different number.\n"
            "4. ALWAYS double-quote every table and column name to preserve case: \"full_name\", \"createdAt\".\n"
            "5. ALWAYS prefix tables with their schema: \"public\".\"users\", not just \"users\".\n\n"

            # ----------------------------------------------------------------
            # TEXT & NAME MATCHING
            # ----------------------------------------------------------------
            "TEXT SEARCH RULES:\n"
            "6. NEVER use exact equality (=) for name or text searches.\n"
            "   Always use case-insensitive search:\n"
            "   CORRECT:  WHERE LOWER(\"full_name\") LIKE LOWER('%Priyank%')\n"
            "   WRONG:    WHERE \"full_name\" = 'Priyank'\n"
            "7. If the user gives a full name (e.g. 'Priyank Godhani'), split and match each word:\n"
            "   WHERE LOWER(\"full_name\") LIKE '%priyank%' AND LOWER(\"full_name\") LIKE '%godhani%'\n"
            "8. If multiple name-like columns exist (full_name, first_name, last_name, user_name),\n"
            "   search ALL of them with OR:\n"
            "   WHERE LOWER(\"full_name\") LIKE '%value%'\n"
            "      OR LOWER(\"first_name\") LIKE '%value%'\n"
            "      OR LOWER(\"last_name\") LIKE '%value%'\n\n"

            # ----------------------------------------------------------------
            # COLUMN MAPPING
            # ----------------------------------------------------------------
            "COLUMN MAPPING RULES:\n"
            "9. NEVER assume column names — use ONLY what is in the schema context.\n"
            "10. Common user terms map to these column patterns (verify against schema first):\n"
            "    'name'     → full_name, user_name, first_name, last_name, name\n"
            "    'email'    → email, email_address, user_email\n"
            "    'role'     → role_name, role_id, user_role\n"
            "    'status'   → is_active, status, account_status\n"
            "    'date'     → created_at, createdAt, updated_at, date_of_birth\n"
            "    'phone'    → phone, phone_number, mobile\n"
            "11. If you cannot find a matching column in the schema, do NOT guess.\n"
            "    Instead output: SELECT 'COLUMN_NOT_FOUND' AS error\n\n"

            # ----------------------------------------------------------------
            # JOIN RULES
            # ----------------------------------------------------------------
            "JOIN RULES:\n"
            "12. If the answer requires data from multiple tables, always JOIN them.\n"
            "    Use the relationships in the schema context to find the correct keys.\n"
            "13. Always use table aliases for clarity in JOINs:\n"
            "    SELECT u.\"full_name\", r.\"role_name\"\n"
            "    FROM \"public\".\"users\" u\n"
            "    JOIN \"public\".\"roles\" r ON u.\"role_id\" = r.\"role_id\"\n"
            "14. Use LEFT JOIN when the related record might not exist (e.g. a user might have no role).\n"
            "15. Never use implicit joins (comma-separated tables in FROM). Always use explicit JOIN.\n\n"

            # ----------------------------------------------------------------
            # NULL & EMPTY HANDLING
            # ----------------------------------------------------------------
            "NULL HANDLING RULES:\n"
            "16. For soft-deleted tables, always filter out deleted rows:\n"
            "    WHERE \"deletedAt\" IS NULL   (or deleted_at IS NULL)\n"
            "17. If checking for active records, add: WHERE \"is_active\" = true\n\n"

            # ----------------------------------------------------------------
            # AGGREGATION
            # ----------------------------------------------------------------
            "AGGREGATION RULES:\n"
            "18. For 'count', 'total', 'how many' questions use COUNT(*) with a clear alias:\n"
            "    SELECT COUNT(*) AS \"total_users\" FROM \"public\".\"users\"\n"
            "19. Always add GROUP BY when selecting a non-aggregated column alongside an aggregate.\n\n"
        )

        # ----------------------------------------------------------------
        # CONVERSATION HISTORY BLOCK
        # ----------------------------------------------------------------
        history_block = ""
        if conversation_history:
            logger.info(
                "[SqlGeneration] Injecting %d history messages into prompt",
                len(conversation_history),
            )
            lines = []
            for msg in conversation_history:
                role_label = "User" if msg.get("role") == "user" else "Assistant"
                lines.append(f"{role_label}: {msg.get('content', '').strip()}")
            if lines:
                history_block = (
                    "CONVERSATION HISTORY:\n"
                    "Use the exchanges below to resolve references in the current question.\n"
                    "- If the user stated their name (e.g. 'I am Priyank Godhani') → use it as a WHERE filter\n"
                    "- Replace 'my', 'their', 'same person', 'whose' with the actual name/value from history\n"
                    "- If a previous query returned specific names/IDs, use them when the user says 'that person' or 'same one'\n"
                    "- NEVER use placeholder values like 'current_user' or 'user_id_placeholder'\n\n"
                    + "\n".join(lines)
                    + "\n\n"
                    "Now write the SQL for the CURRENT question using the above context.\n\n"
                )
        else:
            logger.info(
                "[SqlGeneration] No conversation history — generating SQL without context"
            )

        prompt = PromptTemplate.from_template(
            system_instructions
            + "{history_block}"
            + "CURRENT QUESTION: {question}\n"
            + "SQL QUERY:"
        )

        chain = prompt | llm
        try:
            result = await chain.ainvoke(
                {
                    "question": question,
                    "schema_context": schema_context,
                    "database_type": database_type.upper(),
                    "guardrails": guardrails or "",
                    "history_block": history_block,
                }
            )
            return _extract_text(result.content).strip()
        except Exception as e:
            logger.error(f"SQL Generation failed: {e}")
            raise