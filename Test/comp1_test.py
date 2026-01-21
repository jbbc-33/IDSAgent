#!/usr/bin/env python3
import logging

from typing import Any
from uuid import uuid4
import pandas as pd
import asyncio
import json

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

PATH_TEST_CSV="/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/data/1-test-logs-dataset.csv"
PATH_EVAL_CSV="/home/julio/Escritorio/otherTFG/PruebasMias/Proyecto/data/1-eval-logs-dataset.csv"

#Valor para columnas faltantes de final test tras evaluar
MISSING_DATA = "missing"
#Keys del dataset final test
CONFIDENT_INDEX = "confident_index"
LLM_LABEL = "llm_label"
REASON = "reason"
LOG = "log_message"
SOURCE = "source"
LABEL = "label"

#Constantes para saber si el agente a logrado clasificar
ROLE_NODE_EVALUATOR_PHASE1_SUCCESS = "phase1"
ROLE_NODE_EVALUATOR_PHASE2_SUCCESS = "phase2"

URL_AGENT_SERVING='http://localhost:9999/'

EXAMPLE_LOG = """
                log:
                    {"service":{"type":"system"},"agent":{"hostname":"internal-share","name":"internal-share","id":"480761c0-a9a7-48cc-a30b-f67100b44955","ephemeral_id":"cc234e3a-114f-402c-ab60-737cee803231","version":"7.13.2","type":"metricbeat"},"event":{"module":"system","dataset":"system.diskio","duration":846779},"@version":"1","metricset":{"period":45000,"name":"diskio"},"ecs":{"version":"1.9.0"},"host":{"name":"internal-share"},"@timestamp":"2022-01-20T17:55:07.556Z","tags":["beats_input_raw_event"],"system":{"diskio":{"name":"vda14","io":{"time":0,"ops":0},"write":{"time":0,"bytes":0,"count":0},"iostat":{"await":0,"queue":{"avg_size":0},"busy":0,"write":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}},"request":{"avg_size":0},"service_time":0,"read":{"await":0,"request":{"merges_per_sec":0,"per_sec":0},"per_sec":{"bytes":0}}},"read":{"time":260,"bytes":991232,"count":242}}}}
                source:
                    monitoring
                """

TIMEOUT = 600

async def main() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance


    base_url = URL_AGENT_SERVING

    async with httpx.AsyncClient(timeout=TIMEOUT) as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )

        # Fetch Public Agent Card and Initialize Client
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(
                f'Attempting to fetch public agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}'
            )
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info('Successfully fetched public agent card:')
            logger.info(
                _public_card.model_dump_json(indent=2, exclude_none=True)
            )
            final_agent_card_to_use = _public_card
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )

        except Exception as e:
            logger.error(
                f'Critical error fetching public agent card: {e}', exc_info=True
            )
            raise RuntimeError(
                'Failed to fetch the public agent card. Cannot continue.'
            ) from e

        
        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info('A2AClient initialized.')


        #Index(['Unnamed: 0', 'log_message', 'source', 'label'], dtype='object')
        test_data = pd.read_csv(PATH_TEST_CSV, index_col=0)
        #test_data = test_data.drop(columns=["Unnamed: 0"])
        #test_data = test_data.reset_index(drop=True)
        test_data[LLM_LABEL] = pd.Series(pd.NA, index=test_data.index, dtype="string")
        test_data[CONFIDENT_INDEX] = pd.Series(pd.NA, index=test_data.index, dtype="Float64")
        test_data[REASON] = pd.Series(pd.NA, index=test_data.index, dtype="string")
        
        for i, row in test_data.iterrows():      

            send_message_payload: dict[str, Any] = {
                'message': {
                    'role': 'user',
                    'parts': [
                        {'kind':'text','text': f'{row[LOG]}'},
                    ],
                    'messageId': uuid4().hex,
                },
            }
            request = SendMessageRequest(
                id=str(uuid4()), params=MessageSendParams(**send_message_payload)
            )

            response = await client.send_message(request)
            
            data=None
            try:
                mes = response.model_dump(mode='json', exclude_none=True)
                role = mes["result"]["parts"][0]["data"]['role']
                data = mes["result"]["parts"][0]["data"]['content']
                print("PARTE-----------------------------------")
                print(data)
                if role != ROLE_NODE_EVALUATOR_PHASE1_SUCCESS and role != ROLE_NODE_EVALUATOR_PHASE2_SUCCESS:
                    continue #Si el rol no es exitoso, nos indica que no ha podido clasificar bien el log actual y pasamos al siguiente
                llm_label=data.get('label', None)
                if llm_label == None:
                    continue #Si no hay label por parte del llm directamente no apuntamos resultados para el log actual y pasamos a la siguiente
                try:
                    llm_label = str(llm_label)
                    test_data.loc[i, LLM_LABEL] = llm_label
                except Exception:
                    continue #Si no podemos convertir el label a cadena no seguimos analizando
                try:
                    conf_index = data.get('confident_index',MISSING_DATA)
                    if conf_index != MISSING_DATA:
                        conf_index = float(conf_index)
                        test_data.loc[i, CONFIDENT_INDEX] = conf_index
                    else:
                        test_data.loc[i, CONFIDENT_INDEX] = pd.NA
                except Exception:
                    test_data.loc[i, CONFIDENT_INDEX] = pd.NA
                try:
                    reason = data.get('reason',MISSING_DATA)
                    if reason != MISSING_DATA:
                        reason = str(reason)
                        test_data.loc[i, REASON] = reason
                    else:
                        test_data.loc[i, REASON] = pd.NA
                except Exception:
                    test_data.loc[i, REASON] = pd.NA
                
                print("CAMBIO REGISTRADO")
            except Exception as e:
                print("No ha sido posible extraer el mensaje")

        test_data.to_csv(PATH_EVAL_CSV)


        """
        {'role': 'phase1', 'content': {'label': 'normal_log', 'confident_index': 1.0, 'reason': 'The log details system disk I/O statistics and does not show any suspicious activity, indicating a normal operational event.'}}
        """


if __name__ == '__main__':
    asyncio.run(main())