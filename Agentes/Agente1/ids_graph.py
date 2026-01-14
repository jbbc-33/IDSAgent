from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from litellm import acompletion, logging
import json
import asyncio

from uuid import uuid4

#from google.ai.generativelanguage_v1beta.types import Message, MessagePart
import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Message,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
)

logging = False

# Constantes de configuracion
URL_MCP_SERVER = "http://localhost:8000/mcp"
URL_API_OLLAMA_BASE = "http://localhost:11434"
MODEL_OLLAMA = "ollama/qwen2.5:3b"
URL_EXPOSED_A2A_AGENTS=["http://localhost:9998"]
TIMEOUT=600


# Constantes de keys de state
MESSAGES = "messages"
TOOLS = "tools"
SELECTED_TOOL = "selected_tool"
SELECTED_TOOL_ARGS = "selected_tool_args"
AGENTS = "agents"
SELECTED_AGENT = "selected_agent"

# Constantes para el nombre de los nodos
NAME_NODE_LOAD_TOOLS = "node_load_tools"
NAME_NODE_RETRIEVE_INFORMATION = "node_retrieve_information"
NAME_NODE_EXECUTE_SELECTED_TOOL = "node_execute_selected_tool"
NAME_NODE_EVALUATOR_PHASE1 = "node_evaluator_phase1"
NAME_NODE_SELECT_AGENT = "node_select_agent"
NAME_NODE_COMUNICATE_A2A = "node_comunicate_a2a"
NAME_NODE_EVALUATOR_PHASE2 = "node_evaluator_phase2"
NAME_NODE_FINAL_ANSWER = "name_node_final_answer"

# Constantes para los roles del agente en cada nodo
ROLE_NODE_RETRIEVE_INFORMATION_SUCCESS = "retriever"
ROLE_NODE_RETRIEVE_INFORMATION_FAILURE = "retriever_error"
ROLE_NODE_EXECUTE_SELECTED_TOOL_SUCCESS = "tool"
ROLE_NODE_EXECUTE_SELECTED_TOOL_FAILURE = "tool_error"
ROLE_NODE_EVALUATOR_PHASE1_SUCCESS = "phase1"
ROLE_NODE_EVALUATOR_PHASE1_FAILURE = "phase1_error"
ROLE_NODE_SELECT_AGENT_SUCCESS = "agent_selector"
ROLE_NODE_SELECT_AGENT_FAILURE = "agent_selector_error"
ROLE_NODE_COMUNICATE_A2A_SUCCESS = "comunicate_a2a"
ROLE_NODE_COMUNICATE_A2A_FAILURE = "comunicate_a2a_error"
ROLE_NODE_EVALUATOR_PHASE2_SUCCESS = "phase2"
ROLE_NODE_EVALUATOR_PHASE2_FAILURE = "phase2_error"

# Constantes de para las categorias de clasificacion
CLASSIFICACTION_CATHEGORIES = ["normal_log", "dnsteal","attacker_http","service_scan","dns_scan","network_scan","escalate","attacker_vpn","webshell_cmd","dirb","escalated_command","wpscan","traceroute","attacker_change_user"]

# Clase que guardara el estado del agente
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    #tools: Dict[str, Any]                  # herramientas combinadas MCP + A2A
    tools: List[BaseTool]
    selected_tool: Optional[BaseTool]
    selected_tool_args: Optional[Any]
    agents: List[AgentCard]   # Lista de tuplas (agenteA2A, agentCard)
    selected_agent: AgentCard




# Funcion para obtener las mcp tools disponibles a traves del cliente MCP
async def get_mcp_tools() -> List[BaseTool]:
    # Creacion del cliente MCP
    clientMCP = MultiServerMCPClient(
        {
            "RAG": {
                "transport": "streamable_http",  # HTTP-based remote server
                # Ensure you start your weather server on port 8000
                "url": URL_MCP_SERVER,
            }
        }
    )
    tools = await clientMCP.get_tools()
    return tools



# Funcion para obtener los agentes expuestos por a2a y sus respectivas AgentCards
async def get_a2a_agents() -> List[AgentCard]:
    lista_agentes_a2a : List[AgentCard] = []
    for base_url in URL_EXPOSED_A2A_AGENTS:
        async with httpx.AsyncClient(timeout=TIMEOUT) as httpx_client:
            # Initialize A2ACardResolver
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
                # agent_card_path uses default, extended_agent_card_path also uses default
            )

            # Fetch Public Agent Card and Initialize Client
            final_card: AgentCard | None = None
            try:
                public_card = await resolver.get_agent_card()
                final_card = public_card
            except Exception as e:
                print("No se han descubierto agentes a2a adicionales")
                continue # Saltamos la iteracion porque no se ha descubierto agente para esta url
            #client = A2AClient(httpx_client=httpx_client, agent_card=final_card)
            lista_agentes_a2a.append(final_card)
    #print(len(lista_agentes_a2a))
    return lista_agentes_a2a
            





