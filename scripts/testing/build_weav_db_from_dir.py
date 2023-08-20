import os
import uuid
import textwrap
import html2text
from typing import Dict

from src.libs.storage.storage_data_classes import TextContent, Webpage, MimeType
from src.libs.storage.weaviate_store import WeaviateStore
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


def process_file(file_path: str, file_url: str) -> [str, str]:

    with open(file_path, "r") as f:
        html_content = f.read()

    return [file_url, html_content]


def process_directory(directory_path: str) -> Dict[str, str]:
    
    webpages = {}

    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        if os.path.isfile(file_path):
            file = process_file(file_path, file_name)
            webpages[file[0]] = file[1]

    return webpages


def build_webpage(html_content: str, file_url: str) -> Webpage:
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
        mime_type=MimeType.MARKDOWN,
        html_content=html_content,
        text_contents=text_contents
    )

    return webpage

# Check for updates
def update_db(crawled_webpages: Dict, store: WeaviateStore) -> None:

    current_webpages = store.get_all_webpages()

    webpages_to_add = []
    
    # Delete all the webpage objects where the url of the webpage object is not contained in the keys of the dictionary of crawled webpages
    for wp_url, wp_html in current_webpages.items():
        if wp_url not in crawled_webpages.keys():
            store.delete_webpage(wp_url)

    # Interate over the the crawled dictionary and check if the URL key in the dictionary is contained in the webpage object dictionary
    print(f"len crawled webpages {len(crawled_webpages.keys())}")
    print(f"len current webpages {len(current_webpages.keys())}")

    for crawled_url, crawled_html in crawled_webpages.items():
        if crawled_url in current_webpages.keys():
            # If the HTML content is not the same, delete the Webpage object along with its corresponding TextContent objects and then build a new Webpage object and create its corresponding TextContent objects
            if crawled_html != current_webpages[crawled_url]:
                store.delete_webpage(crawled_url)
                new_webpage = build_webpage(crawled_html, crawled_url)
                webpages_to_add.append(new_webpage)
        else:
            # If the URL is not contained in the Webpage object dictionary create the Webpage and its corresponding textContent objects
            new_webpage = build_webpage(crawled_html, crawled_url)
            webpages_to_add.append(new_webpage)

    print(f"len webpages to add {len(webpages_to_add)}")

    print(f"batch size: {store.client.batch.batch_size}")
        
    store.insert_webpage(webpages_to_add)


def count_files_in_directory(directory):
    try:
        files = os.listdir(directory)
        num_files = len([file for file in files if os.path.isfile(os.path.join(directory, file))])
        print(f'The directory {directory} contains {num_files} files.')
    except FileNotFoundError:
        print(f'The directory {directory} does not exist.')


def main():
    # Initialize config
    env_file = ".env"
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)
    
    instance_url = config.get("WEAVIATE_URL")
    api_key = config.get("WEAVIATE_API_KEY")
    openai_api_key = config.get("OPENAI_API_KEY")
    namespace = config.get("DATA_NAMESPACE")
    directory_path = DIRECTORY_PATH
    
    # embeddings_client = EmbeddingsClient(openai_api_key=config.get("OPENAI_API_KEY"))


    store = WeaviateStore(instance_url=instance_url, api_key=api_key, openai_api_key=openai_api_key, namespace=namespace)

    store.create_schema(delete_if_exists=True)
    # crawled_webpages = process_directory(directory_path)

    # update_db(crawled_webpages, store)




if __name__ == "__main__":
    main()