from flask import Flask, request, jsonify
from flask_cors import CORS

import os
import time
from typing import Union
from dataclasses import asdict

import src.libs.config as config
import src.libs.storage.weaviate_store as store
import src.libs.search.weaviate_search_engine as search_engine
from src.libs.search.search_agent.search_agent import SearchAgent, SearchAgentFeatures
import langchain.chat_models


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


env_file = ".env"
if not env_file.startswith("/"):
    current_directory = os.path.dirname(__file__)
    env_file = os.path.join(current_directory, env_file)
init_config(local_env_file=env_file)

# Initialize WeaviateStore and WeaviateSearchEngine
weaviate_store = store.WeaviateStore(
    instance_url=config.get("WEAVIATE_URL"),
    api_key=config.get("WEAVIATE_API_KEY"),
    openai_api_key=config.get("OPENAI_API_KEY"),
    namespace=config.get("DATA_NAMESPACE"),
    cohere_api_key=config.get("COHERE_API_KEY")
)

weaviate_engine = search_engine.WeaviateSearchEngine(weaviate_store=weaviate_store)

# Initialize a reasoning LLM
reasoning_llm = langchain.chat_models.ChatOpenAI(
    model_name="gpt-3.5-turbo-0613",
    temperature=0.0,
    openai_api_key=config.get("OPENAI_API_KEY")
)

features = [SearchAgentFeatures.CROSS_ENCODER_RE_RANKING, SearchAgentFeatures.QUERY_PLANNING]

search_agent = SearchAgent(
    weaviate_search_engine=weaviate_engine,
    reasoning_llm=reasoning_llm,
    features=features
)

app = Flask(__name__)
CORS(app)


@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


async def search_agent_job(agent: SearchAgent, query: str) -> dict:
    print(f"Running job: {query}")
    search_job_start_time = time.time()
    result = await agent.run(query)
    result_dict = asdict(result)
    result_dict['search_job_duration'] = round((time.time() - search_job_start_time), 2)
    print(f"Running job: {query} finished")
    return result_dict


@app.route("/", methods=['GET', 'POST'])
async def chat():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            if 'input' in data:
                input_text = data['input']

                # Run the SearchAgent
                agent_result = await search_agent_job(search_agent, input_text)

                sorted_lst = sorted(agent_result['sources'], key=lambda x: x['score'], reverse=True)

                # Extract the first 5 URLs

                top_5_urls = [item['url'] for item in sorted_lst[:10]]

                url_str = ""
                num = 0
                for url in top_5_urls:
                    if url in url_str:
                        continue

                    num += 1
                    url_str += "<br>"  # Use HTML break line tag here
                    url_str += f"{num}. {url} "

                response = f"{agent_result['answer']} <br><br> Sources: {url_str}"  # Use HTML break line tag here

                print(f"SearchAgent answer: {response}.")

                result = jsonify({'response': response})

                return result
            else:
                return "Missing 'input' in the provided data", 400
        else:
            return "Request was not JSON", 400
    else:
        return "Hello, this is the chatbot. Please use POST method to send a message."


if __name__ == '__main__':
    app.run(port=5001, debug=True)