#-----------Nodos del grafo de ejecucion-------------

# Nodo de entrada, carga las tools y los agentes disponibles
async def node_load_tools(state : AgentState):
    print("Entering NODE: node_load_tools")
    tools = await get_mcp_tools()
    agents = await get_a2a_agents()
    #print(len(agents))
    return {
        **state,
        TOOLS : tools,
        AGENTS : agents
    }


# Nodo encargado de ejecutar la tool seleccionada
async def node_execute_selected_tool(state : AgentState):
    print("Entering NODE: node_execute_selected_tool")
    tool = state.get(SELECTED_TOOL, None)
    args = state.get(SELECTED_TOOL_ARGS, None)
    
    result="No result"
    if tool is None or args is None:
        # Devolver un mensaje para indicar que no hay ninguna tool seleccionada
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_EXECUTE_SELECTED_TOOL_FAILURE,
                "name" : "no_tool",
                "content" : "Error, there is no tool or no arguments to execute the tool"
            }],
            SELECTED_TOOL : None,
            SELECTED_TOOL_ARGS : None
        }
    else:
        try:
            result = await tool.arun(tool_input=args) # Transforma el input en dict a argumentos de la funcion run
        except Exception as e:
            print(args)
            return {
                **state,
                MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_EXECUTE_SELECTED_TOOL_FAILURE,
                "name" : tool.name,
                "content" : f"Error, error executing tool {tool.name}, the error is : {str(e)}"
                }],
                SELECTED_TOOL : None,
                SELECTED_TOOL_ARGS : None
            }
        
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_EXECUTE_SELECTED_TOOL_SUCCESS,
                "name" : tool.name,
                "content" : str(result)
            }],
            SELECTED_TOOL : None,
            SELECTED_TOOL_ARGS : None
        }

# Nodo planificador, se encarga de decidir que tool usar (en nuestro caso primero queremos que use el RAG para clasificar logs)
async def node_retrieve_information(state : AgentState):
    print("Entering NODE: node_retrieve_information")
    prompt ="""
            If there are tools avaliable, you have to choose one of them to retrieve information about similar logs to the given log.
            the tools are: 
            """
    tools = state.get(TOOLS, None)
    if tools is None or tools == []:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_RETRIEVE_INFORMATION_FAILURE,
                "content" : "No tools avaliable for retrieving"
            }],
            SELECTED_TOOL : None,
            SELECTED_TOOL_ARGS: None
        }
    else:
        prompt = prompt + "".join([f"NAME: {str(tool.name)}, PARAMETERS: {str(tool.args_schema)}, DESCRIPTION: {str(tool.description)}\n" for tool in tools])
        given_info = state[MESSAGES][-1]["content"]
        prompt = prompt + "the given log is:  "+given_info + "\n"
        response_format="""
                        {
                            "tool_name": "the name of the tool you want to use",
                            "tool_args": "the args for running the tool in the correct format, following its args schema"
                        }
                        """
        prompt = prompt + "ALWAYS USE THIS JSON FORMAT FOR THE RESPONSE : \n" + response_format + "\n"
        llm_response = await acompletion(
                            model=MODEL_OLLAMA,
                            base_url=URL_API_OLLAMA_BASE,
                            stream=False,
                            messages=[{"role": "user", "content": prompt}]
                        )
        decision = llm_response["choices"][0]["message"]["content"]
        parsed = {}
        try:
            parsed = json.loads(decision)
        except Exception as e:
            return {
                **state,
                MESSAGES : state[MESSAGES] + [
                    {
                        "role": ROLE_NODE_RETRIEVE_INFORMATION_FAILURE,
                        "content": f"Unable to parse the model decision: {decision}"
                    }
                ],
                SELECTED_TOOL: None,
                SELECTED_TOOL_ARGS: None,
            }
        tool_name = parsed.get("tool_name", False)
        tool_args = parsed.get("tool_args", False)
        #Ninguna tool seleccionada o no args para la tool
        if not tool_name or not tool_args:
            return {
                **state,
                MESSAGES: state[MESSAGES] + [
                    {"role": ROLE_NODE_RETRIEVE_INFORMATION_FAILURE, 
                     "content": "No tool selected"}
                ],
                SELECTED_TOOL: None,
                SELECTED_TOOL_ARGS: None,
            }
        else:
            #Buscamos la tool con el nombre de la seleccionada por el agente
            selected_tool = next((tool for tool in tools if tool.name == tool_name), None)
            #Caso en que la tool no existe
            if selected_tool is None:
                return {
                **state,
                MESSAGES: state[MESSAGES] + [
                    {
                        "role": ROLE_NODE_RETRIEVE_INFORMATION_FAILURE,
                        "content": f"Error, the choosed tool '{tool_name}' doesnt exist."
                    }
                ],
                SELECTED_TOOL: None,
                SELECTED_TOOL_ARGS: None,
                }
            else:
                #El agente ha conseguido elegir la tool correcta
                return {
                    **state,
                    MESSAGES: state[MESSAGES] + [
                        {
                            "role": ROLE_NODE_RETRIEVE_INFORMATION_SUCCESS,
                            "content": f"Voy a usar la tool '{selected_tool.name}' con args: {tool_args}"
                        }
                    ],
                    SELECTED_TOOL: selected_tool,
                    SELECTED_TOOL_ARGS: tool_args,
                }

