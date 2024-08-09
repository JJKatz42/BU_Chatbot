from pydantic import BaseModel, Field

"""
This module defines Pydantic models for a chatbot API.

JWTHeader:
    - jwt_token (str): JWT token for authentication. Required. Alias for 'Authorization'.

ChatRequest:
    - question (str): The question text to get a response for.

ChatResponse: 
    - response (str): The generated response text.
    - responseID (str): Unique ID for the response.

FeedbackRequest:
    - responseID (str): ID of the response to provide feedback for.
    - is_liked (bool): Feedback indicating if the response was liked.

ErrorResponse:
    - error (str): Error message text.
    - code (int): Numeric error code.

IncompleteResponse:
    - message (str): Message indicating an incomplete response.

ProfileInformationRequest
    - profile_info_dict (dict): Dictionary of personal information to use for search.
"""


class JWTHeader(BaseModel):
    jwt_token: str = Field(..., alias="Authorization")


class ChatRequest(BaseModel):
    question: str
    context: str


class ChatResponse(BaseModel):
    response: str
    responseID: str


class IsAuthorizedResponse(BaseModel):
    is_authorized: bool


class FeedbackRequest(BaseModel):
    responseID: str
    is_liked: bool


class ErrorResponse(BaseModel):
    error: str
    code: int


class IncompleteResponse(BaseModel):
    message: str


class ProfileInformationRequest(BaseModel):
    profile_info_dict: dict


class CurrentDictResponse(BaseModel):
    profile_info_dict: dict
