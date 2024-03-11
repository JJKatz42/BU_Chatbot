import argparse
import asyncio
import hashlib
import uuid

import weaviate
import datetime
import os
import time
import langchain.chat_models
from dataclasses import asdict

import src.libs.storage.weaviate_store as store
import src.libs.search.weaviate_search_engine as search_engine
from src.libs.search.search_agent.search_agent import SearchAgent, SearchAgentFeatures
from src.libs.config import config
import src.libs.storage.user_management as user_management
import src.libs.storage.user_data_classes as data_classes
import src.libs.logging as logging

logger = logging.getLogger(__name__)


def init_config(local_env_file: str | None):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="USER_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="INFO_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="WEAVIATE_URL"),
            config.ConfigVarMetadata(var_name="WEAVIATE_API_KEY"),
            config.ConfigVarMetadata(var_name="OPENAI_API_KEY"),
            config.ConfigVarMetadata(var_name="COHERE_API_KEY"),
        ],
        local_env_file=local_env_file
    )


User = {
        "class": "blah",
        "vectorizer": "none",
        "vectorIndexConfig": {
            "skip": True
        },
        "invertedIndexConfig": {
            "indexNullState": True,
        },
        "properties": [
            {
                "name": "personalized_info_vector",
                "dataType": ["number[]"],  # Vector is not an available datatype in weaviate,
                # see: https://weaviate.io/developers/weaviate/config-refs/datatypes
            }
        ]
    }


async def main():
    env_file = "/Users/jonahkatz/Dev/BU_Chatbot/src/services/chatbot/.env"
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)

    user_related_classes = [User]

    client = weaviate.Client(
        url='https://test-bu-toevf0ik.weaviate.network',
        auth_client_secret=weaviate.AuthApiKey(api_key="Nl3vl9rgW1w1C7yGajToDMZpKbbp7IsXExnf"),
        additional_headers={
            "X-OpenAI-Api-Key": config.get("OPENAI_API_KEY"),
            "X-Cohere-Api-Key": config.get("COHERE_API_KEY")
        }
    )

    weaviate_store_info = store.WeaviateStore(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("INFO_DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )

    user_class_name = "blah"
    if client.schema.exists(user_class_name):
        delete_if_exists = True
        if delete_if_exists:
            client.schema.delete_class(user_class_name)
        else:
            raise Exception(f"Can't create schema because {user_class_name} already exists. "
                            f"Set delete_if_exists=True to re-create the schema.")

    try:
        client.schema.create({
            "classes": [
                User
            ]
        })

    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        # Add further error handling or logging here as needed.

    vec = weaviate_store_info.create_embedding("blah")[0]

    print(vec)

    data = {
        "personalized_info_vector": vec
    }

    blah = "blah1"

    blah = blah.encode()

    try:
        hashes = hashlib.md5(blah).hexdigest()
        user_uuid = client.data_object.create(
            class_name="blah",
            uuid=uuid.UUID(hex=hashes),
            data_object=data
        )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False





if __name__ == '__main__':
    asyncio.run(main())