# Nodo para evaluar la categoria del log
async def node_evaluator_phase1(state: AgentState):
    print("Entering NODE: node_evaluator_phase1")
    prompt="""
            You are a log-based Intrusion Detection System (IDS). 
            The network includes this services: a web server, cloud file share, mail servers, VPN gateway, DNS, internal intranet, a firewall, four internal employees, three remote employees, and three external users.
            """
    response_format=""
    used_rag = state[MESSAGES][-1]["role"] == "tool" and state[MESSAGES][-1]["content"] != "No result"
    # Caso en el que hay logs del RAG
    if used_rag:
        prompt=prompt+"You will be provided with a list of similar past logs with known labels and the similarity score, and a new log message with the source to classify"
        prompt=prompt+"Using this information retrieved from the RAG as context: " + state[MESSAGES][-1]["content"] +"\n"
        prompt=prompt+"Try to classify this log into one of these cathegories: "+"".join([f"{cat} " for cat in CLASSIFICACTION_CATHEGORIES])+"\n"
        prompt=prompt+"You also have to give a number between 0.0 and 1.0 depending on how confident you are in your classificacion, meaning 0.0 that you are not sure about your classification and 1.0 completely sure about your classification, we will name this number confident_index"+"\n"
        prompt=prompt+"I want you to reason why you put that classification too"+"\n"
        response_format1 ="""
                        {
                            "log" : "the given log with its source, as it was given to you",
                            "rag" : "the given retrieved similar logs as they were passed to you, with everything they had",
                            "label" : "the cathegory label you considered for the given log's classification, it can only be one",
                            "confident_index" : "the number between 0.0 and 1.0 that i mencioned before, indicatig how confident you are on your classification",
                            "reason" : "the explaination on why your label choise was the one it was, no more than 70 words"
                        }
                        """
    # Caso en el que no hay logs del RAG (no se ha usado la tool)
    else:
        prompt=prompt+"Try to classify this log into one of these cathegories: "+"".join([f"{cat} " for cat in CLASSIFICACTION_CATHEGORIES])+"\n"
        prompt=prompt+"You also have to give a number between 0.0 and 1.0 depending on how confident you are in your classificacion, meaning 0.0 that you are not sure about your classification and 1.0 completely sure about your classification, we will name this number confident_index"+"\n"
        prompt=prompt+"I want you to reason why you put that classification too"+"\n"
        response_format1 ="""
                        {
                            "log" : "the given log with its source, as it was given to you",
                            "label" : "the cathegory label you considered for the given log's classification, it can only be one",
                            "confident_index" : "the number between 0.0 and 1.0 that i mencioned before, indicatig how confident you are on your classification",
                            "reason" : "the explaination on why your label choise was the one it was, no more than 70 words"
                        }
                        """
    response_format ="""
                        {
                            "label" : "the cathegory label you considered for the given log's classification, it can only be one",
                            "confident_index" : "the number between 0.0 and 1.0 that i mencioned before, indicatig how confident you are on your classification",
                            "reason" : "the explaination on why your label choise was the one it was, no more than 70 words"
                        }
                        """
    prompt=prompt+"I want the response format to be EXACTLY this one, being a json format where the keys are exactly the ones at the left side, and at the right parts i gave you the description of the data i want you to put: "+response_format+"\n"
    prompt=prompt+"when putting all the data response in the json format, do not use \n character or any scape special characters, RESPECT the json format"
    log = state[MESSAGES][0]["content"] # Accedemos al primer mensaje, que contiene el log que queremos clasificar
    prompt=prompt+"Finally i give you the log, classsify this log: "+log+"\n"
    result = await acompletion(
                            model=MODEL_OLLAMA,
                            base_url=URL_API_OLLAMA_BASE,
                            stream=False,
                            messages=[{"role": "user", "content": prompt}]
                            )
    response = result["choices"][0]["message"]["content"]
    parsed = {}
    try:
        parsed = json.loads(response)
    except Exception as e:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [
                {
                    "role": ROLE_NODE_EVALUATOR_PHASE1_FAILURE,
                    "content": f"Unable to parse the model response: {response}"
                }
            ],
        }
    #log2 = parsed.get("log", False)
    #rag = parsed.get("rag", False) if used_rag else True # Si hemos usado el rag respetamos el valor, si no lo ponemos a True para no tenerlo en cuenta
    label = parsed.get("label", False)
    confident_index = parsed.get("confident_index", False)
    reason = parsed.get("reason", False)
    # not log2 or not rag or 
    if not label or not confident_index or not reason:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_EVALUATOR_PHASE1_FAILURE,
                "content" : "Error, algun elemento faltante en la respuesta del agente"
            }],
        }
    
    # La consulta ha ido bien, devolvemos el veredicto final del agente
    else:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_EVALUATOR_PHASE1_SUCCESS,
                "content" : parsed
            }],
        }

