import os
import uuid
import textwrap
import html2text
from typing import List

from embeddings import EmbeddingsClient
from storage_data_classes import TextContent, Webpage, MimeType
from weaviate_store import WeaviateStore
from src.libs.config import config

# Constants (modify as necessary)
DIRECTORY_PATH = "/workspaces/BU_Chatbot/Questrom_Course_Info"

def init_config(local_env_file: str | None):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="WEAVIATE_URL"),
            config.ConfigVarMetadata(var_name="WEAVIATE_API_KEY"),
            config.ConfigVarMetadata(var_name="OPENAI_API_KEY"),
        ],
        local_env_file=local_env_file
    )



def process_file(file_path: str, file_url: str) -> Webpage:
    with open(file_path, "r") as f:
        html_content = f.read()

    h_1 = html2text.HTML2Text()
    h_1.ignore_links = True
    h_2 = h_1.handle(html_content)
    clean_text = h_2
    chunks = textwrap.wrap(clean_text, 3000)

    text_contents = []
    for i, chunk in enumerate(chunks):
        text_content_object = TextContent(text=chunk, index=i)
        text_contents.append(text_content_object)

    webpage = Webpage(
        id=str(uuid.uuid4()),
        url=file_url,
        html_content=html_content,
        mime_type=MimeType.MARKDOWN,
        text_contents=text_contents
    )

    return webpage


def process_directory(directory_path: str) -> List[Webpage]:
    webpages = []

    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        if os.path.isfile(file_path):
            file_url = file_name
            webpages.append(process_file(file_path, file_url))

    return webpages


def main():
    # init_config(".env")
    env_file = ".env"
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)

    instance_url = config.get("WEAVIATE_URL")
    api_key = config.get("WEAVIATE_API_KEY")
    openai_api_key = config.get("OPENAI_API_KEY")
    directory_path = DIRECTORY_PATH

    embeddings_client = EmbeddingsClient(openai_api_key=openai_api_key)

    store = WeaviateStore(instance_url, api_key, openai_api_key, namespace=config.get("DATA_NAMESPACE"))
    store.create_schema(delete_if_exists=True)
    webpages = process_directory(directory_path)
    for webpage in webpages:
        embeddings_client.create_weaviate_object_embeddings([webpage])
    store.insert_webpages(webpages)


if __name__ == "__main__":
    main()