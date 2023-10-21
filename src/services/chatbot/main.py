import os
import uuid
import pathlib
from typing import Union

import httpx
import jwt
import langchain.chat_models
import langchain.chat_models
from fastapi import Cookie
from fastapi import HTTPException, Query, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

import src.libs.config as config
import src.libs.logging as logging
import src.libs.search.weaviate_search_engine as search_engine
import src.libs.storage.user_management as user_management
import src.libs.storage.weaviate_store as store
import src.services.chatbot.backend_control.backend as backend
from src.libs.search.search_agent.search_agent import SearchAgent, SearchAgentFeatures
from src.services.chatbot.backend_control.auth import generate_google_auth_url
from src.services.chatbot.backend_control.models import ChatRequest, FeedbackRequest
from src.services.chatbot.backend_control.models import ChatResponse, IsAuthorizedResponse

logger = logging.getLogger(__name__)


def init_config(local_env_file: Union[str, None]):
    """
    Initialize the config module.

    Parameters:
        local_env_file (str | None): Path to the local .env file.

    Returns:
        None
    """
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


env_file = ".env"
if not env_file.startswith("/"):
    current_directory = os.path.dirname(__file__)
    env_file = os.path.join(current_directory, env_file)
init_config(local_env_file=env_file)

WHITE_LISTED_EMAILS = [
    "bradleyjocelyn3@gmail.com",
    "georgeflint@berkeley.edu",
    "jonahkatz@gmail.com",
    "ernisierra@gmail.com",
    "ellenkatz@gmail.com",
    "henrykatz@gmail.com",
    "ellenkatz@gmail.com",
    "sasha.vasu@gmail.com",
    "dgkatz@gmail.com",
    "nathanvlad@gmail.com"
]

SECRET_KEY = config.get("SECRET_KEY")
ALGORITHM = config.get("ENCRYPTION_ALGORITHM")

CLIENT_ID = config.get("CLIENT_ID")
CLIENT_SECRET = config.get("CLIENT_SECRET")
REDIRECT_URI = config.get("REDIRECT_URI")

IS_LOCAL_ENV = config.get("IS_LOCAL_ENV")

if str(IS_LOCAL_ENV) == "True":
    BASE_URL = "http://localhost:8000"
    DOMAIN = "localhost:8000"
    SECURE = False
else:
    BASE_URL = "https://app.busearch.com"
    DOMAIN = "app.busearch.com"
    SECURE = True

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


