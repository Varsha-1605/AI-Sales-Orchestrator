"""Base class for the six agents."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from loguru import logger

from ai_workflow.llm import build_llm


class BaseAgent(ABC):
    name: str  # short lowercase name, for example "inventory"
    description: str  # used in the supervisor prompt
    result_key: str  # state key the agent's result is stored under
    needs_approval = False  # True: the graph asks the customer before this agent runs
    system_prompt = ""

    def __init__(self):
        self.llm = build_llm(temperature=0.7, max_tokens=1000)
        if not self.llm:
            logger.warning("{}: running in mock mode (no API key)", self.name)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent. Returns only what it adds: its result and its call record."""
        start_time = time.time()
        logger.info("{} agent called", self.name)
        call_record = {"agent": self.name, "timestamp": start_time, "status": "processing"}

        try:
            result = await self._execute(state)
            call_record.update(status="success", execution_time=time.time() - start_time)
            logger.info("{} agent completed in {:.2f}s", self.name, call_record["execution_time"])
            return {self.result_key: result, "agent_calls": [call_record]}

        except Exception as e:
            call_record.update(status="failed", execution_time=time.time() - start_time, error=str(e))
            logger.error("{} agent failed: {}", self.name, e)
            return {"agent_calls": [call_record]}

    @abstractmethod
    async def _execute(self, state: Dict[str, Any]) -> Any:
        """Agent-specific logic - must be implemented by subclasses"""

    async def _call_llm(self, prompt: str, fallback: Optional[str] = None) -> str:
        """Ask Claude. Without a key, or if the call fails, return the fallback (or a mock reply)."""
        if self.llm:
            try:
                messages = []
                if self.system_prompt:
                    messages.append(("system", self.system_prompt))
                messages.append(("user", prompt))

                response = await self.llm.ainvoke(messages)
                return response.content
            except Exception as e:
                logger.error("LLM call failed: {}", e)
        return fallback or f"[MOCK] Response from {self.name}"
