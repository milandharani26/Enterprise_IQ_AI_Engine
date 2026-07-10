import asyncio
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
from engine.pipelines.ingestion.services.embedding_service import EmbeddingService
from engine.modules.database_connector.sql_generation import SqlGenerationService
from engine.modules.database_connector.sql_validator import SqlValidatorService
from engine.modules.database_connector.sql_executor import SqlExecutionService
from engine.modules.database_connector.response_formatter import SqlResponseFormatter
from engine.modules.database_connector.database_connector_models import SqlQueryLog
from engine.shared.models.connector_model import Connector

from shared.logging import get_logger
logger = get_logger("sql_query_tool")


class SqlQueryToolInput(BaseModel):
    """Input schema for SQL query tool."""

    question: str = Field(
        ..., description="Natural language question about database data"
    )


class SqlQueryTool(BaseTool):
    name = "sql_query"
    properties = ToolProperties(
        description="ALWAYS USE THIS TOOL to answer questions about databases, records, tables, or SQL. Pass the user's natural language question directly to this tool. The tool will automatically find the correct database, schema, and execute the query.",
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
        self._embedding_service = EmbeddingService()
        self._sql_generation = SqlGenerationService(config)

    async def _arun(self, question: str, ctx: ToolContext = None) -> str:
        print(f"\n{'=' * 50}\nDEBUG POINT: tool called")
        print(f"DEBUG POINT: user give this chat: {question}\n{'=' * 50}")
        logger.info("=" * 80)
        logger.info("SQL TOOL STARTED")
        logger.info(f"Question: {question}")
        logger.info(f"Organization ID: {ctx.organization_id if ctx else None}")
        logger.info(f"User ID: {ctx.user_id if ctx else None}")

        org_id_str = ctx.organization_id if ctx else None

        if not org_id_str:
            logger.error("Organization ID missing from context")
            return "Error: Organization ID not found in context."

        # Deterministic check for write/modify query attempts to avoid token usage
        question_clean = question.strip().lower()
        is_write_attempt = False
        if (
            (question_clean.startswith("insert ") and "into" in question_clean)
            or (question_clean.startswith("update ") and "set" in question_clean)
            or (question_clean.startswith("delete ") and "from" in question_clean)
            or question_clean.startswith("drop table")
            or question_clean.startswith("truncate ")
            or "insert into" in question_clean
            or "delete from" in question_clean
            or "update table" in question_clean
        ):
            is_write_attempt = True

        if is_write_attempt:
            logger.warning(f"Rejected write/modify query attempt: {question}")
            return "This assistant is read-only. Database modification queries (INSERT, UPDATE, DELETE, DROP) are not allowed."

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
                # STEP 2 - Embedding question
                print(f"DEBUG POINT: query pass for embadding: {question}")
                logger.info("STEP 2 - Embedding question")
                try:
                    self._embedding_service.org_id = UUID(org_id_str)
                    self._embedding_service.db = db
                    q_vec = await self._embedding_service.embed_query(question)
                    logger.info("Embedding completed successfully")
                except Exception as e:
                    err_msg = str(e)
                    if "rate limit" in err_msg.lower() or "429" in err_msg or "token" in err_msg.lower() or "limit" in err_msg.lower():
                        logger.error(f"Embedding failed due to API rate/token limit constraints: {e}")
                        raise Exception(f"Embedding failed (Rate/Token limit reached): {e}")
                    else:
                        logger.error(f"Embedding query failed: {e}")
                        raise Exception(f"Embedding query failed: {e}")

                # STEP 3 - Finding relevant database
                logger.info("STEP 3 - Finding relevant database")
                try:
                    db_ids = await DatabaseRetrievalService.find_relevant_database(
                        db,
                        q_vec,
                        org_id,
                        top_k=1,
                    )
                    logger.info(f"Database IDs found: {db_ids}")
                except Exception as e:
                    logger.error(f"Failed to query database schema catalog to find database: {e}")
                    raise Exception(f"Failed to locate relevant database in schema catalog: {e}")

                if not db_ids:
                    error_msg = "No database connections configured or found for this organization."
                    logger.error(error_msg)
                    return error_msg

                selected_db_id = db_ids[0]
                logger.info(f"Selected Database ID: {selected_db_id}")

                from sqlalchemy import select

                try:
                    db_obj = (
                        (
                            await db.execute(
                                select(Connector).where(Connector.id == selected_db_id)
                            )
                        )
                        .scalars()
                        .first()
                    )
                    if not db_obj:
                        raise ValueError(f"Database connector record for ID {selected_db_id} was not found in public.connectors.")
                    selected_db_name = db_obj.name
                    db_type = db_obj.connector_id
                    logger.info(f"Database Name: {selected_db_name}")
                    logger.info(f"Database Type: {db_type}")
                except Exception as e:
                    logger.error(f"Error fetching database connection metadata: {e}")
                    raise Exception(f"Failed to retrieve database connection metadata: {e}")

                # STEP 4 - Finding relevant tables
                logger.info("STEP 4 - Finding relevant tables")
                try:
                    table_names = await DatabaseRetrievalService.find_relevant_tables(
                        db,
                        q_vec,
                        org_id,
                        [selected_db_id],
                        top_k=3,
                    )
                    retrieved_tables = table_names
                    logger.info(f"Retrieved Tables: {table_names}")
                except Exception as e:
                    logger.error(f"Failed to find relevant tables: {e}")
                    raise Exception(f"Failed to query relevant tables: {e}")

                # STEP 5 - Building schema context
                logger.info("STEP 5 - Building schema context")
                try:
                    schema_context = await DatabaseRetrievalService.build_schema_context(
                        db,
                        org_id,
                        [selected_db_id],
                        table_names,
                        question=question,
                    )
                    logger.info(
                        f"Schema Context Length: {len(schema_context) if schema_context else 0}"
                    )
                except Exception as e:
                    logger.error(f"Failed to build database schema context: {e}")
                    raise Exception(f"Failed to build schema context: {e}")

                # STEP 6 - Generating SQL
                logger.info("STEP 6 - Generating SQL")
                try:
                    org_uuid = None
                    if org_id_str:
                        try:
                            org_uuid = UUID(org_id_str)
                        except Exception:
                            pass

                    generated_sql = await self._sql_generation.generate_sql(
                        question,
                        schema_context,
                        db_type,
                        guardrails,
                        conversation_history=ctx.conversation_history if ctx else None,
                        org_id=org_uuid,
                    )
                except Exception as e:
                    err_msg = str(e)
                    if "rate limit" in err_msg.lower() or "429" in err_msg or "token" in err_msg.lower() or "limit" in err_msg.lower():
                        logger.error(f"SQL Generation LLM query failed due to rate/token limits: {e}")
                        raise Exception(f"SQL Generation failed (Rate/Token limit reached on LLM): {e}")
                    else:
                        logger.error(f"SQL Generation LLM query failed: {e}")
                        raise Exception(f"SQL Generation failed: {e}")

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

                # STEP 7 - Validating SQL
                logger.info("STEP 7 - Validating SQL")
                print(f"DEBUG POINT: query validator called for sql: {generated_sql}")
                try:
                    is_valid, val_error = SqlValidatorService.validate_sql(generated_sql)
                    logger.info(f"SQL Valid: {is_valid}")
                    if not is_valid:
                        error_msg = val_error
                        logger.error(f"SQL Validation Failed: {val_error}")
                        return f"Failed to validate generated SQL: {val_error}"
                except Exception as e:
                    logger.error(f"SQL validation service threw exception: {e}")
                    raise Exception(f"SQL validation failed: {e}")

                # STEP 8 - Executing SQL
                logger.info("STEP 8 - Executing SQL")
                print(f"DEBUG POINT: about to execute SQL")
                try:
                    columns, rows, row_count = await SqlExecutionService.execute_query(
                        db,
                        selected_db_id,
                        org_id,
                        generated_sql,
                    )
                    print(
                        f"DEBUG POINT: execution done — rows={row_count}, columns={columns}"
                    )
                    logger.info(f"Rows Returned: {row_count}")
                except Exception as e:
                    logger.error(f"Database query execution phase failed: {e}")
                    raise Exception(f"Database execution failed: {e}")

                # STEP 9 - Formatting response
                logger.info("STEP 9 - Formatting response")
                try:
                    response_str = SqlResponseFormatter.format_response(
                        question,
                        columns,
                        rows,
                        row_count,
                    )
                    print(f"DEBUG POINT: formatted response = {response_str[:300]}")
                except Exception as e:
                    logger.error(f"Failed to format SQL execution response: {e}")
                    raise Exception(f"Failed to format response: {e}")

                success = True
                logger.info("SQL TOOL COMPLETED SUCCESSFULLY")
                return response_str

            except Exception as e:
                import traceback
                error_msg = str(e)
                logger.error("=" * 80)
                logger.error("SQL TOOL FAILED")
                logger.error(f"Error occurred: {e}")
                logger.error(traceback.format_exc())
                logger.error("=" * 80)
                return f"An error occurred executing the query: {e}"

            finally:
                logger.info("Writing SQL Query Log")

                exec_time_ms = int((time.time() - start_time) * 1000)

                log_entry = SqlQueryLog(
                    organization_id=org_id,
                    connector_id=selected_db_id,
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
