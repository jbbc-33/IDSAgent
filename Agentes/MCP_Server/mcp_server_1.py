#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP
from opensearchpy import OpenSearch
from client_ports_constants import OSC_PORT1

#Constantes de configuracion
PORT_MCP1=8001

mcp = FastMCP("Search logs for context in labeling new logs", port=PORT_MCP1)


# ------------- CONSTANTES AUXILIARES --------------

MODEL_ID_FROM_FILE_PATH = "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/Configuracion/MODEL_ID_1.txt"
global MODEL_ID
INDEX_NAME="russellmitchell-logs-cosine"


# ------------- FUNCIONES AUXILIARES ---------------

def load_model_id():
    with open(MODEL_ID_FROM_FILE_PATH, 'r') as f:
        model_id=f.readline()
        return model_id
    return None
        
def neural_search(log_message : str, client : OpenSearch, model_id : str, source : str, k : int):

    if (source == None) | (source == ""):
        query = {
            "_source": {
                "excludes": [
                    "embedding"
                ]
            },
            "size": 2,
            "query": {
                "neural": {
                    "embedding": {
                        "query_text": f"{log_message}",
                        "model_id": f"{model_id}",
                        "k": k,
                    }
                }
            }
        }
    else:
        query = {
            "_source": {
                "excludes": [
                    "embedding"
                ]
            },
            "size": 2,
            "query": {
                "neural": {
                    "embedding": {
                        "query_text": f"{log_message}",
                        "model_id": f"{model_id}",
                        "k": k,
                        "filter": {
                            "bool": {
                                "must": [
                                    {
                                        "term": {
                                            "source": f"{source}"
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    response = client.search(index=INDEX_NAME, body=query)
    results = []
    # Extract results

    for hit in response["hits"]["hits"]:
        log_entry = {
            # "raw_message": hit["_source"]["embedding"],
            # Default to "No Label" if missing
            "log": hit["_source"].get("log"),
            "label": hit["_source"].get("label", "No Label"),
            # Similarity score (optional, useful for ranking)
            "score": hit["_score"]
        }
        results.append(log_entry)
    if not results:
        print("SOURCE", source, "LEN", len(source))

        if '-' in source:
            source = source.split('-')
            source = source[1]
        elif "_" in source:
            source = source.split('_')
            source = source[1]
        else:
            source = None
        results = neural_search(log_message, client, MODEL_ID, source, k=k)
    return results





# ------------- TOOLS EXPUESTAS --------------------


# ------------- Tool busqueda neuronal -------------


@mcp.tool(
        name="search_logs",
        description="Get retrieved similar logs from RAG, obtains similiar logs to the one given as the argument log_message from source",
)
async def search_logs(log_message: str, source:str) -> str:
    """Get retrieved logs from RAG, obtains similiar logs to the one given as the argument log_message from source"""

    clientOS = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT1}],
                            http_auth=('admin', 'Developer@123'),
                            #http_auth=('admin', 'admin'),
                            use_ssl=True,
                            #use_ssl=False,
                            verify_certs=False,
                            timeout=60)

    rag= neural_search(log_message, clientOS, MODEL_ID, source,k=3)
    str_rag=str(rag)
    return str_rag





if __name__ == "__main__":
    MODEL_ID=load_model_id()
    if MODEL_ID != None:
        print(f"model_id cargado correctamente: {MODEL_ID}")
    mcp.run(transport="streamable-http")