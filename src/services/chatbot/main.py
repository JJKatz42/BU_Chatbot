import os
import time
from dataclasses import asdict
from typing import Union

import httpx
import jwt
import uuid
import langchain.chat_models
from fastapi import HTTPException, Query, FastAPI, Response, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from fastapi.responses import JSONResponse


import src.libs.config as config
import src.libs.search.weaviate_search_engine as search_engine
import src.libs.storage.user_management as user_management
import src.libs.storage.weaviate_store as store
import src.services.chatbot.backend_control.backend as backend
from src.libs.search.search_agent.search_agent import SearchAgent, SearchAgentFeatures
from src.services.chatbot.backend_control.auth import generate_google_auth_url
from src.services.chatbot.backend_control.models import ChatResponse, ChatRequest, JWTHeader, FeedbackRequest
import src.libs.logging as logging


logger = logging.getLogger(__name__)


def init_config(local_env_file: Union[str, None]):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="INFO_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="USER_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="WEAVIATE_URL"),
            config.ConfigVarMetadata(var_name="WEAVIATE_API_KEY"),
            config.ConfigVarMetadata(var_name="OPENAI_API_KEY"),
            config.ConfigVarMetadata(var_name="COHERE_API_KEY"),
            config.ConfigVarMetadata(var_name="CLIENT_ID"),
            config.ConfigVarMetadata(var_name="CLIENT_SECRET"),
            config.ConfigVarMetadata(var_name="REDIRECT_URI"),
            config.ConfigVarMetadata(var_name="ENCRYPTION_ALGORITHM"),
            config.ConfigVarMetadata(var_name="SECRET_KEY"),
            config.ConfigVarMetadata(var_name="IS_LOCAL_ENV"),
        ],
        local_env_file=local_env_file
    )


def get_current_email(jwt_token: str) -> str:
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["email"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Signature has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_jwt_token(request: Request) -> str:
    """
    Extract the JWT token from the HttpOnly cookie.
    """
    jwt_token = request.cookies.get("Authorization")
    if not jwt_token:
        logger.warning("No JWT token found in the request")
        raise HTTPException(status_code=401, detail="Not authenticated")

    else:
        logger.info(f"JWT token: {jwt_token}")
        return jwt_token


async def search_agent_job(agent: SearchAgent, query: str) -> dict:
    logger.info(f"Running job: {query}")
    search_job_start_time = time.time()
    result = await agent.run(query)
    result_dict = asdict(result)
    result_dict['search_job_duration'] = round((time.time() - search_job_start_time), 2)
    logger.info(f"Running job: {query} finished")
    return result_dict


env_file = ".env"
if not env_file.startswith("/"):
    current_directory = os.path.dirname(__file__)
    env_file = os.path.join(current_directory, env_file)
init_config(local_env_file=env_file)


SECRET_KEY = config.get("SECRET_KEY")
ALGORITHM = config.get("ENCRYPTION_ALGORITHM")
security = HTTPBearer()

CLIENT_ID = config.get("CLIENT_ID")
CLIENT_SECRET = config.get("CLIENT_SECRET")
REDIRECT_URI = config.get("REDIRECT_URI")

IS_LOCAL_ENV = config.get("IS_LOCAL_ENV")


if str(IS_LOCAL_ENV) == "True":
    BASE_URL = "http://localhost:8080"
    DOMAIN = "localhost:8080"
else:
    BASE_URL = "https://app.busearch.com"
    DOMAIN = "app.busearch.com"


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/login")
def login():
    # Generate the Google OAuth URL
    google_auth_url = generate_google_auth_url(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI)
    return RedirectResponse(url=google_auth_url)


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

    email = user_info["email"]
    # first_name = user_info["given_name"]
    # last_name = user_info["family_name"]

    if email.endswith("@bu.edu") or email == "bradleyjocelyn3@gmail.com" or email == "georgeflint@berkeley.edu":
        # Create a session for the user
        user_inserted_successfully = backend.insert_user(user_management=weaviate_user_management, gmail=email)
        if user_inserted_successfully:

            jwt_token = jwt.encode({"email": email}, SECRET_KEY, algorithm=ALGORITHM)

            chat_url = "http://localhost:8005"

            # response = JSONResponse(content={"message": "Cookie has been set!"})
            # response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=True, samesite="none", max_age=3600)
            #
            # return response
            response = RedirectResponse(url=chat_url)
            response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=False, samesite="lax", secure=False)
            return response


            # Set the JWT token as an HttpOnly cookie
            # try:
            #     response.set_cookie(
            #         key="jwt_token",
            #         value=jwt_token,
            #         httponly=False,
            #         secure=False,
            #         samesite="lax"
            #     )
            #
            # except Exception as e:
            #     response = RedirectResponse(url=frontend_url)
            #     logger.error(f"Error setting cookie: {e}")
            #
            # return response
        else:
            message = "There was an error inserting the user into the database (NOT GOOD! Tell Jonah)."

    else:
        message = "Sorry, it looks like you tried to use a non BU gmail to log in. Please log in with your BU gmail."

    frontend_url = f"{BASE_URL}/?message={message}"
    return RedirectResponse(url=frontend_url)


@app.post("/chat", response_model=ChatResponse)
async def send_question(data: ChatRequest, jwt_token: str = Depends(get_jwt_token)):
    # Get the user's email

    if not jwt_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Decode and verify the JWT token
        gmail = get_current_email(jwt_token=jwt_token)

        # Ensure the email is present in the decoded token
        if not gmail:
            raise HTTPException(status_code=401, detail="Invalid token")

        if gmail.endswith("@bu.edu") or gmail == "bradleyjocelyn3@gmail.com" or gmail == "georgeflint@berkeley.edu":
            if backend.user_exists(user_management=weaviate_user_management, gmail=gmail):
                try:
                    response_and_id = await backend.insert_message(search_agent=search_agent,
                                                                   user_management=weaviate_user_management,
                                                                   gmail=gmail,
                                                                   input_text=data.question)
                except Exception as e:
                    logger.error(f"error: {e}")
                    response_and_id = [
                        "Oh no! There was an issue finding your answer, please try refreshing or waiting a few seconds.",
                        str(uuid.uuid4())
                    ]

            else:
                response_and_id = [
                    "I'm sorry, it seems like there has been an error. Please login using your BU gmail above",
                    str(uuid.uuid4())
                ]
        else:
            response_and_id = [
                "I'm sorry, it seems like you are not logged in. Please login using your BU gmail above",
                str(uuid.uuid4())
            ]

        return ChatResponse(response=response_and_id[0], responseID=response_and_id[1])

    # except jwt.ExpiredSignatureError:
    #     raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.api_route("/feedback", methods=["POST"])
async def provide_feedback(data: FeedbackRequest):
    # Store or handle feedback
    # Returns a 200 status code with no body on success
    jwt_token = data.jwt_token
    gmail = get_current_email(jwt_token=jwt_token)
    if backend.user_exists(user_management=weaviate_user_management, gmail=gmail):
        try:
            backend.insert_feedback(user_management=weaviate_user_management, message_id=data.responseID, is_liked=data.is_liked)
        except Exception as e:
            logger.error(f"Feedback insertion error, {e}")
    else:
        logger.error(f"User {gmail} does not exist in the database.")
