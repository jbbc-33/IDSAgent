import urllib3
urllib3.disable_warnings()
import threading as th

from opensearchpy import OpenSearch
import time
import json

from client_ports_constants import *

MODEL_ID_PATH_1 = "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/Configuracion/MODEL_ID_1.txt"
MODEL_ID_PATH_2 = "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/Configuracion/MODEL_ID_2.txt"



def wait_for_task(task_id, client : OpenSearch):
    print(f"Esperando task {task_id}")

    while True:
        response = client.transport.perform_request(
            "GET",
            f"/_plugins/_ml/tasks/{task_id}"
        )
        state = response.get("state")
        print(" → Estado:", state)

        if state == "COMPLETED":
            print("Task completado")
            return response

        if state == "FAILED":
            raise RuntimeError(f"Task falló:\n{json.dumps(response, indent=2)}")

        time.sleep(3)

def setup(client : OpenSearch, path):
    model_group_id=""
    print("\nRegistrando model group")
    try:
        model_group = client.transport.perform_request(
            "POST",
            "/_plugins/_ml/model_groups/_register",
            body={
                "name": "local_model_group",
                "description": "Model group for MiniLM"
            }
        )
        model_group_id = model_group["model_group_id"]
        print("MODEL_GROUP_ID:", model_group_id)

    except Exception as e:
        if "already being used by a model group" in str(e):
            print("Model group ya existe. Recuperando ID")

            groups = client.transport.perform_request(
                "GET",
                "/_plugins/_ml/model_groups/_search",
                body={
                    "query": {"match_all": {}}
                }
            )

            for g in groups.get("model_groups", []):
                if g["name"] == "local_model_group":
                    model_group_id = g["model_group_id"]
                    print("MODEL_GROUP_ID (EXISTENTE):", model_group_id)
                    break
        else:
            raise e


    print("\nRegistrando modelo MiniLM")
    register_model = client.transport.perform_request(
        "POST",
        "/_plugins/_ml/models/_register",
        body={
            "name": "huggingface/sentence-transformers/all-MiniLM-L6-v2",
            "version": "1.0.1",
            "model_group_id": model_group_id,
            "model_format": "TORCH_SCRIPT"
        }
    )

    task_id = register_model["task_id"]
    print("TASK_ID REGISTRO:", task_id)

    task_result = wait_for_task(task_id, client)
    model_id = task_result["model_id"]
    print("MODEL_ID:", model_id)


    print("\nDesplegando modelo")
    deploy = client.transport.perform_request(
        "POST",
        f"/_plugins/_ml/models/{model_id}/_deploy"
    )

    deploy_task_id = deploy["task_id"]
    print("TASK_ID DEPLOY:", deploy_task_id)

    wait_for_task(deploy_task_id, client)


    print("\nCreando ingest pipeline log-filter-pipeline")

    client.ingest.put_pipeline(
        id="log-filter-pipeline",
        body={
            "description": "Pipeline to embed logs using MiniLM",
            "processors": [
                {
                    "text_embedding": {
                        "model_id": model_id,
                        "field_map": {
                            "log": "embedding"
                        }
                    }
                }
            ]
        }
    )

    print("Model Group:", model_group_id)
    print("Model ID:", model_id)
    print("Pipeline ID: log-filter-pipeline")

    with open(path, "w") as f:
        f.write(model_id)

    print(f"Model ID escrito en ruta: "+path)




if __name__ == "__main__":

    input_text = "Pulsar 1 ----> Configurar solo 1\nPulsar 2 ----> Configurar 2\nPulsar 3 ----> Configurar 2 de manera concurrente\n"
    opcion = input(input_text)
    
    if opcion == "1":
        client1 = OpenSearch(
            hosts=[{"host": "localhost", "port": OSC_PORT1}],
            http_auth=("admin", "Developer@123"),
            use_ssl=True,
            verify_certs=False
        )
        setup(client1, MODEL_ID_PATH_1)
    elif opcion == "2":
        client1 = OpenSearch(
            hosts=[{"host": "localhost", "port": OSC_PORT1}],
            http_auth=("admin", "Developer@123"),
            use_ssl=True,
            verify_certs=False
        )
        client2 = OpenSearch(
            hosts=[{"host": "localhost", "port": OSC_PORT2}],
            http_auth=("admin", "Developer@123"),
            use_ssl=True,
            verify_certs=False
        )
        setup(client1, MODEL_ID_PATH_1)
        setup(client2, MODEL_ID_PATH_2)
    elif opcion == "3":
        client1 = OpenSearch(
            hosts=[{"host": "localhost", "port": OSC_PORT1}],
            http_auth=("admin", "Developer@123"),
            use_ssl=True,
            verify_certs=False
        )
        client2 = OpenSearch(
            hosts=[{"host": "localhost", "port": OSC_PORT2}],
            http_auth=("admin", "Developer@123"),
            use_ssl=True,
            verify_certs=False
        )
        hilo1 = th.Thread(target=setup, args=(client1, MODEL_ID_PATH_1))
        hilo2 = th.Thread(target=setup, args=(client2, MODEL_ID_PATH_2))
        hilo1.start()
        hilo2.start()
        hilo1.join()
        hilo2.join()
        print("\n\n PIPELINES CONFIGURADOS")
    elif opcion == "11":
        client1 = OpenSearch(
            hosts=[{"host": "localhost", "port": OSC_PORT1}],
            http_auth=("admin", "Developer@123"),
            use_ssl=True,
            verify_certs=False
        )
        setup(client1, MODEL_ID_PATH_1)
    elif opcion == "22":
        client1 = OpenSearch(
            hosts=[{"host": "localhost", "port": OSC_PORT2}],
            http_auth=("admin", "Developer@123"),
            use_ssl=True,
            verify_certs=False
        )
        setup(client1, MODEL_ID_PATH_2)
    else:
        print("\nSelecciona una de las posibles opciones\n")
        exit(2)