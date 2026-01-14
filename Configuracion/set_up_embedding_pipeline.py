import urllib3
urllib3.disable_warnings()

from opensearchpy import OpenSearch
import time
import json

MODEL_ID_PATH = "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/Configuracion/MODEL_ID.txt"

client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "Developer@123"),
    use_ssl=True,
    verify_certs=False
)

def wait_for_task(task_id):
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

task_result = wait_for_task(task_id)
model_id = task_result["model_id"]
print("MODEL_ID:", model_id)


print("\nDesplegando modelo")
deploy = client.transport.perform_request(
    "POST",
    f"/_plugins/_ml/models/{model_id}/_deploy"
)

deploy_task_id = deploy["task_id"]
print("TASK_ID DEPLOY:", deploy_task_id)

wait_for_task(deploy_task_id)


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

with open(MODEL_ID_PATH, "w") as f:
    f.write(model_id)

print(f"Model ID escrito en ruta: "+MODEL_ID_PATH)
