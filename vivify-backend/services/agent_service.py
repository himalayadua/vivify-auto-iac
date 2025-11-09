"""
Conversational Agent Service using LangChain + Gemini Pro
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.agent import AgentExecutor
from langchain.agents.react.agent import create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from typing import Dict, Any, List, AsyncGenerator
from services.tools import WebSearchTool, TaskTool
from services.tools.canvas_tool import get_canvas_tool
import os
import json
import asyncio
from queue import Queue
import logging

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for streaming agent events"""
    
    def __init__(self, queue: Queue):
        self.queue = queue
        super().__init__()
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts"""
        self.queue.put({"type": "thinking", "thought": "Processing your request..."})
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when tool starts"""
        tool_name = serialized.get("name", "unknown")
        self.queue.put({
            "type": "tool_call",
            "toolName": tool_name,
            "toolInput": input_str
        })
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when tool ends"""
        self.queue.put({
            "type": "tool_result",
            "toolOutput": output[:500]  # Limit output size
        })
    
    def on_agent_finish(self, finish: Any, **kwargs) -> None:
        """Called when agent finishes"""
        try:
            output = finish.return_values.get("output", "")
            self.queue.put({
                "type": "final_answer",
                "text": output
            })
        except:
            pass


class ConversationalAgent:
    """Main conversational agent class"""
    
    def __init__(self, gemini_api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_api_key,
            temperature=0.7
        )
        
        self.sessions: Dict[str, ConversationBufferMemory] = {}
        self.tools = self._initialize_tools()
        self.agent_prompt = self._get_prompt()
        
        logger.info("Conversational agent initialized with Gemini Pro")
    
    def _initialize_tools(self) -> List:
        """Initialize all tools"""
        return [
            WebSearchTool(),
            TaskTool(),
            get_canvas_tool()
        ]
    
    def _get_prompt(self) -> PromptTemplate:
        """Get the agent prompt template"""
        template = """You are Vibe, a helpful DevOps assistant. You help users manage their tasks and GCP infrastructure.

You have access to the following tools:

{tools}

Tool Names: {tool_names}

When using tools, follow this format exactly:

Question: the input question you must answer
Thought: think about what to do
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action (must be valid JSON for task_manager and canvas_query)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Important guidelines:
- For task_manager and canvas_query tools, Action Input MUST be valid JSON
- Always provide a helpful, conversational Final Answer
- If a tool returns an error, explain it clearly to the user
- Be concise but friendly

Previous conversation:
{chat_history}

Question: {input}
{agent_scratchpad}"""
        
        return PromptTemplate.from_template(template)
    
    def get_or_create_memory(self, session_id: str) -> ConversationBufferMemory:
        """Get or create conversation memory for a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=False,
                input_key="input",
                output_key="output"
            )
            logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]
    
    async def stream_response(
        self,
        message: str,
        session_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream agent response with thinking, tool calls, and final answer"""
        
        try:
            memory = self.get_or_create_memory(session_id)
            
            # Create event queue
            event_queue = Queue()
            callback = StreamingCallbackHandler(event_queue)
            
            # Create agent
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.agent_prompt
            )
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,
                callbacks=[callback]
            )
            
            # Run agent in background
            async def run_agent():
                try:
                    result = await agent_executor.ainvoke({"input": message})
                    logger.info(f"Agent completed for session {session_id}")
                except Exception as e:
                    logger.error(f"Agent error: {str(e)}")
                    event_queue.put({
                        "type": "error",
                        "message": f"I encountered an error: {str(e)}"
                    })
                finally:
                    event_queue.put(None)  # Signal completion
            
            # Start agent task
            agent_task = asyncio.create_task(run_agent())
            
            # Stream events
            while True:
                # Check queue
                if not event_queue.empty():
                    event = event_queue.get()
                    
                    if event is None:  # Completion signal
                        break
                    
                    yield event
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
                # Check if agent task is done
                if agent_task.done():
                    # Drain remaining events
                    while not event_queue.empty():
                        event = event_queue.get()
                        if event is not None:
                            yield event
                    break
        
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield {
                "type": "error",
                "message": f"Sorry, I encountered an error: {str(e)}"
            }
    
    def clear_session(self, session_id: str):
        """Clear session memory"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session: {session_id}")
    
    def update_canvas_data(self, architecture: dict):
        """Update canvas tool with latest architecture data"""
        canvas_tool = get_canvas_tool()
        canvas_tool.set_architecture_data(architecture)
        logger.info("Updated canvas data in agent")


# Global agent instance
_agent = None

def get_agent() -> ConversationalAgent:
    """Get or create agent instance"""
    global _agent
    if _agent is None:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        _agent = ConversationalAgent(gemini_api_key)
    return _agent
