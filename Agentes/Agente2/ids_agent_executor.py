from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message, new_agent_parts_message
from a2a.types import DataPart
from ids_graph import makeGraph, AgentState
import requests

# Constantes de keys de state
MESSAGES = "messages"
TOOLS = "tools"
SELECTED_TOOL = "selected_tool"
SELECTED_TOOL_ARGS = "selected_tool_args"
AGENTS = "agents"
SELECTED_AGENT = "selected_agent"

class IDSAgent:
    """IDSAgent.
    description: this is a LLM agent that classifies one log into labeled cathegories, if you use me, you must only give me the log you want me to classify
    """

    # Constructor general
    def __init__(self):
        self.graph = makeGraph()
        self.agent = self.graph.compile()


    # Funcion de invocacion, ejecuta una peticion al LLM IDS agent
    async def invoke(self, query : AgentState) -> AgentState:
        datos = await self.agent.ainvoke(query)
        return datos
    


class IDSAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    # Constructor completo
    def __init__(self):
        self.agent = IDSAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        log = context.message.parts[0].root.text
        role = context.message.role.name
        query = {
            MESSAGES: [{"role": str(role), "content": log}],
            TOOLS: [],
            SELECTED_TOOL: None,
            SELECTED_TOOL_ARGS: None,
            AGENTS: [],
            SELECTED_AGENT: None
        }
        result = await self.agent.invoke(query)
        part = DataPart(data=result[MESSAGES][-1])
        await event_queue.enqueue_event(new_agent_parts_message(parts=[part]))
        #await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception('cancel not supported')