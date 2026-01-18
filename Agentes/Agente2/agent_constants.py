# Constantes de configuracion
URL_MCP_SERVER = "http://localhost:8000/mcp"
URL_API_OLLAMA_BASE = "http://localhost:11434"
URL_API_OLLAMA_CHAT = "http://localhost:11434/api/chat"
MODEL_OLLAMA = "qwen2.5:3b"
URL_EXPOSED_A2A_AGENTS=["http://localhost:9999"]
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
NAME_NODE_LOAD_AGENTS = "node_load_agents"
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