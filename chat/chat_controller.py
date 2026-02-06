from fastapi import APIRouter, HTTPException
from .chat_service import chat_completion as chat_completion_service
from .chat_dto import ChatRequest, ChatResponse
import logging

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/chat", tags=["chat"])

@chat_router.post(
        "/",
        response_model=ChatResponse,
        summary="Chat Completition",
        description="Sending question to RAG Service"
)
async def chat_completion(payload: ChatRequest):
    logger.info(f"POST /api/v1/chat Request payload:{dict(payload)}")
    try:
        responses = await chat_completion_service(message=payload.query, tenant=payload.tenant, user_id=payload.user_id)
        logger.info(f"POST /api/v1/chat Response payload:{dict(responses)}")
        return responses
    except Exception as e:
        logger.error(f"POST /api/v1/chat ERROR while processing {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")