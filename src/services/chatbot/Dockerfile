FROM python:3.10.11-slim

WORKDIR /app

COPY 3rdparty-py/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY src src

# Make port 80 available to the world outside this container
EXPOSE 8000

CMD ["uvicorn", "src.services.chatbot.main:app", "--port", "8000", "--host", "0.0.0.0"]
