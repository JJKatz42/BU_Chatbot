import datetime
import time
import markdown
from dataclasses import asdict

import src.libs.logging as logging
import src.libs.storage.user_data_classes as data_classes
from src.libs.search.search_agent.search_agent import SearchAgent
from src.libs.storage.user_management import UserDatabaseManager
from src.libs.storage.weaviate_store import WeaviateStore

logger = logging.getLogger(__name__)


async def search_agent_job(
        agent: SearchAgent,
        query: str,
        current_profile_info: dict,
        profile_info_vector: list[float]
) -> dict:
    """
    Runs a search agent job.

    Parameters:
        agent (SearchAgent): The search agent to use for the job.
        query (str): The search query to run.
        current_profile_info (dict): The current profile information for the user.
        profile_info_vector (list[float]): The profile information vector for the user.

    Returns:
        dict: A dictionary containing the search result and metadata. Includes:
            answer (str): The generated answer text.
            sources (list): List of source objects used to generate answer.
            search_job_duration (float): Time taken to run the search job.
    """
    logger.info(f"Running job: {query}")
    search_job_start_time = time.time()

    result = await agent.run(query, current_profile_info, profile_info_vector)

    result_dict = asdict(result)
    result_dict['search_job_duration'] = round((time.time() - search_job_start_time), 2)
    logger.info(f"Running job: {query} finished")

    return result_dict


async def get_answer(
        search_agent: SearchAgent,
        input_text: str,
        current_profile_info: dict,
        profile_info_vector: list[float]
) -> str:
    """
    Gets an answer from a search agent.

    Parameters:
        search_agent (SearchAgent): The search agent to use.
        input_text (str): The input text to get an answer for.
        current_profile_info (dict): The current profile information for the user.
        profile_info_vector (list[float]): The profile information vector for the user.

    Returns:
        str: The generated answer text.
    """
    try:
        agent_result = await search_agent_job(search_agent, input_text, current_profile_info, profile_info_vector)

        answer = markdown.markdown(agent_result['answer'])
        if "related to your query." in answer or "couldn't find any relevant" in answer or "does not have any specific meaning or relevance" in answer or "I apologize" in answer or "I'm sorry" in answer or "can't assist with your request" in answer:
            # response = f"<p>{answer[34:]}</p>"  # This is a really quick and not good way of checking to see
            # if the searchengine could not find a result
            response = f"<p>{answer}</p>"

        else:
            sorted_lst = sorted(agent_result['sources'], key=lambda x: x['score'], reverse=True)

            # Extract the first 5 URLs
            top_10_urls = [item['url'] for item in sorted_lst[:10]]

            url_str = ""

            for url in top_10_urls:
                if url in url_str:
                    continue

                url_str += f'<li><a class="link" href="{url}" target="_blank">{url}</a></li>'

            response = f"<p>{answer}</p> <p><br>Below are the related sources:</p> <ol>{url_str}</ol>"
            # Used HTML break line tag here

        return response

    except Exception as e:
        logger.error(f"Error getting answer from agent: {e}")

        return ("<p>Sorry, there was an error finding your answer please wait a few moments "
                "before trying again.</p>")


async def insert_message(
        search_agent: SearchAgent,
        user_management: UserDatabaseManager,
        gmail: str,
        input_text: str,
        cap: int
):
    """
    Inserts a message into the database.

    Parameters:
        search_agent (SearchAgent): The search agent to use.
        user_management (UserDatabaseManager): The user management object to use.
        gmail (str): The gmail of the user to insert the message for.
        input_text (str): The input text to insert.
        cap (int): The maximum number of messages a user can send within 24 hours.

    Returns:
        list: A list containing the response and the bot message uuid.
    """
    # Insert the message into the database
    is_good_query = "True"

    if "False" in is_good_query:
        response = "Sorry, this is a bad query. Please try again."
        return [response, "None"]

    if user_management.user_exists(gmail):
        if user_management.num_user_messages_24hrs(gmail=gmail) < cap:

            current_profile_info = user_management.get_profile_info_for_user(gmail=gmail)

            profile_info_vector = user_management.get_profile_info_vector_for_user(gmail=gmail)

            response = await get_answer(search_agent, input_text, current_profile_info, profile_info_vector)
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
            return [
                "Sorry, you have reached the maximum number of queries in 24 hours. Please try again tomorrow.",
                "None"
            ]

    else:
        return ["Sorry, you are not a registered user.", "None"]


def user_exists(user_management: UserDatabaseManager, gmail: str) -> bool:
    """
    Checks if a user exists in the database.

    Parameters:
        user_management (UserDatabaseManager): The user management object to use.
        gmail (str): The gmail of the user to check.

    Returns:
        bool: True if the user exists, False otherwise.
    """
    return user_management.user_exists(gmail)


def insert_user(user_management: UserDatabaseManager, gmail: str) -> bool:
    """
    Inserts a user into the database.

    Parameters:
        user_management (UserDatabaseManager): The user management object to use.
        gmail (str): The gmail of the user to insert.

    Returns:
        bool: True if the user was inserted, False otherwise.
    """
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


def insert_feedback(user_management: UserDatabaseManager, message_id: str, is_liked: bool):
    """
    Inserts feedback into the database.

    Parameters:
        user_management (UserDatabaseManager): The user management object to use.
        message_id (str): The message id to insert feedback for.
        is_liked (bool): True if the message was liked, False otherwise.

    Returns:
        str: A string indicating the result of the insert.
    """
    logger.info("Inserting like into user")
    user_management.insert_liked(
        liked=is_liked,
        bot_message_id=message_id
    )
    return "Finished inserting like"


def insert_profile_info(
        user_management: UserDatabaseManager,
        weaviate_store: WeaviateStore,
        gmail: str,
        profile_info_dict: dict
):
    """
    Inserts profile information into the database.

    Parameters:
        user_management (UserDatabaseManager): The user management object to use.
        weaviate_store (WeaviateStore): The weaviate store object to use.
        gmail (str): The gmail of the user to insert profile information for.
        profile_info_dict (dict): The profile information to insert.

    Returns:
        str: A string indicating the result of the insert.
    """
    # Get current profile info for user
    logger.info("Deleting current profile info from user")
    user_management.delete_profile_info_for_user(gmail=gmail)
    # Insert profile info into user
    profile_info_lst = []

    for key, value in profile_info_dict.items():
        profile_info = data_classes.ProfileInformation(
            key=key,
            value=value
        )

        profile_info_lst.append(profile_info)

    user_management.insert_profile_info(
        gmail=gmail,
        profile_info_lst=profile_info_lst,
    )
    logger.info("Finished inserting profile info")
    # Create profile information vector
    logger.info("Creating profile info vector")
    profile_info_vect = weaviate_store.create_embedding(str(profile_info_dict))[0]
    # insert profile information vector into user
    logger.info("Inserting profile info vector into user")
    user_management.update_profile_info_vector(
        gmail=gmail,
        profile_info_vect=profile_info_vect
    )
