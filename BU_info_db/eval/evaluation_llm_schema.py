import enum

import pydantic

import BU_info_db.search.search_agent.openai_schema as openai_schema


class EvaluationGrade(enum.Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"


class EvaluationLlmSchema(openai_schema.OpenAISchema):
    """Class representing the evaluation of the Student's answer."""
    grade: EvaluationGrade = pydantic.Field(
        default=...,
        description="Grade of the of the BUChatbot's answer relative to true answer"
    )

    score: int = pydantic.Field(
        default=...,
        le=100,
        ge=0,
        description="Score of the of the BUChatbot's answer relative to true answer."
    )

    grade_explanation: str = pydantic.Field(
        default=...,
        description="Explanation of the grade."
    )

    score_explanation: str = pydantic.Field(
        default=...,
        description="Explanation of the score."
    )

    class Config:
        use_enum_values = True