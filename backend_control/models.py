from pydantic import BaseModel

class ChatRequestWithSession(BaseModel):
    sessionID: str
    gmail: str
    question: str

class ChatResponse(BaseModel):
    response: str
    responseID: str

class FeedbackRequest(BaseModel):
    responseID: str
    liked: bool

class ErrorResponse(BaseModel):
    error: str
    code: int

class IncompleteResponse(BaseModel):
    message: str