# Nodo encargado de la seguna fase de razonamiento, con el resultado de la consulta al agente de apoyo
async def node_evaluator_phase2(state: AgentState):
    print("Entering NODE: node_evaluator_phase2")
    # esta fase del evaluador solo se ejecuta cuando recibimos la respuesta de otro agente a2a
    if state[MESSAGES][-1]["role"] == "comunicate_a2a":
        prompt="""
            You are a log-based Intrusion Detection System (IDS). 
            The network includes this services: a web server, cloud file share, mail servers, VPN gateway, DNS, internal intranet, a firewall, four internal employees, three remote employees, and three external users.
            """
        response_format=""
        #Recuperamos la informacion extraida de la fase 1 de evaluacion
        phase1_info = {}
        for message in state[MESSAGES]:
            if message["role"] == "phase1":
                phase1_info = message["content"]
                break
        # Si encontramos la informacion de la fase 1 avanzamos
        if phase1_info != {}:
            #log = phase1_info.get("log", False)
            log = state[MESSAGES][0]["content"]
            #rag = phase1_info.get("rag", False)
            rag=False
            for message in state[MESSAGES]:
                if message["role"]==ROLE_NODE_EXECUTE_SELECTED_TOOL_SUCCESS:
                    rag = message["content"]
                    break
            label = phase1_info.get("label", False)
            confident_index = phase1_info.get("confident_index", False)
            reason = phase1_info.get("reason", False)
            previous_info_for_llm=""
            try:
                previous_info_for_llm = ""+(f"LOG: {str(log)}\n" if log else "")+(f"RAG: {str(rag)}\n" if rag else "")+(f"PREVIOUS ASSIGNED LABEL: {str(label)}\n" if  label else "")+(f"PREVIOUS CONFIDENT INDEX: {str(confident_index)}\n" if confident_index else "")+(f"PREVIUOS REASONING: {str(reason)}"if reason else "")
            except Exception as e:
                return {
                    **state,
                    MESSAGES : state[MESSAGES] + [{
                        "role" : ROLE_NODE_EVALUATOR_PHASE2_FAILURE,
                        "content" : f"Error, error extracting info from previous phase 1 evaluation, {e}"
                    }]
                }
            prompt=prompt+"You previously classified one log into one of these cathegories: "+"".join([f"{cat} " for cat in CLASSIFICACTION_CATHEGORIES])+"\n"
            prompt=prompt+"these same cathegories are also the ones you are going to use now"+"\n"
            try:
                prompt=prompt+"But we asked for a second opinion to another classification IDS Agent, and the information it gave us is: "+str(state[MESSAGES][-1]["content"])+"\n"
            except Exception as e:
                return {
                    **state,
                    MESSAGES : state[MESSAGES] + [{
                        "role" : ROLE_NODE_EVALUATOR_PHASE2_FAILURE,
                        "content" : f"Error, converting to string the data from the communication agent, {e}"
                    }]
                }
            prompt=prompt+"The information you had before consulting the other agent was: "+previous_info_for_llm+"\n"
            prompt=prompt+"The log i want you to classify (in one of the cathegories i showed you before) is the same one that you have already classified,"+(f"LOG: {str(log)}" if log else "")+",but taking all the information i gave you into account"+"\n"
            prompt=prompt+"You also have to give a new number between 0.0 and 1.0 depending on how confident you are now in your classificacion, meaning 0.0 that you are not sure about your classification and 1.0 completely sure about your classification, we will name this number confident_index"+"\n"
            prompt=prompt+"I want you to reason why you put that classification too"+"\n"
            response_format1 ="""
                            {
                                "log" : "the given log with its source, as it was given to you",
                                "rag" : "the given retrieved similar logs as they were passed to you, with everything they had; only if there is some rag information, if not just ignore this field and dont put it",
                                "label" : "the cathegory label you considered for the given log's classification, it can only be one",
                                "confident_index" : "the number between 0.0 and 1.0 that i mencioned before, indicatig how confident you are on your classification",
                                "reason" : "the explaination on why your label choise was the one it was, no more than 70 words"
                            }
                            """
            response_format ="""
                        {
                            "label" : "the cathegory label you considered for the given log's classification, it can only be one",
                            "confident_index" : "the number between 0.0 and 1.0 that i mencioned before, indicatig how confident you are on your classification",
                            "reason" : "the explaination on why your label choise was the one it was, no more than 70 words"
                        }
                        """
            prompt=prompt+"I want the response format to be EXACTLY this one, being a json format where the keys are exactly the ones at the left side, and at the right parts i gave you the description of the data i want you to put: "+response_format+"\n"
            prompt=prompt+"when putting all the data response in the json format, do not use \n character or any scape special characters, RESPECT the json format"
            result = await acompletion(
                            model=MODEL_OLLAMA,
                            base_url=URL_API_OLLAMA_BASE,
                            stream=False,
                            messages=[{"role": "user", "content": prompt}]
                            )
            response = result["choices"][0]["message"]["content"]
            parsed = {}
            try:
                parsed = json.loads(response)
            except Exception as e:
                return {
                    **state,
                    MESSAGES : state[MESSAGES] + [
                        {
                            "role": ROLE_NODE_EVALUATOR_PHASE2_FAILURE,
                            "content": f"Unable to parse the model response: {response}"
                        }
                    ],
                }
            #log_resp = parsed.get("log", False)
            label_resp = parsed.get("label", False)
            confident_index_resp = parsed.get("confident_index", False)
            reason_resp = parsed.get("reason", False)
            #not log_resp  or
            if  not label_resp or not confident_index_resp or not reason_resp:
                return {
                    **state,
                    MESSAGES : state[MESSAGES] + [{
                        "role" : ROLE_NODE_EVALUATOR_PHASE2_FAILURE,
                        "content" : "Error, en phase2, algun elemento faltante en la respuesta del agente"
                    }],
                }
            
            # La consulta ha ido bien, devolvemos el veredicto final del agente
            else:
                return {
                    **state,
                    MESSAGES : state[MESSAGES] + [{
                        "role" : ROLE_NODE_EVALUATOR_PHASE2_SUCCESS,
                        "content" : parsed
                    }],
                }
            
            
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_EVALUATOR_PHASE2_FAILURE,
                "content" : "Error, couldnt reach info from previous reasoning (from phase1) in phase2"
            }]
        }
    return {
        **state,
        MESSAGES : state[MESSAGES] + [{
            "role" : ROLE_NODE_EVALUATOR_PHASE2_FAILURE,
            "content" : "Error, no previous communication in phase2, something failed in node comunicate_a2a"
        }]
    }
        

