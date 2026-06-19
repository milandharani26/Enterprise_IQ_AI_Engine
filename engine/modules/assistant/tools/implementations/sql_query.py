import asyncio
import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from engine.modules.assistant.tools.base_tool import BaseTool, ToolContext, ToolProperties, ToolCategory
from engine.modules.assistant.tools.exceptions import ToolExecutionError
from engine.shared.db.session import AsyncSessionLocal

from engine.modules.database_connector.retrieval_service import DatabaseRetrievalService
from engine.modules.database_connector.embedding_service import SchemaEmbeddingService
from engine.modules.database_connector.sql_generation import SqlGenerationService
from engine.modules.database_connector.sql_validator import SqlValidatorService
from engine.modules.database_connector.sql_executor import SqlExecutionService
from engine.modules.database_connector.response_formatter import SqlResponseFormatter
from engine.modules.database_connector.models import SqlQueryLog, DatabaseConnection

logger = logging.getLogger(__name__)

class SqlQueryToolInput(BaseModel):
    """Input schema for SQL query tool."""
    question: str = Field(..., description="Natural language question about database data")


class SqlQueryTool(BaseTool):
    name = "sql_query"
    properties = ToolProperties(
        description="Query connected SQL databases using natural language.",
        category=ToolCategory.BUSINESS,
        input_schema=SqlQueryToolInput,
        required_connectors=["database"],
        risk_level="medium",
        default_instructions="""### SQL_QUERY (Natural Language Database Query)

**Purpose:** Query connected SQL databases using natural language.

**When to use:**
- Any question about database records, sales, employees, structured transactional data.

**Input Parameter:**
- question (str, required): Natural language question.
"""
    )

    def __init__(self, config: Dict[str, Any] = None, credential_id: Optional[str] = None, usage_instructions: Optional[str] = None):
        super().__init__(config=config, credential_id=credential_id, usage_instructions=usage_instructions)
        self._embedding_service = SchemaEmbeddingService()
        self._sql_generation = SqlGenerationService(config)

    async def _run_async(self, question: str, context: ToolContext = None) -> str:
        org_id_str = context.organization_id if context else None
        if not org_id_str:
            return "Error: Organization ID not found in context."

        org_id = UUID(str(org_id_str))
        user_id = UUID(str(context.user_id)) if context and context.user_id else None
        
        # We need the assistant's specific guardrails
        guardrails = context.guardrails if context and hasattr(context, 'guardrails') and context.guardrails else ""

        # 1. Guardrail pre-check
        passed = await self._sql_generation.pre_generate_guardrail_check(question, guardrails)
        if not passed:
            return "Query blocked by security guardrails. You do not have permission to ask this question."

        start_time = time.time()
        selected_db_id = None
        selected_db_name = None
        retrieved_tables = []
        generated_sql = None
        success = False
        error_msg = None
        row_count = 0

        async with AsyncSessionLocal() as db:
            try:
                # 2. Embed question
                q_vec = await self._embedding_service._embed_text(question)

                # 3. Find relevant database
                db_ids = await DatabaseRetrievalService.find_relevant_database(db, q_vec, org_id, top_k=1)
                if not db_ids:
                    error_msg = "No database connections configured or found for this organization."
                    return error_msg

                selected_db_id = db_ids[0]

                # Fetch db name for logging
                from sqlalchemy import select
                db_obj = (await db.execute(select(DatabaseConnection).where(DatabaseConnection.id == selected_db_id))).scalars().first()
                if db_obj:
                    selected_db_name = db_obj.name
                    db_type = db_obj.database_type
                else:
                    raise Exception("Database connection vanished during retrieval.")

                # 4. Find relevant tables
                table_names = await DatabaseRetrievalService.find_relevant_tables(db, q_vec, org_id, [selected_db_id], top_k=5)
                retrieved_tables = table_names

                # 5. Build schema context
                schema_context = await DatabaseRetrievalService.build_schema_context(db, org_id, [selected_db_id], table_names)

                # 6. Generate SQL
                generated_sql = await self._sql_generation.generate_sql(question, schema_context, db_type, guardrails)
                
                if "GUARDRAIL_VIOLATION" in generated_sql:
                    error_msg = "This query was blocked by the assistant's security guardrails."
                    return error_msg

                # 7. Validate SQL
                is_valid, val_error = SqlValidatorService.validate_sql(generated_sql)
                if not is_valid:
                    error_msg = val_error
                    return f"Failed to validate generated SQL: {val_error}"

                # 8. Execute SQL
                columns, rows, row_count = await SqlExecutionService.execute_query(db, selected_db_id, org_id, generated_sql)
                
                # 9. Format response
                response_str = SqlResponseFormatter.format_response(question, columns, rows, row_count)
                success = True
                return response_str

            except Exception as e:
                error_msg = str(e)
                logger.error(f"SqlQueryTool failed: {e}")
                return f"An error occurred executing the query: {e}"
            
            finally:
                # 10. Log Query
                exec_time_ms = int((time.time() - start_time) * 1000)
                log_entry = SqlQueryLog(
                    organization_id=org_id,
                    database_connection_id=selected_db_id,
                    user_id=user_id,
                    question=question,
                    generated_sql=generated_sql,
                    selected_database=selected_db_name,
                    retrieved_tables=retrieved_tables,
                    execution_time_ms=exec_time_ms,
                    row_count=row_count,
                    success=success,
                    error_message=error_msg
                )
                db.add(log_entry)
                await db.commit()

    def _run(self, *args, **kwargs) -> Any:
        raise NotImplementedError("SqlQueryTool only supports async execution.")
