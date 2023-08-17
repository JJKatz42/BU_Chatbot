import argparse
import asyncio
import datetime
import os
import time
import langchain.chat_models
from dataclasses import asdict


import BU_info_db.storage.weaviate_store as store
import BU_info_db.search.weaviate_search_engine as search_engine
from BU_info_db.search.search_agent import SearchAgent, SearchAgentFeatures
from BU_info_db.config import config
import user_info_db.user_management as user_management
import user_info_db.user_data_classes as data_classes


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

    insert_user_parser = subparsers.add_parser(
        "insert-user",
        help="Insert user into database",
        argument_default=argparse.SUPPRESS)
    insert_user_parser.add_argument(
        "--gmail",
        help="By default gmail is jjkatz@bu.edu",
        default="jjkatz2@bu.edu",
        action="store_true"
    )
    insert_user_parser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default=".env"
    )
    insert_user_parser.add_argument(
        "--full-refresh",
        help="By default indexing is incremental. Set this flag to build indexes from scratch. "
             "This includes re-creating Weaviate schema by deleting all existing objects.",
        default=False,
        action="store_true"
    )
    insert_message_parser = subparsers.add_parser(
        "insert-message",
        help="Run a search query and get back search result"
    )
    insert_message_parser.add_argument("ask", nargs="?", default="describe sm 132")
    insert_message_parser.add_argument(
        "--gmail",
        help="By default gmail is jjkatz@bu.edu",
        default="jjkatz2@bu.edu",
        action="store_true"
    )
    insert_message_parser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default=".env"
    )
    insert_like_parser = subparsers.add_parser(
        "insert-like",
        help="insert a like or dislike"
    )
    insert_like_parser.add_argument("liked", nargs="?", default="True")
    insert_like_parser.add_argument(
        "--message_id",
        help="By default message_id is 1be74784-0173-4dfd-a655-ef9338ff1a93",
        default="1c5e2e99-62a9-423c-96a1-b14c88ab2c70",
        action="store_true"
    )
    insert_like_parser.add_argument("--env-file", help="Local .env file containing config values", default=".env")
    clear_conversation_parser = subparsers.add_parser(
        "clear-conversation",
        help="clear a conversation for a given user")
    clear_conversation_parser.add_argument(
        "--gmail",
        help="By default gmail is jjkatz@bu.edu",
        default="jjkatz2@bu.edu",
        action="store_true"
    )
    clear_conversation_parser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default=".env")

    insert_profile_info_pasrser = subparsers.add_parser(
        "insert-profile-info",
        help="inserts dict of profile info into user")

    insert_profile_info_pasrser.add_argument(
        "profile_info",
        nargs="?",
        default="{'name': 'John', 'age': '25'}"
    )
    insert_profile_info_pasrser.add_argument(
        "--gmail",
        help="By default gmail is jjkatz@bu.edu",
        default="jjkatz2@bu.edu",
        action="store_true"
    )
    insert_profile_info_pasrser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default=".env"
    )

    script_args = parser.parse_args()

    # Initialize config
    env_file = script_args.env_file
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)

    # Initialize weaviate user management
    weaviate_user_management = user_management.UserDatabaseManager(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("USER_DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )

    # Initialize weaviate store
    weaviate_store_info = store.WeaviateStore(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("INFO_DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )

    # Route to sub command specific logic either build indexes for search or run a search
    if script_args.command == "insert-user":
        # Create weaviate schema
        if script_args.full_refresh:
            weaviate_user_management.create_schema(delete_if_exists=True)

        if weaviate_user_management.user_exists(script_args.gmail):
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

            # Insert webpages to weaviate
            print("Inserting user into weaviate")
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

        message_list = weaviate_user_management.get_messages_for_user(gmail=script_args.gmail)
        print(message_list)

        ask_str = script_args.ask

        # Run the SearchAgent
        print("Running search agent")
        agent_result = await search_agent_job(search_agent, ask_str)
        # sort the sources by score
        sorted_lst = sorted(agent_result['sources'], key=lambda x: x['score'], reverse=True)
        # Extract the first 5 URLs
        top_5_urls = [item['url'] for item in sorted_lst[:10]]
        # Create a string of the URLs
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

    elif script_args.command == "insert-like":
        # Insert like into user
        print("Inserting like into user")
        weaviate_user_management.insert_liked(
            liked=script_args.liked,
            bot_message_id=script_args.message_id
        )
        print("Finished inserting like")

    elif script_args.command == "clear-conversation":
        # Clear conversation for user
        print("Clearing conversation for user")
        weaviate_user_management.clear_conversation(
            gmail=script_args.gmail
        )
        print("Finished clearing conversation")

    elif script_args.command == "insert-profile-info":
        # Get current profile info for user
        current_profile_info_dict = weaviate_user_management.get_profile_info_for_user(gmail=script_args.gmail)
        print(current_profile_info_dict)

        # Insert profile info into user
        print("Inserting profile info into user")

        profile_info_dict = eval(script_args.profile_info)

        profile_info_lst = []

        for key, value in profile_info_dict.items():
            profile_info = data_classes.ProfileInformation(
                key=key,
                value=value
            )

            profile_info_lst.append(profile_info)

        weaviate_user_management.insert_profile_info(
            gmail=script_args.gmail,
            profile_info_lst=profile_info_lst,
        )
        print("Finished inserting profile info")

if __name__ == '__main__':
    asyncio.run(main())