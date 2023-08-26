from fastapi import FastAPI, Depends, HTTPException, Response, Request
from fastapi.security.oauth2 import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import jwt
from datetime import datetime, timedelta
from starlette.responses import FileResponse

from starlette.responses import RedirectResponse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Configuration
config = Config('.env')

print("CLIENT_ID", config('SECRET_KEY'))

app.add_middleware(SessionMiddleware, secret_key=config('SECRET_KEY', default='test'))

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=config('CLIENT_ID'),
    client_secret=config('CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri='http://localhost:8000/auth/callback',
    client_kwargs={'scope': 'openid profile email'},
)


@app.get("/login")
async def login(request: Request):
    redirect_uri = 'http://localhost:8000/auth/callback'
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)

    # Create JWT token
    jwt_token = jwt.encode({
        "sub": user["email"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }, config('SECRET_KEY', default='test'), algorithm="HS256")

    response = RedirectResponse(url="/")
    response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=False)
    return response


@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
