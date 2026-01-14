import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from url_agent_executor import (
    UrlAgentExecutor,  # type: ignore[import-untyped]
)





AGENT_NAME = "Conversation Agent"
AGENT_URL = "http://localhost:11434/api/generate"
AGENT_MODEL_NAME = "gemma3:4b"
AGENT_INITIAL_PROMPT = "you are an expert in solving questions and chatting so solve the query: "


if __name__ == '__main__':
    
    # Skill for conversation
    skill = AgentSkill(
        id='conversation',
        name='returns the answer of a generic question',
        description='just returns the answer of a generic question',
        tags=['conversation','question','answer'],
        examples=['hi, how are you', 'I am fine thanks'],
    )

    
    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='Conversation Agent',
        description='A conversational Agent, it can answer or solve questions',
        url='http://localhost:9999/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],  # Only the basic skill for the public card
        supports_authenticated_extended_card=True,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=UrlAgentExecutor(name=AGENT_NAME, url=AGENT_URL, model_name=AGENT_MODEL_NAME, initial_prompt=AGENT_INITIAL_PROMPT),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(server.build(), host='0.0.0.0', port=9999)