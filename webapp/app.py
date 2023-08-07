from flask import Flask, request, jsonify
from flask_cors import CORS

from json import dumps
import os
from typing import Union

import argparse
import asyncio
import csv
import enum
import getpass
import json
import shutil
import time
import openai
from dataclasses import asdict
from datetime import datetime

import langchain.chat_models
import pydantic

import BU_info_db.eval.evaluation_test_schema as evaluation_test_schema
import BU_info_db.eval.evaluation_agent as evaluation_agent

from BU_info_db.config import config
from BU_info_db.search.search_agent import SearchAgent
from BU_info_db.search.search_agent import SearchAgentFeatures
import BU_info_db.search.weaviate_search_engine as search_engine

import BU_info_db.storage.weaviate_store as store

from BU_info_db.config import config

app = Flask(__name__)
CORS(app)


@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


def init_config(local_env_file: Union[str, None]):
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


async def search_agent_job(agent: SearchAgent, query: str) -> dict:
    print(f"Running job: {query}")
    search_job_start_time = time.time()
    result = await agent.run(query=query)

    result_dict = asdict(result)
    result_dict['search_job_duration'] = round((time.time() - search_job_start_time), 2)
    print(f"Running job: {query} finished")
    return result_dict


@app.route("/", methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            input_text = data['input']

            env_file = ".env"
            if not env_file.startswith("/"):
                current_directory = os.path.dirname(__file__)
                env_file = os.path.join(current_directory, env_file)
            init_config(local_env_file=env_file)

            weaviate_store = store.WeaviateStore(
                instance_url=config.get("WEAVIATE_URL"),
                api_key=config.get("WEAVIATE_API_KEY"),
                openai_api_key=config.get("OPENAI_API_KEY"),
                namespace=config.get("DATA_NAMESPACE"),
                cohere_api_key=config.get("COHERE_API_KEY")
            )
            # Initialize a search engine
            weaviate_search_engine = search_engine.WeaviateSearchEngine(weaviate_store=weaviate_store)
            # Initialize a reasoning LLM
            reasoning_llm = langchain.chat_models.ChatOpenAI(
                model_name="gpt-3.5-turbo-0613",
                temperature=0.0,
                openai_api_key=config.get("OPENAI_API_KEY")
            )
            # Initialize the search agent with the search engine and reasoning llm
            # print(f"search_agent_features={script_args.search_agent_features}")
            search_agent_features = [SearchAgentFeatures.CROSS_ENCODER_RE_RANKING]
            search_agent_args = {
                "weaviate_search_engine": weaviate_search_engine,
                "reasoning_llm": reasoning_llm,
                "features": search_agent_features
            }
            search_agent = SearchAgent(**search_agent_args)

            # Load the content of the test file

            print("Question!")
            print(f"\tquestion: {input_text}")

            # Run all tests
            result = search_agent_job(search_agent, input_text)
            search_run_time = round((time.time() - start_time), 1)

            return jsonify({'response': result})
        else:
            return "Request was not JSON", 400
    else:
        return "Hello, this is the chatbot. Please use POST method to send a message."


if __name__ == '__main__':
    app.run(port=5001, debug=True)