# Nodo encargado de seleccionar un agente
async def node_select_agent(state: AgentState):
    print("Entering NODE: node_select_agent")
    avaliable_agents = state.get(AGENTS, [])
    # Caso en el que no hay agentes de apoyo disponibles
    if avaliable_agents == []:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_SELECT_AGENT_FAILURE,
                "content" : "Error, no agents avaliable in the list of discovered agents"
            }],
            SELECTED_AGENT : None
        }
    prompt = "From the given agents, you have to choose one in order to comunicate, you have to choose the one you believe is the most suitable for classifying log messages\n"
    prompt = prompt + "you are going to recieve the name of the agent and it's description: "
    prompt = prompt + "".join([f"Agent name: {card.name} Description: {card.description}\n" for card in state.get(AGENTS)])
    prompt = prompt + "I also want you to use this format for the response: "
    response_format = """
                    {
                        "agent_name" : "the name of the agent you choosed"
                    }
                    """
    prompt = prompt + response_format
    result = await acompletion(
                                model=MODEL_OLLAMA,
                                base_url=URL_API_OLLAMA_BASE,
                                stream=False,
                                messages=[{"role": "user", "content": prompt}]
                            )
    response = result["choices"][0]["message"]["content"]
    parsed = {}
    try:
        parsed = json.loads(response)
    except Exception as e:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [
                {
                    "role": ROLE_NODE_SELECT_AGENT_FAILURE,
                    "content": f"Unable to parse the model response: {response}"
                }
            ],
            SELECTED_AGENT : None
        }
    agent_name = parsed.get("agent_name", False)
    if not agent_name:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_SELECT_AGENT_FAILURE,
                "content" : "Error, algun elemento faltante en la respuesta del agente"
            }],
            SELECTED_AGENT : None
        }
    #Buscamos el agente con el nombre del seleccionado
    selected_agent = next((card for card in avaliable_agents if card.name == agent_name), None)
    #Caso en que el agente no existe
    if selected_agent is None:
        return {
        **state,
        MESSAGES: state[MESSAGES] + [
            {
                "role": ROLE_NODE_SELECT_AGENT_FAILURE,
                "content": f"Error, the choosed agent '{agent_name}' doesnt exist."
            }
        ],
        SELECTED_AGENT: None,
        }
    else:
        #El agente ha conseguido elegir al agente de apoyo correcto
        return {
            **state,
            MESSAGES: state[MESSAGES] + [
                {
                    "role": ROLE_NODE_SELECT_AGENT_SUCCESS,
                    "content": f"Voy a usar el agente '{agent_name}'"
                }
            ],
            SELECTED_AGENT: selected_agent,
        }

