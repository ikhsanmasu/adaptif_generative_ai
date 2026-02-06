from ollama import ChatResponse, AsyncClient, Client
from typing import Union
import os
import dotenv

dotenv.load_dotenv()

OLLAMA_LOCAL_HOST = os.environ.get("OLLAMA_LOCAL_HOST", "http://localhost:11434")

OLLAMA_CLOUD_HOST = os.environ.get("OLLAMA_CLOUD_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")

local_client = AsyncClient(
    host=OLLAMA_LOCAL_HOST
)

cloud_client = AsyncClient(
    host=OLLAMA_CLOUD_HOST,
    headers={'Authorization': 'Bearer ' + OLLAMA_API_KEY}
)

def prompt_template(prompt: str, variables: dict) -> str:
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{key}}}", value)
    return prompt

async def responses(message: Union[str, list], model: str, tools: list = [], stream: str = False, think: Union[bool, str] = False) -> str: 
    if isinstance(message, str):
        message = [
            {
                "role": "user",
                "content": message
            }
        ]

    if 'cloud' in model:
        client = cloud_client
    else:
        client = local_client

    response: ChatResponse = await client.chat(
        model=model, 
        messages=message,
        tools = tools,
        stream=stream
    ) 
    return response


local_client_sync = Client(
    host=OLLAMA_LOCAL_HOST
)

cloud_client_sync = Client(
    host=OLLAMA_CLOUD_HOST,
    headers={'Authorization': 'Bearer ' + OLLAMA_API_KEY}
)

def responses_sync(message: Union[str, list], model: str, tools: list = [], stream: str = False, think: Union[bool, str] = False) -> str: 
    if isinstance(message, str):
        message = [
            {
                "role": "user",
                "content": message
            }
        ]

    if 'cloud' in model:
        client = cloud_client_sync
    else:
        client = local_client_sync

    response: ChatResponse = client.chat(
        model=model, 
        messages=message,
        tools = tools,
        stream=stream
    ) 
    return response

