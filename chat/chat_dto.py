from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., examples=["Halo are you there?"])
    tenant: str = Field(..., examples=["tenant_0"])
    user_id: str = Field(..., examples=["user_0"])

class ChatResponse(BaseModel):
    question: str = Field(..., example="Halo are you there?")
    answer: str = Field(..., examples=["Hi im here, is there anything i can help?"])
    ritrieved_documents: list = Field(...)
    prompt_used: list = Field(...)
    token_usage_estimation: int = Field(...)


