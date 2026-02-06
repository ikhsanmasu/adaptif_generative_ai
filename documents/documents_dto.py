from pydantic import BaseModel, Field
from fastapi import UploadFile

class DocumentsRequest(BaseModel):
    tenant: str = Field(..., examples=["tenant_0"])
    document_id: str = Field(..., examples=["document_0"])
    file: UploadFile = Field(...)

class DocumentsResponse(BaseModel):
    result: str = Field(..., example= "File Indexing Success")


