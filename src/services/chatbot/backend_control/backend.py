import time
from dataclasses import asdict
import datetime

from src.libs.search.search_agent.search_agent import SearchAgent
import src.libs.storage.user_data_classes as data_classes
import src.libs.storage.user_management as user_management
import src.libs.logging as logging


logger = logging.getLogger(__name__)


async def search_agent_job(agent: SearchAgent, query: str) -> dict:
    logger.info(f"Running job: {query}")
    search_job_start_time = time.time()
    result = await agent.run(query)
    result_dict = asdict(result)
    result_dict['search_job_duration'] = round((time.time() - search_job_start_time), 2)
    logger.info(f"Running job: {query} finished")
    return result_dict


async def get_answer(search_agent: SearchAgent, input_text: str) -> str:
    # Get the answer from the search agent
    try:
        agent_result = await search_agent_job(search_agent, input_text)

        sorted_lst = sorted(agent_result['sources'], key=lambda x: x['score'], reverse=True)

        # Extract the first 5 URLs

        top_5_urls = [item['url'] for item in sorted_lst[:10]]

        url_str = ""
        num = 0
        for url in top_5_urls:
            if url in url_str:
                continue

            num += 1
            url_str += "<br>"  # Use HTML break line tag here
            url_str += f"{num}. {url} "

        response = f"{agent_result['answer']} <br><br> Sources: {url_str}"  # Use HTML break line tag here

        # logger.info("response: ", response)

        # response = "It worked"

        return response
    except:
        return "Sorry, there was an error finding your answer please check the get_answer function in the testerbackend file."


async def insert_message(search_agent: SearchAgent, user_management: user_management.UserDatabaseManager, gmail: str, input_text: str):
    # Insert the message into the database
    is_good_query = "True"
    if "False" in is_good_query:
        response = "Sorry, this is a bad query. Please try again."
        return [response, "None"]

    if user_management.user_exists(gmail):
        response = await get_answer(search_agent, input_text)

        # response = "This is a test response 2"
        # Create messages
        logger.info("Creating user message")
        user_message = data_classes.UserMessage(
            query_str=input_text,
            is_good_query=None,
            created_time=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        logger.info("Creating bot message")
        bot_message = data_classes.BotMessage(
            response_str=response,
            is_liked=None,
            created_time=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        # Insert message into user
        logger.info("Inserting message into user")
        bot_message_uuid = user_management.insert_message(
            user_message=user_message,
            bot_message=bot_message,
            gmail=gmail
        )
        logger.info("Finished inserting message")

        return [response, bot_message_uuid]

    else:
        return ["Sorry, you are not a registered user. Please register at https://busearch.com", "None"]


def user_exists(user_management: user_management.UserDatabaseManager, gmail: str) -> bool:
    return user_management.user_exists(gmail)


def insert_user(user_management: user_management.UserDatabaseManager, gmail: str) -> bool:
    user = data_classes.User(
        gmail=gmail,
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
    logger.info("Inserting user into weaviate")
    succeeded = user_management.create_user(user=user)

    logger.info("Finished inserting user")

    return succeeded


def insert_feedback(user_management: user_management.UserDatabaseManager, message_id: str, is_liked: bool):
    logger.info("Inserting like into user")
    user_management.insert_liked(
        liked=is_liked,
        bot_message_id=message_id
    )
    return "Finished inserting like"
