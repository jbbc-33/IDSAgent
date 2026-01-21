from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_parts_message
from a2a.types import DataPart
from ids_graph import GraphAgent
from llm_ollama import LLMOllama
from llm_controller import LLMController
from agent_constants import *



class IDSAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    # Constructor completo
    def __init__(self, force_a2a : bool = False):
        llm = LLMOllama(url=URL_API_OLLAMA_CHAT, model = MODEL_OLLAMA)
        self.agent = GraphAgent(llmController = llm, force_a2a=force_a2a)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        log = context.message.parts[0].root.text
        role = context.message.role.name
        result = await self.agent.ainvoke(role=role, log=log)
        part = DataPart(data=result)
        await event_queue.enqueue_event(new_agent_parts_message(parts=[part]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception('cancel not supported')