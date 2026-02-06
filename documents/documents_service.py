from vector_db.vector_db_service import add_document
from fastapi import UploadFile, File
import pdfplumber
from pathlib import Path
from agent import background_audit_chunks

def chunk_text(text:str, chunk_size:int = 800, overlap_size:int = 1600) -> list:
    """
    Chunking based on number of characters
    """
    chunks = []
    current_chunk = ""
    for char in text:
        if len(current_chunk) < overlap_size:
            if len(current_chunk) >= chunk_size and (char == "." or char == "\n"):
                chunks.append(current_chunk)
                current_chunk = ""
            else:
                current_chunk += char
        else:
            chunks.append(current_chunk)
            current_chunk = ""
 
    if current_chunk:
        chunks.append(current_chunk)

    return chunks   

async def upload_file(tenant:str, document_id:str, uploaded_file:UploadFile = File(...)) -> str:
    """
    Indexing chunk to vector db and call background indexing agent tasks
    """
    file_location = Path(f"temp/{uploaded_file.filename}")
    file_location.parent.mkdir(parents=True, exist_ok=True)
    try:
        with file_location.open("wb") as out:
            while True:
                chunk = await uploaded_file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    finally:
        await uploaded_file.close()

    full_text = ""
    with pdfplumber.open(file_location) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    chunks = chunk_text(full_text)

    await add_document(tenant=tenant, doc_id=document_id, title=uploaded_file.filename, chunks=chunks)
    
    background_audit_chunks(tenant, document_id, len(chunks))

    return "File Indexing Success"
