"""
Base Agent Class
All specialized agents inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from config import settings
import time
import json

class BaseAgent(ABC):
    """
    Base class for all specialized agents
    """
    
    def __init__(self, agent_name: str, agent_description: str):
        self.agent_name = agent_name
        self.agent_description = agent_description
        
        # Initialize Claude if API key available
        if settings.ANTHROPIC_API_KEY:
            self.llm = ChatAnthropic(
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                model=settings.ANTHROPIC_MODEL,
                temperature=0.7,
                max_tokens=1000
            )
        else:
            self.llm = None
            print(f"⚠️ {agent_name}: Running in MOCK mode (no API key)")
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method - calls the agent and updates state
        """
        start_time = time.time()
        
        # Log agent call
        print(f"🤖 {self.agent_name} called...")
        
        # Record agent activity
        state["agent_calls"].append({
            "agent": self.agent_name,
            "timestamp": time.time(),
            "status": "processing"
        })
        
        try:
            # Execute agent logic
            result = await self._execute(state)
            
            execution_time = time.time() - start_time
            
            # Update agent call status
            state["agent_calls"][-1].update({
                "status": "success",
                "execution_time": execution_time,
                "result": result
            })
            
            print(f"✅ {self.agent_name} completed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            state["agent_calls"][-1].update({
                "status": "failed",
                "execution_time": execution_time,
                "error": str(e)
            })
            print(f"❌ {self.agent_name} failed: {e}")
            return {}
    
    @abstractmethod
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent-specific logic - must be implemented by subclasses
        """
        pass
    
    def _load_data(self, filename: str) -> Dict[str, Any]:
        """
        Load data from JSON file
        """
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return {}
    
    async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """
        Call Claude LLM with fallback to mock response
        """
        if self.llm and not settings.USE_MOCK_RESPONSES:
            try:
                messages = []
                if system_prompt:
                    messages.append(("system", system_prompt))
                messages.append(("user", prompt))
                
                response = await self.llm.ainvoke(messages)
                return response.content
            except Exception as e:
                print(f"LLM call failed: {e}")
                return self._get_mock_response(prompt)
        else:
            return self._get_mock_response(prompt)
    
    def _get_mock_response(self, prompt: str) -> str:
        """
        Fallback mock response when API not available
        """
        return f"[MOCK] Response from {self.agent_name}"
    
    def _format_json_response(self, data: Dict[str, Any]) -> str:
        """
        Format response as JSON string
        """
        return json.dumps(data, indent=2)