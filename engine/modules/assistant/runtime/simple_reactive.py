"""Simple reactive assistant type with LangChain agent + tools."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from engine.modules.assistant.runtime.llm_initializer import initialize_llm
from engine.modules.assistant.tools.base_tool import BaseTool, ToolContext
from engine.modules.assistant.tools.tool_registry import ToolRegistryNew
from engine.modules.assistant.runtime.rag_context import RAG_WORKFLOW_INSTRUCTIONS
from engine.modules.assistant.runtime.drive_context import DRIVE_WORKFLOW_INSTRUCTIONS
from engine.modules.assistant.tools.exceptions import LLMInitializationError

logger = logging.getLogger(__name__)


class SimpleReactiveType:
    def get_type_id(self) -> str:
        return "simple_reactive"

    def _get_tools(self, tools_config: List[Dict[str, Any]] = None) -> List[BaseTool]:
        tools: List[BaseTool] = []
        for t in tools_config or []:
            if isinstance(t, dict) and t.get("tool_id"):
                tool_class = ToolRegistryNew.get_tool(t["tool_id"])
                tools.append(
                    tool_class(
                        config=t.get("config", {}),
                        credential_id=t.get("credential_id"),
                        usage_instructions=t.get("usage_instructions", ""),
                    )
                )
        return tools

    def get_system_instruction(
        self, config_dict: Dict[str, Any], tools: List[BaseTool]
    ) -> str:
        base = config_dict.get("system_instruction", "")
        tool_text = "\n## AVAILABLE TOOLS\n\n"
        for tool in tools:
            tool_text += f"### {tool.name.upper()}\n{tool.get_instruction()}\n\n"

        workflow = ""
        if any(t.name == "rag_search" for t in tools):
            workflow += RAG_WORKFLOW_INSTRUCTIONS
        if any(t.name == "drive_search" for t in tools):
            workflow += DRIVE_WORKFLOW_INSTRUCTIONS



        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        guardrails = config_dict.get("guardrails", [])
        guardrails_text = ""
        if guardrails:
            guardrails_text = "\n## GUARDRAILS & RESTRICTIONS\nYou must strictly follow these rules:\n"
            for g in guardrails:
                if g.get("is_enabled", True) and g.get("instructions"):
                    enforcement = str(g.get("enforcement", "moderate")).upper()
                    guardrails_text += f"- [{enforcement} PRIORITY]: {g['instructions']}\n"

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

        agent = create_agent(
            model=llm,
            tools=langchain_tools,
            system_prompt=system_instruction,
        )
        return agent, system_instruction, langchain_tools

    def invoke(self, agent, query: str, session_id: str):
        return agent.invoke(
            {"messages": [HumanMessage(content=query)]},
            config={"configurable": {"thread_id": session_id}},
        )
