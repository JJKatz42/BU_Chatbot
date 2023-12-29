import json

import langchain.chat_models
import llama_index.llms.openai_utils as openai_utils
import pydantic
import tenacity

import src.libs.search.search_agent.exceptions as exceptions
import src.libs.logging as logging

logger = logging.getLogger(__name__)


llm_schema_gen_retry_config = tenacity.retry(
    wait=tenacity.wait_exponential(min=1, max=60),
    stop=tenacity.stop_any(tenacity.stop_after_delay(60), tenacity.stop_after_attempt(3)),
    retry=tenacity.retry_if_exception_type((pydantic.ValidationError, json.JSONDecodeError)),
)


def get_llm_to_use(
    prompt_msgs: list[langchain.prompts.base.BaseMessage],
    llm: langchain.chat_models.ChatOpenAI,
    fallback_llm: langchain.chat_models.ChatOpenAI,
    max_answer_tokens: int,
) -> langchain.chat_models.ChatOpenAI:

    num_tokens_in_prompt = llm.get_num_tokens_from_messages(prompt_msgs)
    llm_max_tokens = openai_utils.openai_modelname_to_contextsize(llm.model_name)
    fallback_llm_max_tokens = openai_utils.openai_modelname_to_contextsize(fallback_llm.model_name)

    llm_to_use = llm
    if num_tokens_in_prompt > llm_max_tokens - max_answer_tokens:
        if num_tokens_in_prompt > fallback_llm_max_tokens - max_answer_tokens:
            raise exceptions.SearchAgentException(
                f"Prompt has {num_tokens_in_prompt} tokens which is larger "
                f"than maximum supported context size ({fallback_llm_max_tokens}) assuming {max_answer_tokens} "
                f"are reserved for the answer."
            )

        logger.warning(
            f"Prompt has {num_tokens_in_prompt} tokens which is larger than "
            f"than {llm.model_name} context size assuming {max_answer_tokens} are reserved for the answer, "
            f"switching to {fallback_llm.model_name}."
        )
        llm_to_use = fallback_llm

    return llm_to_use