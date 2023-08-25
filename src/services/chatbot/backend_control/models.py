from pydantic import BaseModel, Field


class JWTHeader(BaseModel):
    jwt_token: str = Field(..., alias="Authorization")


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    response: str
    responseID: str


class FeedbackRequest(BaseModel):
    jwt_token: str = Field(..., alias="Authorization")
    responseID: str
    is_liked: bool


class ErrorResponse(BaseModel):
    error: str
    code: int


class IncompleteResponse(BaseModel):
    message: str
