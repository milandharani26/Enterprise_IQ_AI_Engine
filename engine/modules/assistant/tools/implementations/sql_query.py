import asyncio
import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from engine.modules.assistant.tools.base_tool import (
    BaseTool,
    ToolContext,
    ToolProperties,
    ToolCategory,
)
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

    question: str = Field(
        ..., description="Natural language question about database data"
    )


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
""",
    )

    def __init__(
        self,
        config: Dict[str, Any] = None,
        credential_id: Optional[str] = None,
        usage_instructions: Optional[str] = None,
    ):
        super().__init__(
            config=config,
            credential_id=credential_id,
            usage_instructions=usage_instructions,
        )
        self._embedding_service = SchemaEmbeddingService()
        self._sql_generation = SqlGenerationService(config)

    async def _arun(self, question: str, ctx: ToolContext = None) -> str:
        logger.info("=" * 80)
        logger.info("SQL TOOL STARTED")
        logger.info(f"Question: {question}")
        logger.info(f"Organization ID: {ctx.organization_id if ctx else None}")
        logger.info(f"User ID: {ctx.user_id if ctx else None}")

        org_id_str = ctx.organization_id if ctx else None

        if not org_id_str:
            logger.error("Organization ID missing from context")
            return "Error: Organization ID not found in context."

        org_id = UUID(str(org_id_str))
        user_id = UUID(str(ctx.user_id)) if ctx and ctx.user_id else None

        guardrails = (
            ctx.guardrails
            if ctx and hasattr(ctx, "guardrails") and ctx.guardrails
            else ""
        )

        logger.info(f"Guardrails Present: {bool(guardrails)}")

        logger.info("STEP 1 - Running guardrail check")
        passed = await self._sql_generation.pre_generate_guardrail_check(
            question, guardrails
        )

        logger.info(f"Guardrail Result: {passed}")

        if not passed:
            logger.warning("Query blocked by guardrails")
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
                logger.info("STEP 2 - Embedding question")
                q_vec = await self._embedding_service._embed_text(question)
                logger.info("Embedding completed")

                logger.info("STEP 3 - Finding relevant database")
                db_ids = await DatabaseRetrievalService.find_relevant_database(
                    db,
                    q_vec,
                    org_id,
                    top_k=1,
                )

                logger.info(f"Database IDs found: {db_ids}")

                if not db_ids:
                    error_msg = "No database connections configured or found for this organization."
                    logger.error(error_msg)
                    return error_msg

                selected_db_id = db_ids[0]

                logger.info(f"Selected Database ID: {selected_db_id}")

                from sqlalchemy import select

                db_obj = (
                    (
                        await db.execute(
                            select(DatabaseConnection).where(
                                DatabaseConnection.id == selected_db_id
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                if db_obj:
                    selected_db_name = db_obj.name
                    db_type = db_obj.database_type

                    logger.info(f"Database Name: {selected_db_name}")
                    logger.info(f"Database Type: {db_type}")
                else:
                    raise Exception("Database connection vanished during retrieval.")

                logger.info("STEP 4 - Finding relevant tables")

                table_names = await DatabaseRetrievalService.find_relevant_tables(
                    db,
                    q_vec,
                    org_id,
                    [selected_db_id],
                    top_k=5,
                )

                retrieved_tables = table_names

                logger.info(f"Retrieved Tables: {table_names}")

                logger.info("STEP 5 - Building schema context")

                schema_context = await DatabaseRetrievalService.build_schema_context(
                    db,
                    org_id,
                    [selected_db_id],
                    table_names,
                )

                logger.info(
                    f"Schema Context Length: {len(schema_context) if schema_context else 0}"
                )

                logger.info("STEP 6 - Generating SQL")

                generated_sql = await self._sql_generation.generate_sql(
                    question,
                    schema_context,
                    db_type,
                    guardrails,
                )

                logger.info("=" * 50)
                logger.info("GENERATED SQL")
                logger.info(generated_sql)
                logger.info("=" * 50)

                if "GUARDRAIL_VIOLATION" in generated_sql:
                    error_msg = (
                        "This query was blocked by the assistant's security guardrails."
                    )
                    logger.warning(error_msg)
                    return error_msg

                logger.info("STEP 7 - Validating SQL")

                is_valid, val_error = SqlValidatorService.validate_sql(generated_sql)

                logger.info(f"SQL Valid: {is_valid}")

                if not is_valid:
                    error_msg = val_error
                    logger.error(f"SQL Validation Failed: {val_error}")
                    return f"Failed to validate generated SQL: {val_error}"

                logger.info("STEP 8 - Executing SQL")

                columns, rows, row_count = await SqlExecutionService.execute_query(
                    db,
                    selected_db_id,
                    org_id,
                    generated_sql,
                )

                logger.info(f"Rows Returned: {row_count}")

                logger.info("STEP 9 - Formatting response")

                response_str = SqlResponseFormatter.format_response(
                    question,
                    columns,
                    rows,
                    row_count,
                )

                success = True

                logger.info("SQL TOOL COMPLETED SUCCESSFULLY")

                return response_str

            except Exception as e:
                import traceback

                error_msg = str(e)

                logger.error("=" * 80)
                logger.error("SQL TOOL FAILED")
                logger.error(f"Error: {e}")
                logger.error(traceback.format_exc())
                logger.error("=" * 80)

                return f"An error occurred executing the query: {e}"

            finally:
                logger.info("Writing SQL Query Log")

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
                    error_message=error_msg,
                )

                db.add(log_entry)
                await db.commit()

                logger.info("SQL Query Log Saved")

    def _run(self, *args, **kwargs) -> Any:
        raise NotImplementedError("SqlQueryTool only supports async execution.")
