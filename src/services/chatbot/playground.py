import openai
from packaging import version

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)

if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {openai.__version__}"
                     " is less than the required version 1.1.1")
else:
    print("OpenAI version is compatible.")

import os
import uuid
import pathlib
from typing import *

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
import
# Initialize a reasoning LLM
client = langchain.chat_models.ChatOpenAI(
    model_name="gpt-3.5-turbo-0613",
    temperature=0.0,
    openai_api_key="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",
    streaming=True
)

# TODO figure out how to get the correct Type for the messages parameter. Is client.generate even the right method? 
stream = client.generate(
    model="gpt-3.5-turbo",
    messages=[BaseMessage(
        role="user",  # or "user" depending on the context
        content="Your message here"
    )],
    # messages=[{"role": "user", "content": "Please provide me a very, very in depth explanation of quantum mechanics in the style of Shakespeare."}],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")