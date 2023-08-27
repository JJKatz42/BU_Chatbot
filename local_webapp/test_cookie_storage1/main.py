from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.security.oauth2 import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

import jwt
from datetime import datetime, timedelta

app = FastAPI()

# Configuration
config = Config('../Succesful_cookie_storage_no_google_auth_or_JWT/.env')

app.add_middleware(SessionMiddleware, secret_key=config('SECRET_KEY', default='test'))

print(config('SECRET_KEY'))

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=config('GOOGLE_CLIENT_ID'),
    client_secret=config('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri=config('REDIRECT_URI', default='http://localhost:8000/auth/callback'),
    client_kwargs={'scope': 'openid profile email'},
)


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth")
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)

    # Create JWT token
    jwt_token = jwt.encode({
        "sub": user["email"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }, config('SECRET_KEY', default='test'), algorithm="HS256")

    response = RedirectResponse(url="/")
    response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=True)
    return response


@app.get("/")
async def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
