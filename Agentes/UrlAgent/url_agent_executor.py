from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
import requests

class UrlAgent:
    """UrlAgent.
    description: this is an agent wrapper that connects to other LLM model running on some url
    """

    # Constructor general
    def __init__(self, name:str, url:str, model_name:str, initial_prompt:str):
        self.name = name
        self.url = url
        self.model_name = model_name
        self.initial_prompt = initial_prompt

    # Funcion de invocacion, ejecuta una peticion al LLM
    async def   invoke(self, prompt:str) -> str:
        final_prompt = self.initial_prompt + " " + prompt
        response = requests.post(
            self.url,
            json={"model": self.model_name,
                 "prompt": final_prompt,
                 "stream": False
                 }
        )
        # Lanza una excepcion si el status de la respuesta es incorrecto
        response.raise_for_status()
        datos = response.json()["response"]
        return datos
    


    


class UrlAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    # Constructor completo
    def __init__(self,name:str, url:str, model_name:str, initial_prompt:str):
        self.agent = UrlAgent(name = name, url = url, model_name = model_name, initial_prompt = initial_prompt)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        role = context.message.role.name
        print(str(role))
        print(role == "user")
        query = context.message.parts[0].root.text
        print(query)
        #print(query)
        result = await self.agent.invoke(query)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception('cancel not supported')



