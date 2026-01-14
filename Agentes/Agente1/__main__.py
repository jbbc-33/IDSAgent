import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from ids_agent_executor import (
    IDSAgentExecutor,  # type: ignore[import-untyped]
)


URL_AGENT_SERVING='http://localhost:9999/'
PORT=9999
HOST='0.0.0.0'

CLASSIFICACTION_CATHEGORIES = ["normal_log", "dnsteal","attacker_http","service_scan","dns_scan","network_scan","escalate","attacker_vpn","webshell_cmd","dirb","escalated_command","wpscan","traceroute","attacker_change_user"]
EXAMPLE_LOG = """
                log:
                    {"service":{"type":"system"},"agent":{"hostname":"internal-share","name":"internal-share","id":"480761c0-a9a7-48cc-a30b-f67100b44955","ephemeral_id":"cc234e3a-114f-402c-ab60-737cee803231","version":"7.13.2","type":"metricbeat"},"event":{"module":"system","dataset":"system.diskio","duration":846779},"@version":"1","metricset":{"period":45000,"name":"diskio"},"ecs":{"version":"1.9.0"},"host":{"name":"internal-share"},"@timestamp":"2022-01-20T17:55:07.556Z","tags":["beats_input_raw_event"],"system":{"diskio":{"name":"vda14","io":{"time":0,"ops":0},"write":{"time":0,"bytes":0,"count":0},"iostat":{"await":0,"queue":{"avg_size":0},"busy":0,"write":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}},"request":{"avg_size":0},"service_time":0,"read":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}}},"read":{"time":260,"bytes":991232,"count":242}}}}
                source:
                    monitoring
                """
EXAMPLE_RESPONSE =f"""
                    {{
                        "log" : {EXAMPLE_LOG},
                        "label" : "normal_log",
                        "confident_index" : "0.9",
                        "reason" : " i am pretty sure that the activity showed in this log doesnt seem malicious or suspicious"
                    }}
                """

if __name__ == '__main__':
    
    # Skill for conversation
    skill = AgentSkill(
        id='Classification',
        name='IDS Service',
        description='classify one log and its source into one of the cathegories defined by the labels: '+''.join([f'{label}, ' for label in CLASSIFICACTION_CATHEGORIES]),
        tags=['IDS','classifying','labels','cathegories','log','source'],
        examples=[EXAMPLE_LOG, EXAMPLE_RESPONSE],
    )

    
    # This will be the public-facing agent card
    public_agent_card = AgentCard(
        name='IDS Agent',
        description='This agent is able to classify one log and its source into one of the cathegories defined by the labels: '+''.join([f'{label}, ' for label in CLASSIFICACTION_CATHEGORIES]),
        url=URL_AGENT_SERVING,
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['application/json'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],  # Only the basic skill for the public card
        supports_authenticated_extended_card=True,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=IDSAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(server.build(), host=HOST, port=PORT)