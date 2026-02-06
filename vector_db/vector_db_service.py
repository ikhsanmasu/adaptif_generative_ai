from qdrant_client import QdrantClient, AsyncQdrantClient, models
from embedding import embed_text
import uuid
import logging
import os
import dotenv

dotenv.load_dotenv()

QDRANT_HOST = os.environ.get('QDRANT_HOST', 'localhost')
QDRANT_PORT = int(os.environ.get('QDRANT_PORT', 6333))
QDRANT_ID_NAMESPACE = os.environ.get('QDRANT_ID_NAMESPACE', '2f3f1b4a-9d6e-4fbb-8d74-6c2f1b7c8a91')
QDRANT_ID_NAMESPACE_UUID = uuid.UUID(QDRANT_ID_NAMESPACE)

async_qdrant_client = AsyncQdrantClient(QDRANT_HOST, port=QDRANT_PORT)

logger = logging.getLogger(__name__)





async def search_documents(query, tenant:str, limit:int = 2) -> str:
    try:
        query_vector = embed_text(query)
        collection_name = f"tenants_{tenant}_documents"

        search_result = await async_qdrant_client.query_points(
            collection_name=collection_name,
            query=query_vector,
            with_payload=True,
            limit= limit
        )

        documents = []

        logger.debug(f"Qdrant search results: {search_result}")

        for point in search_result.points:
            payload = point.payload
            documents.append({
                "chunk_id": payload['chunk_id'],
                "tenant": payload['tenant'],
                "doc_id": payload['doc_id'],
                "index": payload['index'],
                "title": payload['title'],
                "text": payload['text'],
                "score": point.score
            })
        
        logger.debug(f"Document results: {documents}")
        return documents
    except Exception as e:
        logger.error(f"Error during search_documents: {e}")
        return []

async def add_document(tenant:str, doc_id:str, title:str, chunks:list[str]):
    collection_name = f"tenants_{tenant}_documents"
    points = []
    for idx, chunk in enumerate(chunks):
        text_embedding = embed_text(chunk)
        point = models.PointStruct(
            id=uuid.uuid5(QDRANT_ID_NAMESPACE_UUID, f"{tenant}:{doc_id}:{idx}"),
            vector=text_embedding,
            payload={
                "chunk_id": f"{tenant}:{doc_id}:{idx}",
                "tenant": tenant,
                "doc_id": doc_id,
                "index": idx,
                "title": title,
                "text": chunk,
                "original_text": chunk,
                "audited_text": "",
                "audit_status": "pending",
                "audit_version": 0
            }
        )
        points.append(point)

    if not await async_qdrant_client.collection_exists(
            collection_name=collection_name
        ):
            await async_qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=2048,
                distance=models.Distance.COSINE,
            ),
        )
            
    await async_qdrant_client.upsert(
        collection_name=collection_name,
        points=points
    )

async def update_point(chunk_id:str, collection_name:str, payload:dict):
    point_id = uuid.uuid5(QDRANT_ID_NAMESPACE_UUID, chunk_id)
    new_vector = embed_text(payload['audited_text'])
    await async_qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=new_vector,
                    payload=None,
                )
            ],
            wait=True,
    )

    await async_qdrant_client.set_payload(
        collection_name=collection_name,
        points=[point_id],
        payload=payload
    )

async def get_point(chunk_id:str, collection_name:str) -> models.PointStruct | None:
    point_id = uuid.uuid5(QDRANT_ID_NAMESPACE_UUID, chunk_id)

    result = await async_qdrant_client.retrieve(
        collection_name=collection_name,
        ids=[point_id],
        with_payload=True
    )

    return result

########################### Syncronous client #################################

sync_qdrant_client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)

def search_documents_sync(query, tenant:str, limit:int = 2) -> str:
    try:
        query_vector = embed_text(query)
        collection_name = f"tenants_{tenant}_documents"

        search_result = sync_qdrant_client.query_points(
            collection_name=collection_name,
            query=query_vector,
            with_payload=True,
            limit= limit
        )

        documents = []

        logger.debug(f"Qdrant search results: {search_result}")

        for point in search_result.points:
            payload = point.payload
            documents.append({
                "chunk_id": payload['chunk_id'],
                "tenant": payload['tenant'],
                "doc_id": payload['doc_id'],
                "index": payload['index'],
                "title": payload['title'],
                "text": payload['text'],
                "score": point.score
            })
        
        logger.debug(f"Document results: {documents}")
        return documents
    except Exception as e:
        logger.error(f"Error during search_documents: {e}")
        return []

def add_document_sync(tenant:str, doc_id:str, title:str, chunks:list[str]):
    collection_name = f"tenants_{tenant}_documents"
    points = []
    for idx, chunk in enumerate(chunks):
        text_embedding = embed_text(chunk)
        point = models.PointStruct(
            id=uuid.uuid5(QDRANT_ID_NAMESPACE_UUID, f"{tenant}:{doc_id}:{idx}"),
            vector=text_embedding,
            payload={
                "chunk_id": f"{tenant}:{doc_id}:{idx}",
                "tenant": tenant,
                "doc_id": doc_id,
                "index": idx,
                "title": title,
                "text": chunk,
                "original_text": chunk,
                "audited_text": "",
                "audit_status": "pending",
                "audit_version": 0
            }
        )
        points.append(point)

    if not sync_qdrant_client.collection_exists(
            collection_name=collection_name
        ):
            sync_qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=2048,
                distance=models.Distance.COSINE,
            ),
        )
            
    sync_qdrant_client.upsert(
        collection_name=collection_name,
        points=points
    )

def update_point_sync(chunk_id:str, collection_name:str, payload:dict):
    point_id = uuid.uuid5(QDRANT_ID_NAMESPACE_UUID, chunk_id)
    new_vector = embed_text(payload['audited_text'])
    sync_qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=new_vector,
                    payload=None,
                )
            ],
            wait=True,
    )

    sync_qdrant_client.set_payload(
        collection_name=collection_name,
        points=[point_id],
        payload=payload
    )

def get_point_sync(chunk_id:str, collection_name:str) -> models.PointStruct | None:
    point_id = uuid.uuid5(QDRANT_ID_NAMESPACE_UUID, chunk_id)

    result = sync_qdrant_client.retrieve(
        collection_name=collection_name,
        ids=[point_id],
        with_payload=True
    )

    return result