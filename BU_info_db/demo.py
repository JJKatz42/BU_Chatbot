import asyncio
import os

import langchain.chat_models

# import libs.agents as agents
# import libs.config as config
# import libs.search as search
# import libs.storage as storage
import config
from weaviate_store import WeaviateStore
from search_agent import SearchAgentFeatures, SearchAgent
from weaviate_search_engine import WeaviateSearchEngine


def init_config(local_env_file: str | None):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="WEAVIATE_URL"),
            config.ConfigVarMetadata(var_name="WEAVIATE_API_KEY"),
            config.ConfigVarMetadata(var_name="OPENAI_API_KEY"),
        ],
        local_env_file=local_env_file
    )



async def main():
    # init_config(".env")
    env_file = ".env"
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)

    # Initialize weaviate store
    weaviate_store = WeaviateStore(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )
    # Initialize a search engine
    weaviate_search_engine = WeaviateSearchEngine(weaviate_store=weaviate_store)
    # Initialize a LLM
    reasoning_llm = langchain.chat_models.ChatOpenAI(
        model_name="gpt-3.5-turbo-0613",
        temperature=0.0,
        openai_api_key=config.get("OPENAI_API_KEY")
    )
    # Initialize the agent with the search engine and reasoning llm
    agent = SearchAgent(
        weaviate_search_engine=weaviate_search_engine,
        reasoning_llm=reasoning_llm,
        features=[
            # SearchAgentFeatures.CROSS_ENCODER_RE_RANKING,
            # SearchAgentFeatures.QUERY_PLANNING,
            # SearchAgentFeatures.AUTO_SEARCH_PARAMETER_GEN
        ],
    )

    # Run the agent
    query = "what is the description for sm 132"
    result = await agent.run(query=query)
    # print(result)


if __name__ == '__main__':
    asyncio.run(main())