# Nodo encargado de conversar con el agente remoto previamente seleccionado CUIDADO CON LOOPS DE COMUNICACION
async def node_comunicate_a2a(state: AgentState):
    print("Entering NODE: node_comunicate_a2a")
    agent_card = state.get(SELECTED_AGENT, False)
    if not agent_card:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_COMUNICATE_A2A_FAILURE,
                "content" : "Error, no hay ningun agente seleccionado"
            }],
            SELECTED_AGENT: None
        }
    log = state[MESSAGES][0]["content"] # Extraemos el log que queremos clasificar del primer mensaje que le mandamos al agente
    send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'agent',
                'parts': [
                    {'kind':'text','text': f'{log}'}
                ],
                'messageId': uuid4().hex,
            },
    }
    request = SendMessageRequest(
        id=str(uuid4()), params=MessageSendParams(**send_message_payload)
    )

    result = ""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as httpx_client:
            client = A2AClient(httpx_client=httpx_client,agent_card=agent_card)
            response = await client.send_message(request)
        result = response.model_dump(mode='json', exclude_none=True)["result"]["parts"][0]["data"]
        print(result)
    except Exception as e:
        return {
            **state,
            MESSAGES : state[MESSAGES] + [{
                "role" : ROLE_NODE_COMUNICATE_A2A_FAILURE,
                "content" : f"Error extrayendo respuesta del agente de apoyo, {e}"
            }],
            SELECTED_AGENT : None
        }
    if result != "":
        role=result.get("role",False)
        content=result.get("content", False)
        if role and "error" in role:
            return {
                **state,
                MESSAGES : state[MESSAGES] +[{
                    "role" : ROLE_NODE_COMUNICATE_A2A_FAILURE,
                    "content" : "Error, la consulta del agente ha devuelto un error"
                }],
                SELECTED_AGENT : None
            }
        elif not role:
            return {
                **state,
                MESSAGES : state[MESSAGES] + [{
                    "role" : ROLE_NODE_COMUNICATE_A2A_FAILURE,
                    "content" : "Error, no hay rol disponible en el mensaje del agente consultado"
                }],
                SELECTED_AGENT : None
            }
        if not content:
            return {
                **state,
                MESSAGES : state[MESSAGES] + [{
                    "role" : ROLE_NODE_COMUNICATE_A2A_FAILURE,
                    "content" : "Error, no hay content disponible en el mensaje del agente consultado"
                }],
                SELECTED_AGENT : None
            }
    return {
        **state,
        MESSAGES : state[MESSAGES] + [{
            "role" : ROLE_NODE_COMUNICATE_A2A_SUCCESS,
            "content" : result["content"]
        }],
        SELECTED_AGENT : None
    }


        


# Nodo encargado de dar la respuesta final del agente
async def node_final_answer(state: AgentState):
    print("Entering NODE: node_final_answer")
    # SOLO PARA VERSION FINAL, si ha ocurrido algun error en pasos intermedios devolvemos la ultima evaluacion valida, si no la hay, devolvemos el error
    """if "error" in state[MESSAGES][-1]["role"]:
        for message in state[MESSAGES]:
            if message["role"] == ROLE_NODE_EVALUATOR_PHASE1_SUCCESS:
                return {
                    MESSAGES : [{
                        "role" : ROLE_NODE_EVALUATOR_PHASE1_SUCCESS,
                        "content" : message["content"]
                    }]
                }"""
    return {
        **state
    }


# Router condicional encargado de guiar la ejecucion del grafo
def router(state : AgentState):
    tool = state.get(SELECTED_TOOL, None)
    if tool is None:
        return "node_final_answer"
    return "node_execute_selected_tool"


def router_retriever(state : AgentState):
    role = state[MESSAGES][-1].get("role")
    if role == ROLE_NODE_RETRIEVE_INFORMATION_SUCCESS:
        return NAME_NODE_EXECUTE_SELECTED_TOOL
    return NAME_NODE_EVALUATOR_PHASE1

