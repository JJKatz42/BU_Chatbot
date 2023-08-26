import os
import random
import string
import urllib.parse
from typing import Union

import httpx
import jwt
from fastapi import Cookie
from fastapi import HTTPException, Query, FastAPI, Response, Request
from pydantic import BaseModel
from starlette.responses import RedirectResponse

import src.libs.config as config
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


env_file = ".env"
if not env_file.startswith("/"):
    current_directory = os.path.dirname(__file__)
    env_file = os.path.join(current_directory, env_file)
init_config(local_env_file=env_file)
# Initialize WeaviateStore and WeaviateSearchEngine


# Constants for setting and checking cookies

# Constants for Google OAuth

SECRET_KEY = config.get("SECRET_KEY")
ALGORITHM = config.get("ENCRYPTION_ALGORITHM")

CLIENT_ID = config.get("CLIENT_ID")
CLIENT_SECRET = config.get("CLIENT_SECRET")
REDIRECT_URI = config.get("REDIRECT_URI")

IS_LOCAL_ENV = config.get("IS_LOCAL_ENV")


def generate_google_auth_url(client_id: str, redirect_uri: str) -> str:
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    scope = "openid profile email"
    response_type = "code"
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": response_type,
        "state": state
    }
    auth_url = base_url + "?" + urllib.parse.urlencode(params)
    return auth_url


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
        print("No JWT token found in the request")
        raise HTTPException(status_code=401, detail="Not authenticated")

    else:
        print(f"JWT token: {jwt_token}")
        return jwt_token


app = FastAPI()


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.get("/")
async def read_root():
    with open(os.path.join("static", "index_deprecated.html"), "r") as f:
        content = f.read()
    return Response(content, media_type="text/html")


@app.get("/login")
def login():
    google_auth_url = generate_google_auth_url(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI)
    return RedirectResponse(url=google_auth_url)


@app.get("/auth/callback")
async def auth_callback(code: str = Query(...)):
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
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
    jwt_token = jwt.encode({"email": email}, SECRET_KEY, algorithm=ALGORITHM)
    # response = Response(content="Logged in successfully!")
    response = RedirectResponse(url="/")
    response.set_cookie(key="auth_token", value=jwt_token)  # Set the token as a cookie
    return response


class Question(BaseModel):
    question: str


@app.post("/chat")
def chat(question: Question, auth_token: str = Cookie(None)):
    if auth_token:
        # Here, you can add more logic to validate the token if needed
        return {"authorized": "True", "question": question, "answer": "boo", "gmail": get_current_email(auth_token)}
    return {"authorized": "False"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
