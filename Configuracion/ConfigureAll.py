import subprocess
from client_ports_constants import *
from opensearchpy import OpenSearch
from set_up_embedding_pipeline import setup_pipeline, MODEL_ID_PATH_1, MODEL_ID_PATH_2
from ingestion import setup_ingestion, TRAIN_CSV_1, TRAIN_CSV_2
import requests
import time
import argparse


PATH_DOCKER_COMPOSE_YAML = "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/Docker"
URL_OS="http://localhost:"
TIMEOUT = 320  # segundos



def create_client(port : int) -> OpenSearch:
    return OpenSearch(hosts=[{'host': 'localhost', 'port': port}],
                        http_auth=('admin', 'Developer@123'),
                        #http_auth=('admin', 'admin'),
                        use_ssl=True,
                        #use_ssl=False,
                        verify_certs=False,
                        timeout=60)

def check_OS_ready(client : OpenSearch, url : str) -> bool:
    start = time.time()
    while True:
        try:
            """
            r = requests.get(
                f"{url}/_cluster/health",
                timeout=2
            )
            r.raise_for_status()

            status = r.json()["status"]
            print(status)
            if status in ("green", "yellow"):
                print("OPENSEARCH LISTO------------------------------------------")
                return True
            """
            health = client.cluster.health()
            status = health.get("status", "red")
            print(f"Estado actual del cluster: {status}")

            if status in ("green", "yellow"):
                print("OpenSearch listo")
                time.sleep(30)
                return True
                
        except Exception:
            pass
        if time.time() - start > TIMEOUT:
            raise TimeoutError("OpenSearch no respondio a tiempo")
        time.sleep(15)

def comp1_config():
    subprocess.run(
            ["docker", "compose", "up", "-d", "opensearch1"],
            cwd=PATH_DOCKER_COMPOSE_YAML,
            check=True,
            timeout=120
    )
    client1 = create_client(port=OSC_PORT1)
    time.sleep(10)
    if check_OS_ready(client=client1, url=URL_OS+str(OSC_PORT1)):
        print("\n\nCONFIGURANDO CLIENTE 1 ----------------------------------\n")     
        setup_pipeline(client=client1, path=MODEL_ID_PATH_1)
        try:
            setup_ingestion(client=client1, train_path=TRAIN_CSV_1)
        except Exception as e:
            subprocess.run(
                ["docker", "compose", "restart", "opensearch1"],
                cwd=PATH_DOCKER_COMPOSE_YAML,
                check=True,
                timeout=120
            )
            time.sleep(20)
            if check_OS_ready(client=client1, url=URL_OS+str(OSC_PORT1)):
                client1 = create_client(port=OSC_PORT1)
                setup_pipeline(client=client1, path=MODEL_ID_PATH_1)
                time.sleep(20)
                setup_ingestion(client=client1, train_path=TRAIN_CSV_1)

def comp2_config():
    subprocess.run(
            ["docker", "compose", "up", "-d", "opensearch2"],
            cwd=PATH_DOCKER_COMPOSE_YAML,
            check=True,
            timeout=120
    )
    client2 = create_client(port=OSC_PORT2)
    time.sleep(10)
    if check_OS_ready(client=client2, url=URL_OS+str(OSC_PORT2)):
        print("\n\nCONFIGURANDO CLIENTE 2 ----------------------------------\n") 
        setup_pipeline(client=client2, path=MODEL_ID_PATH_2)
        try:
            #time.sleep(60)
            setup_ingestion(client=client2, train_path=TRAIN_CSV_2)
            #time.sleep(60)
        except Exception as e:
            subprocess.run(
                ["docker", "compose", "restart", "opensearch2"],
                cwd=PATH_DOCKER_COMPOSE_YAML,
                check=True,
                timeout=120
            )
            #time.sleep(60)
            time.sleep(20)
            if check_OS_ready(client=client2, url=URL_OS+str(OSC_PORT2)):
                client2 = create_client(port=OSC_PORT2)
                setup_pipeline(client=client2, path=MODEL_ID_PATH_2)
                #time.sleep(200)
                time.sleep(20)
                setup_ingestion(client=client2, train_path=TRAIN_CSV_2)
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Ejemplo de script con argumentos")
    
    help_text = "op 1 -> comp1\nop 2 -> comp2\nop 3 -> comp1 y comp2\n"
    
    parser.add_argument("op", type=int, help="Nombre de la persona", default=1)
    
    args = parser.parse_args()
    
    # Usar los argumentos
    if args.op == 1:
        comp1_config()
    elif args.op == 2:
        comp2_config()
    elif args.op == 3:
        comp1_config()
        time.sleep(120)
        comp2_config()
    else:
        print("Selecciona un argumento o numero de opcion valido")
        exit(2)
    """
    subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=PATH_DOCKER_COMPOSE_YAML,
            check=True,
            timeout=120
    )
    client1 = create_client(port=OSC_PORT1)
    time.sleep(10)
    if check_OS_ready(client=client1, url=URL_OS+str(OSC_PORT1)):
        print("\n\nCONFIGURANDO CLIENTE 1 ----------------------------------\n")     
        setup_pipeline(client=client1, path=MODEL_ID_PATH_1)
        try:
            setup_ingestion(client=client1, train_path=TRAIN_CSV_1)
        except Exception as e:
            subprocess.run(
                ["docker", "compose", "restart", "opensearch1"],
                cwd=PATH_DOCKER_COMPOSE_YAML,
                check=True,
                timeout=120
            )
            time.sleep(20)
            if check_OS_ready(client=client1, url=URL_OS+str(OSC_PORT1)):
                client1 = create_client(port=OSC_PORT1)
                setup_pipeline(client=client1, path=MODEL_ID_PATH_1)
                time.sleep(20)
                setup_ingestion(client=client1, train_path=TRAIN_CSV_1)
    
    time.sleep(240)
    client2 = create_client(port=OSC_PORT2)
    time.sleep(10)
    if check_OS_ready(client=client2, url=URL_OS+str(OSC_PORT2)):
        print("\n\nCONFIGURANDO CLIENTE 2 ----------------------------------\n") 
        setup_pipeline(client=client2, path=MODEL_ID_PATH_2)
        try:
            time.sleep(60)
            setup_ingestion(client=client2, train_path=TRAIN_CSV_2)
            time.sleep(60)
        except Exception as e:
            subprocess.run(
                ["docker", "compose", "restart", "opensearch2"],
                cwd=PATH_DOCKER_COMPOSE_YAML,
                check=True,
                timeout=120
            )
            time.sleep(60)
            if check_OS_ready(client=client2, url=URL_OS+str(OSC_PORT2)):
                client2 = create_client(port=OSC_PORT2)
                setup_pipeline(client=client2, path=MODEL_ID_PATH_2)
                time.sleep(200)
                setup_ingestion(client=client2, train_path=TRAIN_CSV_2)
    """