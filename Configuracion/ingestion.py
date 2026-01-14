from opensearchpy import OpenSearch
import pandas as pd
from opensearchpy import helpers

#---------Constantes-----------------------

# Path to training CSV subset
TRAIN_CSV = '/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/data/train-logs-dataset.csv'
# Embedding vector size (MiniLM = 384 dims)
VECTOR_SIZE = 384
# OpenSearch index name for vectorized logs
INDEX_NAME = "russellmitchell-logs-cosine"

#---------Funciones Auxiliares ------------

# Create the index with mapping for raw_message and embedding vector
def create_index(client):
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




# -----------Main Execution -------------------

open_search_client = OpenSearch(hosts=[{'host': 'localhost', 'port': 9200}],
                            http_auth=('admin', 'Developer@123'),
                            #http_auth=('admin', 'admin'),
                            use_ssl=True,
                            #use_ssl=False,
                            verify_certs=False,
                            timeout=60)

create_index(open_search_client)
train_df = pd.read_csv(TRAIN_CSV)
print("Training samples:", len(train_df))
print(train_df.head(5))
print(train_df["source"].value_counts())
# Ingest logs 
ingest_batches_from_csv_pipeline(train_df, open_search_client)
print("-----------INGESTION PROCESS FINNISHED UP SUCCESSFULLY -------------")



