from fastapi import FastAPI
from ollama import ChatResponse, chat, embed
from qdrant_client import QdrantClient, models as qdrant_models

qdrant_client = QdrantClient("localhost", port=6333)
if not qdrant_client.get_collections().collections:
    qdrant_client.create_collection(
        collection_name="documents",
        vectors_config=qdrant_models.VectorParams(
            size=2048,
            distance=qdrant_models.Distance.COSINE,
        ),
    )

app = FastAPI()

@app.post("/chat/")
def chat_completion(query: str):
    query_embedding = embed(model='llama3.2:1b', input=query)['embeddings'][0]

    search_result = qdrant_client.query_points(
        collection_name="documents",
        query=query_embedding,
        limit=1,
        with_payload=True,
    )

    print(search_result)
    context_text = ""
    if search_result.points:
        context_text = str(search_result.points[0].payload.get("text", ""))

    prompt = f"context: {context_text}\n\nquery:{query}" if context_text else query

    print(prompt)

    response: ChatResponse = chat(model='llama3.2:1b', messages=[
      {
        'role': 'user',
        'content': prompt,
      },
    ])
    return {"response": response['message']['content']}

@app.post("/document/")
def text(text: str):
    text_embedding = embed(model='llama3.2:1b', input=text)['embeddings'][0]
    print(len(text_embedding))
    qdrant_client.upsert(
        collection_name="documents",
        points=[
            {
                "id": 1,
                "vector": text_embedding,
                "payload": {"text": text},
            }
        ],
    )
    return {"ok": True}
