import logging
from typing import Optional, Dict, Any

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
        # Concatenate all text blocks in order
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    # Fallback: coerce to string
    return str(content)


class SqlGenerationService:
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        # We enforce a slightly longer max_tokens for SQL generation
        if llm_config is None:
            llm_config = {}
        llm_config.setdefault("max_tokens", 1024)

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

        prompt = PromptTemplate.from_template(
            "You are a strict security guard. Read the user's question and the security guardrails.\n"
            "Guardrails: {guardrails}\n"
            "Question: {question}\n\n"
            "Does the question violate the guardrails? Reply strictly with YES or NO."
        )

        chain = prompt | self.llm
        try:
            result = await chain.ainvoke(
                {"question": question, "guardrails": guardrails}
            )
            # FIX: use _extract_text() so this works whether content is a str or a list
            answer = _extract_text(result.content).strip().upper()
            if "YES" in answer:
                logger.warning(f"Guardrail violation detected for question: {question}")
                return False
            return True
        except Exception as e:
            logger.error(f"Guardrail check failed: {e}")
            return True  # Fail open if LLM fails, the main generator will also have guardrails

    async def generate_sql(
        self,
        question: str,
        schema_context: str,
        database_type: str,
        guardrails: Optional[str] = None,
    ) -> str:
        """
        Generates the SQL query based on the database schema and question, enforcing guardrails.
        """
        system_instructions = (
            "You are an expert SQL Data Analyst. Your job is to write a syntactically correct "
            "{database_type} query to answer the user's question.\n"
            "Use ONLY the tables and columns provided in the schema context below.\n\n"
            "SCHEMA CONTEXT:\n{schema_context}\n\n"
        )

        if guardrails:
            system_instructions += (
                "CRITICAL SECURITY GUARDRAILS:\n"
                "You must strictly follow these rules. If the user's question asks for data "
                "prohibited by these rules, you MUST output the exact string: "
                "'GUARDRAIL_VIOLATION' instead of a SQL query.\n"
                "{guardrails}\n\n"
            )

        system_instructions += (
            "RULES:\n"
            "1. Output ONLY the raw SQL query without any markdown formatting, backticks, or explanations.\n"
            "2. Ensure the query is read-only (SELECT only).\n"
            "3. Limit the results to 100 rows maximum if no specific limit is requested.\n"
            '4. ALWAYS use double quotes around ALL table and column names (e.g., "createdAt") to preserve case sensitivity.\n'
        )

        prompt = PromptTemplate.from_template(
            system_instructions + "USER QUESTION: {question}\nSQL QUERY:"
        )

        chain = prompt | self.llm
        try:
            result = await chain.ainvoke(
                {
                    "question": question,
                    "schema_context": schema_context,
                    "database_type": database_type.upper(),
                    "guardrails": guardrails or "",
                }
            )
            # FIX: use _extract_text() so this works whether content is a str or a list
            return _extract_text(result.content).strip()
        except Exception as e:
            logger.error(f"SQL Generation failed: {e}")
            raise
