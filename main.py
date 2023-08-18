from fastapi import HTTPException, Query, Header
from fastapi import FastAPI
import requests
from backend_control.models import ChatResponse, ChatRequestWithSession
from fastapi.responses import RedirectResponse
from backend_control.auth import generate_google_auth_url  # this is pseudocode; replace it with your actual function
import httpx
import os
from typing import Union
import time
from dataclasses import asdict

import BU_info_db.config as config
import BU_info_db.storage.weaviate_store as store
import BU_info_db.search.weaviate_search_engine as search_engine
from BU_info_db.search.search_agent.search_agent import SearchAgent, SearchAgentFeatures
import user_info_db.user_management as user_management
import langchain.chat_models
import backend_control.backend as backend


def init_config(local_env_file: Union[str, None]):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="INFO_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="USER_DATA_NAMESPACE"),
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


env_file = "backend_control/.env"
if not env_file.startswith("/"):
    current_directory = os.path.dirname(__file__)
    env_file = os.path.join(current_directory, env_file)
init_config(local_env_file=env_file)


CLIENT_ID = "google_client_id"  # Replace with your client_id ##### Ask me for it
CLIENT_SECRET = "google_client_secret"  # Replace with your client_secret ##### Ask me for it
REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"  # Adjust if necessary



# Initialize WeaviateStore and WeaviateSearchEngine
weaviate_store = store.WeaviateStore(
    instance_url=config.get("WEAVIATE_URL"),
    api_key=config.get("WEAVIATE_API_KEY"),
    openai_api_key=config.get("OPENAI_API_KEY"),
    namespace=config.get("INFO_DATA_NAMESPACE"),
    cohere_api_key=config.get("COHERE_API_KEY")
)

weaviate_user_management = user_management.UserDatabaseManager(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("USER_DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
)


weaviate_engine = search_engine.WeaviateSearchEngine(weaviate_store=weaviate_store)

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


app = FastAPI()


@app.get("/login")
def login():
    google_auth_url = generate_google_auth_url()  # Generate the Google OAuth URL
    return RedirectResponse(url=google_auth_url)


# @app.get("/auth/callback")
# def auth_callback(code: str = Query(...), state: str = Query(...), scope: str = Query(...), authuser: int = Query(0), prompt: str = Query(None)):
#     # Now you have the code
#     print(code) # This is just for debugging. You should not print sensitive info in production.
#     return {"code": code}
#

@app.get("/auth/callback")
async def auth_callback(code: str = Query(...)):
    # Define the data for the token request
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    # Send a POST request to get the access token
    async with httpx.AsyncClient() as client:
        response = await client.post("https://oauth2.googleapis.com/token", data=token_data)

    token_response = response.json()
    access_token = token_response.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    # Fetch user's info
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)

    user_info = response.json()

    # Return the user info for now (you should handle/store this information securely in production)
    return user_info


@app.get("/auth/callback")
async def handle_callback(code: str):
    # Take the code from the callback and exchange it for a token.
    token_endpoint = "https://oauth2.googleapis.com/token"
    client_id = "64549760389-cnm8nrvko2dea2r7mrusld5uimbkneqv.apps.googleusercontent.com"
    client_secret = "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"
    redirect_uri = "YOUR_REDIRECT_URI"

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }

    response = requests.post(token_endpoint, data=data)
    token_data = response.json()

    email = token_data["email"]
    first_name = token_data["given_name"]
    last_name = token_data["family_name"]

    if email.endswith("@bu.edu"):
        # Create a session for the user
        return [email, first_name, last_name]

    return "You must use a BU email to log in."


@app.api_route("/chat", methods=["POST"], response_model=ChatResponse)
async def send_question(data: ChatRequestWithSession):
    # Placeholder logic for the chatbot response
    response_and_id = ["Hello, this is your chatbot responding!", "randomID12345"]
    try:
        response_and_id = await backend.insert_message(search_agent=search_agent, user_management=weaviate_user_management, gmail="jjkatz2@bu.edu", input_text=data.question)

    except Exception as e:
        print(e)
        response_and_id = ["Oh no my program sucks please go to the insert_message funtion in the backend file!", "randomID12345"]

    response = response_and_id[0]
    responseID = response_and_id[1]
    return ChatResponse(response=response, responseID=responseID)


@app.get("/chat/{responseID}/result", response_model=ChatResponse)
async def get_response(responseID: str, sessionID: str = Header(...)):
    # Placeholder logic to return the chatbot's stored response
    # For the sake of this example, it's hardcoded.
    if responseID == "randomID12345":
        return ChatResponse(response="Hello, this is your chatbot responding!", responseID=responseID)
    else:
        raise HTTPException(status_code=404, detail="ResponseID not found or expired")


@app.post("/feedback", status_code=200)
async def provide_feedback(liked: bool, messageID: str):
    # Store or handle feedback (placeholder logic here)
    # Returns a 200 status code with no body on success
    backend.insert_feedback(user_management=weaviate_user_management, message_id=messageID, is_liked=liked)
