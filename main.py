from fastapi import FastAPI
from chat import chat_router
from documents import documents_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(asctime)s - %(name)s - %(message)s"
)

app = FastAPI(
    title="RAG Service",
    description="Simple RAG Service with adaptif chunking",
    version="1.0.0",
    contact={"name": "Ikhsan Maulana", "email": "ikhsanmsumarno@gmail.com"},
    license_info={"name": "MIT"})

app.include_router(documents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
