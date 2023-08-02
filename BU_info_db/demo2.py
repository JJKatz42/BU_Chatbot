import argparse
import asyncio
import os
import pprint

import config as config
# import libs.search as search
# import libs.storage as storage
import weaviate_store as weav_store
import data_transformer
import weaviate_search_engine as weav_search_engine
import directory_reader as directory_reader


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
        default="/workspaces/BU_Chatbot/weavdb_direct",
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
    weaviate_store = weav_store.WeaviateStore(
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


        # Load documents from Google Drive
        loader = directory_reader.DirectoryReader(script_args.directory)
        webpages = await loader.load_data()
        webpage_splitter_transformer = data_transformer.WebpageSplitterTransformer()
        for webpage in webpages.webpages:
            # Run documents through the DocumentSplitterTransformer to optimize for search and storage
            webpage_splitter_transformer.transform(webpage)

        # Insert documents to weaviate
        weaviate_store.insert_webpages(webpages.webpages)
        
        print("Finished building search indexes")

    elif script_args.command == "search":
        query = script_args.query
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = weav_search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        search_results = weaviate_search_engine.search(query_str=query, mode=mode, top_k=top_k)
        pprint.pprint(search_results)
    elif script_args.command == "ask":
        ask_str = script_args.ask
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = weav_search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        answer = weaviate_search_engine.ask(ask_str=ask_str, mode=mode, top_k=top_k)
        pprint.pprint(answer)
    elif script_args.command == "summarize":
        query_str = script_args.query
        mode = script_args.mode
        top_k = script_args.top_k

        weaviate_search_engine = weav_search_engine.WeaviateSearchEngine(
            weaviate_store=weaviate_store
        )
        summarization = weaviate_search_engine.summarize(query_str=query_str, mode=mode, top_k=top_k)
        pprint.pprint(summarization)


if __name__ == '__main__':
    asyncio.run(main())