import argparse
import asyncio
import os
import pprint

print(os.environ.get('PYTHONPATH'))
print('PYTHONPATH' in os.environ)
root_folder = '/Users/jonahkatz/Desktop/BU_Chatbot'
print(root_folder in os.environ.get('PYTHONPATH', '').split(os.pathsep))


import BU_info_db.storage.weaviate_store as store
import BU_info_db.search.weaviate_search_engine as search_engine
import BU_info_db.storage.data_connnector.webpage_splitter as webpage_splitter
import BU_info_db.storage.data_connnector.directory_reader as directory_reader

from BU_info_db.config import config




def init_config(local_env_file: str | None):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="DATA_NAMESPACE"),
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

    build_indexes_parser = subparsers.add_parser("build-indexes", help="Build indexes used for search", argument_default=argparse.SUPPRESS)
    build_indexes_parser.add_argument(
        "--directory",
        help="By default directory is the questrom courses. ",
        default="/Users/jonahkatz/Desktop/BU_Chatbot/new_webpages4",
        action="store_true"
    )
    build_indexes_parser.add_argument("--env-file", help="Local .env file containing config values", default=".env")
    build_indexes_parser.add_argument(
        "--full-refresh",
        help="By default indexing is incremental. Set this flag to build indexes from scratch. "
             "This includes re-creating Weaviate schema by deleting all existing objects.",
        default=True,
        action="store_true"
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
    run_search_parser.add_argument("--env-file", help="Local .env file containing config values", default=".env")

    run_ask_parser = subparsers.add_parser("ask", help="Ask a question and get back answer based on search results")

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
    run_ask_parser.add_argument("--env-file", help="Local .env file containing config values", default=".env")

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
    run_summarize_parser.add_argument("--env-file", help="Local .env file containing config values", default=".env")

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
        namespace=config.get("DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )


    # Route to sub command specific logic either build indexes for search or run a search
    if script_args.command == "build-indexes":
        # Create weaviate schema
        if script_args.full_refresh:
            weaviate_store.create_schema(delete_if_exists=True)


        # Load Webpages from directory
        loader = directory_reader.DirectoryReader(script_args.directory)
        webpages = await loader.load_data()
        webpage_splitter_transformer = webpage_splitter.WebpageSplitterTransformer()
        for webpage in webpages.webpages:
            # Run webpages through the WebpageSplitterTransformer to optimize for search and storage
            webpage_splitter_transformer.transform(webpage)

        # Insert webpages to weaviate
        weaviate_store.insert_webpages(webpages.webpages)

        print("Finished building search indexes")

    elif script_args.command == "search":
        query = script_args.query
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        search_results = weaviate_search_engine.search(query_str=query, mode=mode, top_k=top_k)
        pprint.pprint(search_results)
    elif script_args.command == "ask":
        ask_str = script_args.ask
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        answer = weaviate_search_engine.ask(ask_str=ask_str, mode=mode, top_k=top_k)
        pprint.pprint(answer)
    elif script_args.command == "summarize":
        query_str = script_args.query
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        summarization = weaviate_search_engine.summarize(query_str=query_str, mode=mode, top_k=top_k)
        pprint.pprint(summarization)


if __name__ == '__main__':
    asyncio.run(main())