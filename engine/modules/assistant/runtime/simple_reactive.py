"""Simple reactive assistant type with LangChain agent + tools."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

# FIX: create_agent does not exist — correct import is create_react_agent
from langgraph.prebuilt import create_react_agent

from engine.modules.assistant.runtime.llm_initializer import initialize_llm
from engine.modules.assistant.tools.base_tool import BaseTool, ToolContext
from engine.modules.assistant.tools.tool_registry import ToolRegistryNew
from engine.modules.assistant.runtime.rag_context import RAG_WORKFLOW_INSTRUCTIONS
from engine.modules.assistant.runtime.drive_context import DRIVE_WORKFLOW_INSTRUCTIONS
from engine.modules.assistant.runtime.sql_context import SQL_WORKFLOW_INSTRUCTIONS
from engine.modules.assistant.tools.exceptions import LLMInitializationError

logger = logging.getLogger(__name__)


class SimpleReactiveType:
    def get_type_id(self) -> str:
        return "simple_reactive"

    def _get_tools(self, tools_config: List[Dict[str, Any]] = None) -> List[BaseTool]:
        tools: List[BaseTool] = []
        for t in tools_config or []:
            tool_id = t.get("id") or t.get("tool_id")
            if isinstance(t, dict) and tool_id:
                tool_class = ToolRegistryNew.get_tool(tool_id)
                if tool_class:
                    tools.append(
                        tool_class(
                            config=t.get("config", {}),
                            credential_id=t.get("credential_id") or t.get("credential"),
                            usage_instructions=t.get("usage_instructions")
                            or t.get("instructions")
                            or "",
                        )
                    )

        return tools

    def get_system_instruction(
        self, config_dict: Dict[str, Any], tools: List[BaseTool]
    ) -> str:
        base = (
            config_dict.get("system_prompt")
            or config_dict.get("system_instruction")
            or ""
        )

        guardrails_config = config_dict.get("guardrails") or []
        if guardrails_config:
            base += (
                "\n\n## GUARDRAILS\nYou MUST adhere strictly to the following rules:\n"
            )
            for g in guardrails_config:
                if g.get("enabled", True):
                    base += f"- [{g.get('type')}] ({g.get('enforcement')}): {g.get('instructions')}\n"

        tool_text = "\n## AVAILABLE TOOLS\n\n"
        for tool in tools:
            tool_text += f"### {tool.name.upper()}\n{tool.get_instruction()}\n\n"

        workflow = ""
        if any(t.name == "rag_search" for t in tools):
            workflow += RAG_WORKFLOW_INSTRUCTIONS
        if any(t.name == "drive_search" for t in tools):
            workflow += DRIVE_WORKFLOW_INSTRUCTIONS
        if any(t.name == "sql_query" for t in tools):
            workflow += SQL_WORKFLOW_INSTRUCTIONS

        if not workflow:
            workflow = (
                "\n## WORKFLOW\n"
                "1. Format your final answer directly in markdown.\n"
            )

        today = datetime.utcnow().strftime("%Y-%m-%d")

        guardrails = config_dict.get("guardrails", [])
        guardrails_text = ""
        if guardrails:
            guardrails_text = "\n## GUARDRAILS & RESTRICTIONS\nYou must strictly follow these rules:\n"
            for g in guardrails:
                if g.get("is_enabled", True) and g.get("instructions"):
                    enforcement = str(g.get("enforcement", "moderate")).upper()
                    guardrails_text += (
                        f"- [{enforcement} PRIORITY]: {g['instructions']}\n"
                    )

        return f"Today's date is {today} (UTC).\n\n{base}{tool_text}{workflow}{guardrails_text}"

    def build_graph(self, config_dict: Dict[str, Any], ctx: ToolContext = None):
        llm_config = config_dict.get("llm_config", {}) or {}
        tools_config = config_dict.get("tools") or []

        try:
            llm = initialize_llm(llm_config)
        except LLMInitializationError:
            raise

        required_tools = self._get_tools(tools_config)
        system_instruction = self.get_system_instruction(config_dict, required_tools)
        langchain_tools = [t.as_langchain_tool(ctx=ctx) for t in required_tools]

        # FIX: was create_agent (does not exist). create_react_agent is the correct
        # LangGraph function. It builds a ReAct loop that automatically cycles back
        # to the LLM after every tool call — this is what was missing, causing the
        # agent to stop after tool execution without generating a final AIMessage.
        agent = create_react_agent(
            model=llm,
            tools=langchain_tools,
            prompt=system_instruction,
        )
        return agent, system_instruction, langchain_tools

    async def invoke(self, agent, query: str, session_id: str):
        # FIX: removed configurable thread_id — create_react_agent without a
        # checkpointer doesn't support memory/threads. Passing thread_id caused
        # a silent config error on some LangGraph versions. Add a MemorySaver
        # checkpointer here if you need per-session memory.
        return await agent.ainvoke(
            {"messages": [HumanMessage(content=query)]},
        )
