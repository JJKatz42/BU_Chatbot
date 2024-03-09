import sys
from pathlib import Path

projectroot = Path(__file__).resolve().parent.parent
sys.path.append(str(projectroot))

import argparse
import asyncio
import os

import src.libs.logging as logging
import src.libs.storage.weaviate_store as store
import src.libs.search.weaviate_search_engine as search_engine
import src.libs.storage.data_connnector.webpage_splitter as webpage_splitter
import src.libs.storage.data_connnector.directory_reader as directory_reader

from src.libs.config import config


logger = logging.getLogger(__name__)


def init_config(local_env_file: str | None):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="INFO_DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="WEAVIATE_URL"),
            config.ConfigVarMetadata(var_name="WEAVIATE_API_KEY"),
            config.ConfigVarMetadata(var_name="OPENAI_API_KEY"),
            config.ConfigVarMetadata(var_name="COHERE_API_KEY"),
        ],
        local_env_file=local_env_file
    )


async def main():
    parser = argparse.ArgumentParser(
        prog="Interact with the search engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

    build_indexes_parser = subparsers.add_parser(
        "build-indexes",
        help="Build indexes used for search",
        argument_default=argparse.SUPPRESS
    )
    build_indexes_parser.add_argument(
        "--directory",
        help="By default directory is the beta_info directory",
        default="/Users/georgeflint/Desktop/berkeley_crawler_data_divided10/berkeley_crawler_data_batch_1"
    )
    build_indexes_parser.add_argument(
        "--university",
        help="By default university is set to BU",
        default="CAL"
    )
    build_indexes_parser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default="/Users/georgeflint/Desktop/BU_Chatbot/src/services/chatbot/.env"
    )
    build_indexes_parser.add_argument(
        "--full-refresh",
        help="By default indexing is incremental. Set this flag to build indexes from scratch. "
             "This includes re-creating Weaviate schema by deleting all existing objects.",
        default=False
    )
    run_search_parser = subparsers.add_parser("search", help="Run a search query and get back search result")
    run_search_parser.add_argument("query", nargs="?", default="describe sm 132")
    run_search_parser.add_argument(
        "--mode",
        choices=["semantic", "hybrid", "keyword"],
        help="If 'semantic', the search will be a pure vector search. "
             "If 'hybrid', both vector and keyword search will be used."
             "If 'keyword', keyword search will be used.",
        default="hybrid"
    )
    run_search_parser.add_argument(
        "--top-k",
        type=int,
        help="Number of most relevant results to return",
        default=3
    )
    run_search_parser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default="/Users/jonahkatz/Dev/BU_Chatbot/src/services/chatbot/.env"
    )

    run_ask_parser = subparsers.add_parser(
        "ask",
        help="Ask a question and get back answer based on search results"
    )

    run_ask_parser.add_argument("ask", nargs="?")
    run_ask_parser.add_argument(
        "--mode",
        choices=["semantic", "hybrid", "keyword"],
        help="If 'semantic', the search will be a pure vector search. "
             "If 'hybrid', both vector and keyword search will be used."
             "If 'keyword', keyword search will be used.",
        default="hybrid"
    )
    run_ask_parser.add_argument(
        "--top-k",
        type=int,
        help="Number of most relevant results to return",
        default=3
    )
    run_ask_parser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default="/Users/jonahkatz/Dev/BU_Chatbot/src/services/chatbot/.env")

    run_summarize_parser = subparsers.add_parser("summarize", help="Summarize query search results")
    run_summarize_parser.add_argument("query", nargs="?")
    run_summarize_parser.add_argument(
        "--mode",
        choices=["semantic", "hybrid", "keyword"],
        help="If 'semantic', the search will be a pure vector search. "
             "If 'hybrid', both vector and keyword search will be used."
             "If 'keyword', keyword search will be used.",
        default="hybrid"
    )
    run_summarize_parser.add_argument(
        "--top-k",
        type=int,
        help="Number of most relevant results to return",
        default=3
    )
    run_summarize_parser.add_argument(
        "--env-file",
        help="Local .env file containing config values",
        default="/Users/jonahkatz/Dev/BU_Chatbot/src/services/chatbot/.env")

    script_args = parser.parse_args()

    # Initialize config
    env_file = script_args.env_file
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)

    # Initialize weaviate store
    weaviate_store = store.WeaviateStore(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("INFO_DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )

    # Route to sub command specific logic either build indexes for search or run a search
    if script_args.command == "build-indexes":
        # Create weaviate schema
        if script_args.full_refresh:
            weaviate_store.create_schema(delete_if_exists=True)

        # Load Webpages from directory
        logger.info("Loading webpages from directory")
        loader = directory_reader.DirectoryReader(script_args.directory, university="BU")
        webpages = await loader.load_data()
        logger.info(f"Loaded {len(webpages.webpages)} webpages")
        logger.info("Transforming webpages")
        webpage_splitter_transformer = webpage_splitter.WebpageSplitterTransformer()
        for webpage in webpages.webpages:
            # Run webpages through the WebpageSplitterTransformer to optimize for search and storage
            webpage_splitter_transformer.transform(webpage)

        logger.info("Inserting webpages to weaviate")
        # Insert webpages to weaviate
        weaviate_store.insert_webpages(webpages.webpages)

        logger.info("Finished building search indexes")

    elif script_args.command == "search":
        query = script_args.query
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        search_results = weaviate_search_engine.search(query_str=query, mode=mode, top_k=top_k)
        logger.info(search_results)
    elif script_args.command == "ask":
        ask_str = script_args.ask
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        answer = weaviate_search_engine.ask(ask_str=ask_str, mode=mode, top_k=top_k)
        logger.info(answer)
    elif script_args.command == "summarize":
        query_str = script_args.query
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        summarization = weaviate_search_engine.summarize(query_str=query_str, mode=mode, top_k=top_k)
        logger.info(summarization)


if __name__ == '__main__':
    asyncio.run(main())
