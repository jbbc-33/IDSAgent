import logging

from typing import Any
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

URL_AGENT_SERVING='http://localhost:9998/'

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

    
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind':'text','text': f'{EXAMPLE_LOG}'},
                ],
                'messageId': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))
        print("PARTE-----------------------------------")
        print(response.model_dump(mode='json', exclude_none=True)["result"]["parts"][0]["data"])
        

        # Para mandar mensaje en modo streaming
        """
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))
        """
        


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())