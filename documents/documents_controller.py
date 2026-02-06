from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from .documents_service import upload_file as upload_file_service

from .documents_dto import DocumentsRequest, DocumentsResponse

documents_router = APIRouter(prefix="/documents", tags=["documents"])

@documents_router.post(
        "/upload",
        response_model=DocumentsResponse,
        summary="Document Upload",
        description="Upload document"
)
async def upload_file( 
    tenant: str = Form("tenant_0"),
    document_id: str = Form("document_0"),
    file: UploadFile = File(...)
):
    try:
        result = await upload_file_service(tenant, document_id, file) 
        return {"result": result}
    except Exception as e:
        return HTTPException(status_code=500, detail=f"Error Found with detai;: {e}")