import os
import dotenv
from ollama import Client

dotenv.load_dotenv()

OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "llama3.2:1b")
OLLAMA_LOCAL_HOST = os.environ.get("OLLAMA_LOCAL_HOST", "http://localhost:11434")

client = Client(host=OLLAMA_LOCAL_HOST)

def embed_text(text: str) -> list[float]:
    return client.embed(model=OLLAMA_EMBED_MODEL, input=text)["embeddings"][0]
