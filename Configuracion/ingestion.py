from opensearchpy import OpenSearch
import pandas as pd
from opensearchpy import helpers
import threading as th
from client_ports_constants import *

#---------Constantes-----------------------

# Path to training CSV subset
TRAIN_CSV = '/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/data/train-logs-dataset.csv'
TRAIN_CSV_1 = "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/data/1-train-logs-dataset.csv"
TRAIN_CSV_2 = "/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/data/2-train-logs-dataset.csv"
# Embedding vector size (MiniLM = 384 dims)
VECTOR_SIZE = 384
# OpenSearch index name for vectorized logs
INDEX_NAME = "russellmitchell-logs-cosine"


#---------Funciones Auxiliares ------------

# Create the index with mapping for raw_message and embedding vector
def create_index(client : OpenSearch):
    mapping = {
        "settings": {
            "index.knn": "true",
            "default_pipeline": "log-filter-pipeline"

        },
        "mappings": {
            "properties": {
                "log": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                            "dimension": VECTOR_SIZE,
                    "data_type": "float",
                    "mode": "on_disk",
                    "compression_level": "32x",
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "cosinesimil",
                                  "parameters": {
                                      "ef_construction": 64,
                                      "m": 35
                                  }
                    }
                },  # for all-MiniLM-L6-v2, the dimension is 384
                "source": {"type": "text"},
                "label": {"type": "text"}
            }
        }
    }
    if not client.indices.exists(index = INDEX_NAME):
        client.indices.create(index=INDEX_NAME, body=mapping)
        print(f"Index '{INDEX_NAME}' created.")
    else:
        print(f"Index '{INDEX_NAME}' already exists.")




def create_action(log_message, source, label):
    doc = {
        "log": log_message,
        "source": source,
        "label": label
    }
    return {
        "_index": INDEX_NAME,
        "_source": doc
    }




def send_actions(client, actions):
    helpers.bulk(client, actions)




def ingest_batches_from_csv_pipeline(data, client, batch_size=64):
    actions = []
    batch_logs = []
    batch_labels = []
    batch_sources = []
    for idx, row in enumerate(data.itertuples(index=False)):
        batch_logs.append(row.log_message)
        batch_sources.append(row.source)
        batch_labels.append(row.label)

        # When batch is full or at the end of the dataset
        if len(batch_logs) == batch_size or idx == len(data) - 1:
            # Build actions
            for log_message, source, label in zip(batch_logs, batch_sources, batch_labels):
                actions.append(create_action(log_message, source, label))

            # Bulk insert
            if actions:
                send_actions(client, actions)
                print(
                    f"Ingested {len(actions)} documents into '{INDEX_NAME}' index.")

            # Reset batches
            actions = []
            batch_logs = []
            batch_labels = []




def setup(client : OpenSearch, train_path : str):
    #create_index()
    create_index(client)
    train_df = pd.read_csv(train_path)
    print("Training samples:", len(train_df))
    print(train_df.head(5))
    print(train_df["source"].value_counts())
    # Ingest logs 
    ingest_batches_from_csv_pipeline(train_df, client)
    print("-----------INGESTION PROCESS FINNISHED UP SUCCESSFULLY -------------")


# -----------Main Execution -------------------


if __name__ == "__main__":
    input_text = "Pulsar 1 ----> Ingerir solo 1 contenedor\nPulsar 2 ----> Ingerir 2 contenedores\nPulsar 3 ----> Ingerir 2 contenedores de manera concurrente\n"
    opcion = input(input_text)
    
    if opcion == "1":
        client1 = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT1}],
                                http_auth=('admin', 'Developer@123'),
                                #http_auth=('admin', 'admin'),
                                use_ssl=True,
                                #use_ssl=False,
                                verify_certs=False,
                                timeout=60)
        setup(client=client1, train_path=TRAIN_CSV)
    elif opcion == "2":
        client1 = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT1}],
                                http_auth=('admin', 'Developer@123'),
                                #http_auth=('admin', 'admin'),
                                use_ssl=True,
                                #use_ssl=False,
                                verify_certs=False,
                                timeout=60)
        client2 = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT2}],
                                http_auth=('admin', 'Developer@123'),
                                #http_auth=('admin', 'admin'),
                                use_ssl=True,
                                #use_ssl=False,
                                verify_certs=False,
                                timeout=60)
        try:
            setup(client=client1, train_path=TRAIN_CSV_1)
        except Exception as e:
            print(e)
        try:
            setup(client=client2, train_path=TRAIN_CSV_2)
        except Exception as e:
            print(e)
    elif opcion == "3":
        client1 = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT1}],
                                http_auth=('admin', 'Developer@123'),
                                #http_auth=('admin', 'admin'),
                                use_ssl=True,
                                #use_ssl=False,
                                verify_certs=False,
                                timeout=60)
        client2 = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT2}],
                                http_auth=('admin', 'Developer@123'),
                                #http_auth=('admin', 'admin'),
                                use_ssl=True,
                                #use_ssl=False,
                                verify_certs=False,
                                timeout=60)
        h1=th.Thread(target=setup, args=(client1, TRAIN_CSV_1))
        h2 = th.Thread(target=setup, args=(client2, TRAIN_CSV_2))
        h1.start()
        h2.start()
        h1.join()
        h2.join()
        print("\n\n LOGS INGERIDOS")
    elif opcion == "11":
        client1 = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT1}],
                                http_auth=('admin', 'Developer@123'),
                                #http_auth=('admin', 'admin'),
                                use_ssl=True,
                                #use_ssl=False,
                                verify_certs=False,
                                timeout=60)
        setup(client=client1, train_path=TRAIN_CSV_1)
    elif opcion == "22":
        client2 = OpenSearch(hosts=[{'host': 'localhost', 'port': OSC_PORT2}],
                                http_auth=('admin', 'Developer@123'),
                                #http_auth=('admin', 'admin'),
                                use_ssl=True,
                                #use_ssl=False,
                                verify_certs=False,
                                timeout=60)
        setup(client=client2, train_path=TRAIN_CSV_2)
    else:
        print("\nSelecciona una de las posibles opciones: 1 o 2\n")
        exit(2)


