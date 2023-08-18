import dataclasses

import langchain.callbacks
import langchain.chat_models
import langchain.schema

import src.libs.eval.evaluation_llm_schema as evaluation_llm_schema


class EvaluationAgent:
    """Agent that evaluates and grades Bots answers.

    This agent evaluates answers to queries

    Args:
        evaluation_llm: LLM object used for evaluation tasks
    """
    def __init__(
        self,
        evaluation_llm: langchain.chat_models.ChatOpenAI,
    ):
        self._evaluation_llm = evaluation_llm

    async def run(self,
                  query: str,
                  expected_rsp: str,
                  bot_rsp: str,
                  ) -> "EvaluationAgentResult":
        """Evaluate answer to a query.

        Args:
            query: The query posed as a question
            expected_rsp: Expected response
            bot_rsp: bot response

        Returns:
            An EvaluationAgentResult object which contains the grade, score, grade explantion, score explanation, various debug details
        """
        with langchain.callbacks.get_openai_callback() as cb:

            llm_prompt_messages = [
                langchain.schema.SystemMessage(
                    content="""
You are a teacher grading a quiz by a student named Bot.
You are given a question, Bot's answer, and the true answer,
and are asked to grade Bot's answer as either CORRECT or INCORRECT.
Also you need to score each question 0 to 100 to represent correctness.
The grade may be only one of "CORRECT" or "INCORRECT" and nothing else.
Any score you arrive at as 60 or higher should yield a CORRECT grade, and INCORRECT otherwise. 
Please provide explanation of your logic for grade and score.

Example Input Format:
QUESTION: question here
Bot ANSWER: Bot's answer here
TRUE ANSWER: true answer here

Grade Bot's answers based ONLY on their factual accuracy.
Ignore differences in punctuation and phrasing between Bot's answer and true answer.
It is OK if Bot's answer contains more information than the true answer,
as long as it does not contain any conflicting statements. Begin! 
                    """
                ),
                langchain.schema.HumanMessage(
                    content=f"QUESTION: {query}\nBOT ANSWER: {bot_rsp}\nTRUE ANSWER: {expected_rsp}"),
            ]

            llm_response_message = await self._evaluation_llm.apredict_messages(
                messages=llm_prompt_messages,
                functions=[evaluation_llm_schema.EvaluationLlmSchema.openai_schema],
                function_call={
                    "name": evaluation_llm_schema.EvaluationLlmSchema.openai_schema["name"]
                },
            )

            # will create a class defined via pydantic schema in EvaluationLlmSchema
            evaluation = evaluation_llm_schema.EvaluationLlmSchema.from_response(
                llm_response_message
            )

        return EvaluationAgentResult(
            query=query,
            expected_rsp=expected_rsp,
            bot_rsp=bot_rsp,
            grade=evaluation.grade,
            score=evaluation.score,
            grade_explanation=evaluation.grade_explanation,
            score_explanation=evaluation.score_explanation,
            total_tokens_used=cb.total_tokens,
            total_tokens_cost=cb.total_cost
        )




@dataclasses.dataclass
class EvaluationAgentResult:
    """Container for result of running an Agent on a query."""
    query: str            # input
    expected_rsp: str     # input
    bot_rsp: str        # input
    grade: evaluation_llm_schema.EvaluationGrade
    score: int
    score_explanation: str
    grade_explanation: str
    total_tokens_used: int
    total_tokens_cost: int