def get_current_email(jwt_token: str) -> str:
    """
    Decode and verify the JWT token.

    Parameters:
        jwt_token (str): The JWT token to decode and verify.

    Returns:
        str: The email address of the user.
    """
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

    Parameters:
        request (Request): The request object.

    Returns:
        str: The JWT token.
    """
    jwt_token = request.cookies.get("Authorization")
    if not jwt_token:
        print("No JWT token found in the request")
        raise HTTPException(status_code=401, detail="Not authenticated")

    else:
        print(f"JWT token: {jwt_token}")
        return jwt_token


app = FastAPI()

file_dir = pathlib.Path(__file__).parent.resolve()

INDEX_PATH = (file_dir / "static").as_posix()

app.mount("/static", StaticFiles(directory=INDEX_PATH), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    """
    Serves the index.html file.
    """
    return FileResponse(INDEX_PATH + "/index.html")


@app.get("/login")
def login():
    """
    Redirects the user to the Google OAuth2 login page.
    """
    google_auth_url = generate_google_auth_url(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI)
    return RedirectResponse(url=google_auth_url)


@app.get("/auth/callback")
async def auth_callback(code: str = Query(...)):
    """
    Callback URL for Google OAuth2.
    """
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    # Fetch user's info
    async with httpx.AsyncClient() as client:
        response = await client.post("https://oauth2.googleapis.com/token", data=token_data)
    token_response = response.json()
    access_token = token_response.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)

    user_info = response.json()

    email = user_info["email"]

    if email.endswith("@bu.edu") or email in WHITE_LISTED_EMAILS:
        # Insert the user into the database
        user_inserted_successfully = backend.insert_user(user_management=weaviate_user_management, gmail=email)
        if user_inserted_successfully:
            # Create a JWT token
            jwt_token = jwt.encode({"email": email}, SECRET_KEY, algorithm=ALGORITHM)
            # Redirect user to the root after logging in
            response = RedirectResponse(url="/")
            # Set the token as a cookie
            response.set_cookie(
                key="auth_token",
                value=jwt_token,
                secure=SECURE,
                httponly=True,
                samesite="lax",
                max_age=7 * 24 * 60 * 60
            )

            return response
        else:
            # User was not inserted successfully
            response = RedirectResponse(url="/?message=you-must-be-a-BU-student-to-access-this-page")
            return response
    # User did not use a BU email
    response = RedirectResponse(url="/?message=you-must-use-a-BU-account-to-access-this-page")
    return response


@app.get("/logout")
async def logout(request: Request):
    """
    Logs out the user by clearing the JWT token from their cookies.
    """
    response = RedirectResponse(url="/")  # Redirect user to the root after logging out
    response.delete_cookie("auth_token")  # Delete the JWT token cookie
    return response


@app.get("/is-authorized", response_model=IsAuthorizedResponse)
async def is_authorized(request: Request):
    """
    Checks if the user has a valid JWT token in their cookies and is authorized.
    """
    jwt_token = request.cookies.get("auth_token")  # Get the JWT token from the cookies
    if not jwt_token:
        return IsAuthorizedResponse(is_authorized=False)  # Return the response
    try:
        get_current_email(jwt_token=jwt_token)  # If the JWT token is valid, the user is authorized
        return IsAuthorizedResponse(is_authorized=True)  # Return the response
    except HTTPException as e:
        if e.status_code == 401:
            return IsAuthorizedResponse(is_authorized=False)  # Return the response
        raise  # Any other unexpected errors can be raised normally


@app.post("/chat", response_model=ChatResponse)
async def chat(data: ChatRequest, auth_token: str = Cookie(None)):
    """
    Chat with the bot.
    """
    if auth_token:
        # Decode and verify the JWT token
        email = get_current_email(jwt_token=auth_token)

        # Ensure the email is present in the decoded token
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")

        if email.endswith("@bu.edu") or email in WHITE_LISTED_EMAILS:  # Check if the user is a BU student
            if backend.user_exists(user_management=weaviate_user_management, gmail=email):
                try:
                    response_and_id = await backend.insert_message(
                        search_agent=search_agent,
                        user_management=weaviate_user_management,
                        gmail=email,
                        input_text=data.question,
                        cap=50
                    )  # Insert the question and answer into the database
                except Exception as e:
                    logger.error(f"error: {e}")
                    response_and_id = [
                        "Oh no! There was an issue finding your answer, "
                        "please try refreshing or waiting a few seconds.",
                        str(uuid.uuid4())
                    ]

            else:
                response_and_id = [
                    "I'm sorry, it seems like you have not been logged in. BUsearch is exclusive to BU students.",
                    str(uuid.uuid4())
                ]  # User does not exist in the database
        else:
            response_and_id = [
                "I'm sorry, it seems like there was an error when you signed in. "
                "Please clear your cookies and log in again using your BU email.",
                str(uuid.uuid4())
            ]  # User is not a BU student
    else:
        logger.warning(f"User not authenticated")
        response_and_id = [
            "I'm sorry, it seems like there was an error when you signed in. "
            "Please clear your cookies and log in again using your BU email",
            str(uuid.uuid4())
        ]  # User is not authenticated

    return ChatResponse(response=response_and_id[0], responseID=response_and_id[1])  # Return the response


@app.api_route("/feedback", methods=["POST"])
async def provide_feedback(data: FeedbackRequest, auth_token: str = Cookie(None)):
    """
    Provide feedback on the bot's response.
    """
    jwt_token = auth_token  # Get the JWT token from the cookies
    email = get_current_email(jwt_token=jwt_token)  # Decode and verify the JWT token
    if backend.user_exists(user_management=weaviate_user_management, gmail=email):
        try:
            backend.insert_feedback(user_management=weaviate_user_management, message_id=data.responseID,
                                    is_liked=data.is_liked)
        except Exception as e:
            logger.error(f"Feedback insertion error, {e}")
    else:
        logger.error(f"User {email} does not exist in the database.")