def router_phase1(state : AgentState):
    role1 = state[MESSAGES][0].get("role") # rol para saber si la consulta del log la hizo otro agente, pidiento una segunda opinion, o un usuario
    role2 = state[MESSAGES][-1].get("role") # rol para saber si ha habido algun error en el estado anterior 
    if role2 == ROLE_NODE_EVALUATOR_PHASE1_SUCCESS:
        if role1 == 'agent':
            # Si la consulta original la hizo un agente pidiendo una segunda opinion devolvemos el resultado de la consulta sin llegar a phase2 (evitando bucles infinitos)
            return NAME_NODE_FINAL_ANSWER
        # solo si el indice de seguridad es muy bajo consultamos a otro agente, para mayor eficiencia
        confident_index = state[MESSAGES][-1]["content"].get("confident_index", False)
        return NAME_NODE_SELECT_AGENT
        if confident_index:
            try:
                confident_index = float(confident_index)
                if confident_index < 0.6:
                    return NAME_NODE_SELECT_AGENT
            except Exception as e:
                return NAME_NODE_FINAL_ANSWER
        return NAME_NODE_FINAL_ANSWER 
    return NAME_NODE_FINAL_ANSWER

def router_select_agent(state: AgentState):
    role = state[MESSAGES][-1].get("role")
    if role == ROLE_NODE_SELECT_AGENT_SUCCESS:
        return NAME_NODE_COMUNICATE_A2A
    return NAME_NODE_FINAL_ANSWER

def router_comunicate_a2a(state: AgentState):
    role = state[MESSAGES][-1].get("role")
    if role == ROLE_NODE_COMUNICATE_A2A_SUCCESS:
        return NAME_NODE_EVALUATOR_PHASE2
    return NAME_NODE_FINAL_ANSWER


def makeGraph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node(NAME_NODE_LOAD_TOOLS,node_load_tools)
    graph.add_node(NAME_NODE_RETRIEVE_INFORMATION,node_retrieve_information)
    graph.add_node(NAME_NODE_EXECUTE_SELECTED_TOOL,node_execute_selected_tool)
    graph.add_node(NAME_NODE_EVALUATOR_PHASE1, node_evaluator_phase1)
    graph.add_node(NAME_NODE_SELECT_AGENT,node_select_agent)
    graph.add_node(NAME_NODE_COMUNICATE_A2A,node_comunicate_a2a)
    graph.add_node(NAME_NODE_EVALUATOR_PHASE2,node_evaluator_phase2)
    graph.add_node(NAME_NODE_FINAL_ANSWER, node_final_answer)

    graph.add_edge(NAME_NODE_LOAD_TOOLS, NAME_NODE_RETRIEVE_INFORMATION)
    graph.add_conditional_edges(NAME_NODE_RETRIEVE_INFORMATION, router_retriever,{
        NAME_NODE_EXECUTE_SELECTED_TOOL : NAME_NODE_EXECUTE_SELECTED_TOOL,
        NAME_NODE_EVALUATOR_PHASE1 : NAME_NODE_EVALUATOR_PHASE1
    })
    graph.add_edge(NAME_NODE_EXECUTE_SELECTED_TOOL, NAME_NODE_EVALUATOR_PHASE1)
    graph.add_conditional_edges(NAME_NODE_EVALUATOR_PHASE1, router_phase1, {
        NAME_NODE_SELECT_AGENT : NAME_NODE_SELECT_AGENT,
        NAME_NODE_FINAL_ANSWER : NAME_NODE_FINAL_ANSWER
    })
    graph.add_conditional_edges(NAME_NODE_SELECT_AGENT, router_select_agent, {
        NAME_NODE_COMUNICATE_A2A : NAME_NODE_COMUNICATE_A2A,
        NAME_NODE_FINAL_ANSWER : NAME_NODE_FINAL_ANSWER
    })
    graph.add_conditional_edges(NAME_NODE_COMUNICATE_A2A, router_comunicate_a2a, {
        NAME_NODE_EVALUATOR_PHASE2 : NAME_NODE_EVALUATOR_PHASE2,
        NAME_NODE_FINAL_ANSWER : NAME_NODE_FINAL_ANSWER
    })
    graph.add_edge(NAME_NODE_EVALUATOR_PHASE2, NAME_NODE_FINAL_ANSWER)

    graph.set_entry_point("node_load_tools")

    return graph


