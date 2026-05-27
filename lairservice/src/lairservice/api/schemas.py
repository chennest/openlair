from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class AssistantInvokeRequest(BaseModel):
    message: str = Field(min_length=1)
    user_id: str = Field(default="local-user", min_length=1)
    session_id: str = Field(default="default", min_length=1)


class AssistantInvokeResponse(BaseModel):
    message: str
    session_id: str
    route: str


class NoteResponse(BaseModel):
    id: int
    content: str
