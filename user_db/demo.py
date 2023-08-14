import argparse
import asyncio
import datetime
import os
import pprint
import time
import uuid
from dataclasses import asdict


import BU_info_db.storage.weaviate_store as store
import BU_info_db.search.weaviate_search_engine as search_engine
import BU_info_db.storage.data_connnector.webpage_splitter as webpage_splitter
import BU_info_db.storage.data_connnector.directory_reader as directory_reader
import user_db.user_management as user_management
import user_db.user_data_classes as data_classes
from BU_info_db.search.search_agent import SearchAgent, SearchAgentFeatures
import langchain.chat_models


from BU_info_db.config import config


def init_config(local_env_file: str | None):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="USER_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="INFO_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="WEAVIATE_URL"),
            config.ConfigVarMetadata(var_name="WEAVIATE_API_KEY"),
            config.ConfigVarMetadata(var_name="OPENAI_API_KEY"),
            config.ConfigVarMetadata(var_name="COHERE_API_KEY"),
        ],
        local_env_file=local_env_file
    )

async def search_agent_job(agent: SearchAgent, query: str) -> dict:
    print(f"Running job: {query}")
    search_job_start_time = time.time()
    result = await agent.run(query)
    result_dict = asdict(result)
    result_dict['search_job_duration'] = round((time.time() - search_job_start_time), 2)
    print(f"Running job: {query} finished")
    return result_dict


async def main():
    parser = argparse.ArgumentParser(
        prog="Interact with the user database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

    insert_user_parser = subparsers.add_parser("insert-user", help="Insert user into database", argument_default=argparse.SUPPRESS)
    insert_user_parser.add_argument(
        "--gmail",
        help="By default gmail is jjkatz@bu.edu",
        default="jjkatz@bu.edu",
        action="store_true"
    )
    insert_user_parser.add_argument("--env-file", help="Local .env file containing config values", default=".env")
    insert_user_parser.add_argument(
        "--full-refresh",
        help="By default indexing is incremental. Set this flag to build indexes from scratch. "
             "This includes re-creating Weaviate schema by deleting all existing objects.",
        default=False,
        action="store_true"
    )
    insert_message_parser = subparsers.add_parser("insert-message", help="Run a search query and get back search result")
    insert_message_parser.add_argument("ask", nargs="?", default="describe sm 132")
    insert_message_parser.add_argument(
        "--gmail",
        help="By default gmail is jjkatz@bu.edu",
        default="jjkatz@bu.edu",
        action="store_true"
    )
    insert_message_parser.add_argument("--env-file", help="Local .env file containing config values", default=".env")


    script_args = parser.parse_args()

    # Initialize config
    env_file = script_args.env_file
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)

    # Initialize weaviate store

    weaviate_user_management = user_management.UserDatabaseManager(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("USER_DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )

    weaviate_store_info = store.WeaviateStore(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("INFO_DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )


    # Route to sub command specific logic either insert user or insert message
    if script_args.command == "insert-user":
        # Create weaviate schema
        if script_args.full_refresh:
            weaviate_user_management.create_schema(delete_if_exists=True)

        if weaviate_user_management.is_duplicate_user(script_args.gmail):
            print("User already exists")

        else:
            # Create user
            user = data_classes.User(
                gmail=script_args.gmail,
                created_time=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                profile_information=[],
                conversations=[]
            )

            user.conversations = [
                data_classes.Conversation(
                    messages=[],
                    created_time=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                )
            ]


            print("Inserting user into weaviate")
            # Insert webpages to weaviate
            weaviate_user_management.create_user(user=user)

            print("Finished inserting user")

    elif script_args.command == "insert-message":

        weaviate_engine = search_engine.WeaviateSearchEngine(weaviate_store=weaviate_store_info)

        # Initialize a reasoning LLM
        reasoning_llm = langchain.chat_models.ChatOpenAI(
            model_name="gpt-3.5-turbo-0613",
            temperature=0.0,
            openai_api_key=config.get("OPENAI_API_KEY")
        )

        features = [SearchAgentFeatures.CROSS_ENCODER_RE_RANKING, SearchAgentFeatures.QUERY_PLANNING]

        search_agent = SearchAgent(
            weaviate_search_engine=weaviate_engine,
            reasoning_llm=reasoning_llm,
            features=features
        )

        weaviate_user_management.get_messages_from_user_gmail(gmail=script_args.gmail)

        ask_str = script_args.ask

        # Run the SearchAgent
        print("Running search agent")
        agent_result = await search_agent_job(search_agent, ask_str)
        # sort the sources by score
        sorted_lst = sorted(agent_result['sources'], key=lambda x: x['score'], reverse=True)
        # Extract the first 5 URLs
        top_5_urls = [item['url'] for item in sorted_lst[:10]]
        # Add sources
        url_str = ""
        num = 0
        for url in top_5_urls:
            if url in url_str:
                continue

            num += 1
            url_str += "\n"  # Use HTML break line tag here
            url_str += f"{num}. {url} "

        response = f"{agent_result['answer']} \n\n Sources: {url_str}"  # Use HTML break line tag here

        # response = "This is a test response 2"
        # Create messages
        print("Creating user message")
        user_message = data_classes.UserMessage(
            query_str=ask_str,
            is_bad_query=None,
            created_time=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        print("Creating bot message")
        bot_message = data_classes.BotMessage(
            response_str=response,
            is_liked=None,
            created_time=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        # Insert message into user
        print("Inserting message into user")
        weaviate_user_management.insert_message(
            user_message=user_message,
            bot_message=bot_message,
            gmail=script_args.gmail
        )
        print("Finished inserting message")


if __name__ == '__main__':
    asyncio.run(main())