async def main2():
    
    graph = makeGraph()
    agent = graph.compile()

    complete_example_log = """
                    log:
                    {"service":{"type":"system"},"agent":{"hostname":"internal-share","name":"internal-share","id":"480761c0-a9a7-48cc-a30b-f67100b44955","ephemeral_id":"cc234e3a-114f-402c-ab60-737cee803231","version":"7.13.2","type":"metricbeat"},"event":{"module":"system","dataset":"system.diskio","duration":846779},"@version":"1","metricset":{"period":45000,"name":"diskio"},"ecs":{"version":"1.9.0"},"host":{"name":"internal-share"},"@timestamp":"2022-01-20T17:55:07.556Z","tags":["beats_input_raw_event"],"system":{"diskio":{"name":"vda14","io":{"time":0,"ops":0},"write":{"time":0,"bytes":0,"count":0},"iostat":{"await":0,"queue":{"avg_size":0},"busy":0,"write":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}},"request":{"avg_size":0},"service_time":0,"read":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}}},"read":{"time":260,"bytes":991232,"count":242}}}}
                source:
                    monitoring
                label:
                    normal_log
                embedding:
                    -0.026113955, 0.06950478, -0.006266765, 0.004739833, -0.03442359, -0.026859924, 0.00034706658, -0.012981886, 0.06037722, 0.024253342, 0.0003067914, -0.07355884, -0.04211788, 0.07502378, 0.06244756, 0.022896104, 0.00987184, -0.08659755, -0.01094916, -0.013618529, 0.011028591, 0.015951412, 0.0003938146, -0.053967137, -0.044704095, -0.027095877, -0.087635756, -0.0
                """
    example_log = """
                    log:
                    {"service":{"type":"system"},"agent":{"hostname":"internal-share","name":"internal-share","id":"480761c0-a9a7-48cc-a30b-f67100b44955","ephemeral_id":"cc234e3a-114f-402c-ab60-737cee803231","version":"7.13.2","type":"metricbeat"},"event":{"module":"system","dataset":"system.diskio","duration":846779},"@version":"1","metricset":{"period":45000,"name":"diskio"},"ecs":{"version":"1.9.0"},"host":{"name":"internal-share"},"@timestamp":"2022-01-20T17:55:07.556Z","tags":["beats_input_raw_event"],"system":{"diskio":{"name":"vda14","io":{"time":0,"ops":0},"write":{"time":0,"bytes":0,"count":0},"iostat":{"await":0,"queue":{"avg_size":0},"busy":0,"write":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}},"request":{"avg_size":0},"service_time":0,"read":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}}},"read":{"time":260,"bytes":991232,"count":242}}}}
                source:
                    monitoring
                """
    example_log_2 = "log:Hola source:monitoring"

    result = await agent.ainvoke({
        MESSAGES: [{"role": "user", "content": example_log}],
        TOOLS: [],
        SELECTED_TOOL: None,
        SELECTED_TOOL_ARGS: None,
        AGENTS: [],
        SELECTED_AGENT: None
    })

    print(result[MESSAGES][-1])




async def main():
    graph = StateGraph(AgentState)

    graph.add_node("node_load_tools",node_load_tools)
    graph.add_node("node_retrieve_information",node_retrieve_information)
    graph.add_node("node_execute_selected_tool",node_execute_selected_tool)
    graph.add_node("node_final_answer", node_final_answer)

    graph.add_edge("node_load_tools", "node_retrieve_information")
    graph.add_edge("node_execute_selected_tool", "node_final_answer")
    graph.add_edge("node_final_answer", END)

    graph.add_conditional_edges("node_retrieve_information", router, {
        "node_final_answer" : "node_final_answer",
        "node_execute_selected_tool" : "node_execute_selected_tool"
    })

    graph.set_entry_point("node_load_tools")

    agent = graph.compile()

    example_log = """
                    log:
                    {"service":{"type":"system"},"agent":{"hostname":"internal-share","name":"internal-share","id":"480761c0-a9a7-48cc-a30b-f67100b44955","ephemeral_id":"cc234e3a-114f-402c-ab60-737cee803231","version":"7.13.2","type":"metricbeat"},"event":{"module":"system","dataset":"system.diskio","duration":846779},"@version":"1","metricset":{"period":45000,"name":"diskio"},"ecs":{"version":"1.9.0"},"host":{"name":"internal-share"},"@timestamp":"2022-01-20T17:55:07.556Z","tags":["beats_input_raw_event"],"system":{"diskio":{"name":"vda14","io":{"time":0,"ops":0},"write":{"time":0,"bytes":0,"count":0},"iostat":{"await":0,"queue":{"avg_size":0},"busy":0,"write":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}},"request":{"avg_size":0},"service_time":0,"read":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}}},"read":{"time":260,"bytes":991232,"count":242}}}}
                source:
                    monitoring
                label:
                    normal_log
                embedding:
                    -0.026113955, 0.06950478, -0.006266765, 0.004739833, -0.03442359, -0.026859924, 0.00034706658, -0.012981886, 0.06037722, 0.024253342, 0.0003067914, -0.07355884, -0.04211788, 0.07502378, 0.06244756, 0.022896104, 0.00987184, -0.08659755, -0.01094916, -0.013618529, 0.011028591, 0.015951412, 0.0003938146, -0.053967137, -0.044704095, -0.027095877, -0.087635756, -0.0
                """
    example_log_2 = "log:Hola source:monitoring"

    result = await agent.ainvoke({
        MESSAGES: [{"role": "user", "content": example_log}],
        TOOLS: [],
        SELECTED_TOOL: None,
        SELECTED_TOOL_ARGS: None,
        AGENTS: [],
        SELECTED_AGENT: None
    })

    print(result[MESSAGES][-1])




asyncio.run(main2())


