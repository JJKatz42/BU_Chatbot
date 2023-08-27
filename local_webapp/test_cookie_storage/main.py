from typing import Union
import uuid
import os

from fastapi import FastAPI, Depends, HTTPException, Response
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import jwt
from datetime import datetime, timedelta
from starlette.requests import Request

import src.libs.config as config


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


# Configuration
env_file = ".env"
if not env_file.startswith("/"):
    current_directory = os.path.dirname(__file__)
    env_file = os.path.join(current_directory, env_file)
init_config(local_env_file=env_file)


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=config.get(var_name="SECRET_KEY"))

print(config.get(var_name="SECRET_KEY"))

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=config.get('CLIENT_ID'),
    client_secret=config.get('CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri=config.get('REDIRECT_URI', default='http://localhost:8000/auth/callback'),
    client_kwargs={'scope': 'openid profile email'},
)


@app.get("/login")
async def login(request: Request):
    state = str(uuid.uuid4())
    request.session["state"] = state
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    state_in_session = request.session.get("state")
    state_in_callback = request.query_params.get("state")

    if not state_in_session or state_in_session != state_in_callback:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)

    # Create JWT token
    jwt_token = jwt.encode({
        "sub": user["email"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }, config.get('SECRET_KEY', default='test'), algorithm="HS256")

    response = Response(content={"message": "Cookie set successfully!"})
    response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=True)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)