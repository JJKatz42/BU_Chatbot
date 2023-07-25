import os
import uuid
import textwrap
from typing import List
from embeddings import EmbeddingsClient

from data_classes import TextContent, Webpage, MimeType
import html2text
from weaviate_store import WeaviateStore

# Constants (modify as necessary)
DIRECTORY_PATH = "/workspaces/BU_Chatbot/weavdb_direct"

WEAVIATE_INSTANCE_URL = "https://bu-cluster-2-o5pekqq0.weaviate.network"
WEAVIATE_API_KEY = "vXNsRxv6vSJ57r0JKOJxhlBwMDIBadbyvjGC"
OPENAI_API_KEY = "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"

NAMESPACE = "jonahs_weaviate"



embeddings_client = EmbeddingsClient(openai_api_key=OPENAI_API_KEY)



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
        title=file_url,
        mime_type=MimeType.MARKDOWN,
        text_contents=text_contents
    )

    embeddings_client.create_weaviate_object_embeddings([webpage])

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
    instance_url = WEAVIATE_INSTANCE_URL
    api_key = WEAVIATE_API_KEY
    openai_api_key = OPENAI_API_KEY
    directory_path = DIRECTORY_PATH

    store = WeaviateStore(instance_url, api_key, openai_api_key, namespace=NAMESPACE)
    store.create_schema(delete_if_exists=True)
    webpages = process_directory(directory_path)
    for webpage in webpages:
        embeddings_client.create_weaviate_object_embeddings([webpage])
    store.insert_webpage(webpages)


if __name__ == "__main__":
    main()
