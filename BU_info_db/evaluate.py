import argparse
import asyncio
import csv
import enum
import getpass
import json
import os
import shutil
import time
from dataclasses import asdict
from datetime import datetime

import langchain.chat_models
import pydantic
import config

import evaluation_test_schema as evaluation_test_schema
# import libs.agents as agents
import evaluation_agent as evaluation_agent
# import libs.config as config
# import libs.search as search
import search_agent as SearchAgent
from search_agent import SearchAgentFeatures
from weaviate_search_engine import WeaviateSearchEngine
from search_agent import SearchAgent
# import libs.storage as storage
from weaviate_store import WeaviateStore


# Constants (modify as necessary)

# Files and directories
ARCHIVE_DIRECTORY = "archive"
SCORES_FILE = "scores.json"
SUMMARY_FILE = "summary.txt"
TEST_RESULTS_FILE = "test_results.csv"



def init_config(local_env_file: str | None):
    config.init(
        metadata=[
            config.ConfigVarMetadata(var_name="DATA_NAMESPACE"),
            config.ConfigVarMetadata(var_name="WEAVIATE_URL"),
            config.ConfigVarMetadata(var_name="WEAVIATE_API_KEY"),
            config.ConfigVarMetadata(var_name="OPENAI_API_KEY"),
            config.ConfigVarMetadata(var_name="EVALUATE_OPENAI_API_KEY"),
            config.ConfigVarMetadata(var_name="COHERE_API_KEY"),
        ],
        local_env_file=local_env_file
    )


def custom_json_encoder(obj):
    if isinstance(obj, pydantic.BaseModel):
        return obj.dict()
    elif isinstance(obj, enum.Enum):
        return obj.value
    else:
        return str(obj)


async def search_agent_job(agent: SearchAgent, query: str) -> dict:
    print(f"Running job: {query}")
    search_job_start_time = time.time()
    result = await agent.run(query=query)

    result_dict = asdict(result)
    result_dict['search_job_duration'] = round((time.time() - search_job_start_time), 2)
    print(f"Running job: {query} finished")
    return result_dict


async def run_search_agent_jobs(agent: SearchAgent, test_specs: list[dict]):
    # Run all tests
    tasks = []
    for spec in test_specs:
        query = spec['definition']['request']
        if spec['definition']['enable']:
            task = asyncio.create_task(search_agent_job(agent, query))
            tasks.append(task)
        else:
            print(f"Skipping disabled query {query}")

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    return results


async def evaluation_agent_job(agent: evaluation_agent.EvaluationAgent,
                               query: str,
                               expected_rsp: str,
                               bot_rsp: str) -> dict:
    print(f"Running evaluation job: {query}")
    result = await agent.run(query=query, expected_rsp=expected_rsp, bot_rsp=bot_rsp)

    print(f"Running Evaluation job: {query} finished")
    return asdict(result)


async def run_evaluation_agent_jobs(agent: evaluation_agent.EvaluationAgent,
                                    test_specs: list[dict],
                                    bot_responses: list[dict]):
    # Run all evaluations
    tasks = []
    for count, spec in enumerate(test_specs):
        query = spec['definition']['request']
        if spec['definition']['enable']:
            task = asyncio.create_task(evaluation_agent_job(agent,
                                                            query,
                                                            spec['definition']['expected_response'],
                                                            bot_responses[count]['result']))
            tasks.append(task)
        else:
            print(f"Skipping disabled query {query}")

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    return results


def save_object_to_json_file(dictionary, filename):
    try:
        with open(filename, 'w') as file:
            json.dump(dictionary, file, default=custom_json_encoder)
    except FileNotFoundError:
        print("Error: File not found")
    except PermissionError:
        print("Error: Permission denied to open the file")
    except IOError as e:
        print(f"I/O error occurred: {e}")
    except json.JSONDecodeError as e:
        print(f"Error in encoding JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def load_data_from_json_file(filename):
    try:
        # Read JSON data from a file
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print("File not found.")
    except json.JSONDecodeError:
        print("Error decoding JSON data.")
    except Exception as e:
        print("An error occurred:", str(e))

    return data


def check_test_file(test_specs: list[dict]):
    # check schema compliance
    evaluation_test_schema.EvaluationTestList.parse_obj(test_specs)


def select_tests_to_run_by_id(test_specs: list[dict], test_ids: list) -> list[dict]:
    return [x for x in test_specs if x['metadata']['test_id'] in test_ids]


def select_tests_to_run_by_tag(test_specs: list[dict], tags: list) -> list[dict]:
    return [x for x in test_specs if has_overlap(x['metadata']['classification_tags'], tags)]


async def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(
        prog="Evaluate Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--env-file", help="Local .env file containing config values. Default=.env",
                        default=".env")
    parser.add_argument("--test-file", help="File containing tests. Default=/workspaces/BU_Chatbot/BU_info_db/test_registry.json",
                        default="/workspaces/BU_Chatbot/BU_info_db/test_registry.json")
    parser.add_argument("--score-thresh", help="Log test results to summary.txt if test score is equal to or less "
                                               "than this score. Default=100", type=int, default=100)
    parser.add_argument("--reasoning-llm", help="Reasoning LLM model name. Default=gpt-3.5-turbo-0613",
                        default="gpt-3.5-turbo-0613")
    parser.add_argument("--evaluation-llm", help="Evaluation LLM model name. Default=gpt-4-0613",
                        default="gpt-3.5-turbo-0613")
    parser.add_argument("--search-agent-features", type=SearchAgentFeatures, nargs="+",
                        default=[SearchAgentFeatures.CROSS_ENCODER_RE_RANKING,
                                 SearchAgentFeatures.QUERY_PLANNING],
                        help="List of Search Agent features, space-separated, "
                             "Default=CROSS_ENCODER_RE_RANKING QUERY_PLANNING")
    parser.add_argument("--test-ids", nargs="+",
                        default=[],
                        help="Subset of test ids to run (from the --test-file), space-separated. Default: run all")
    parser.add_argument("--verbose", help="Verbose output to stdout", action="store_true")
    # # parser.add_argument("--slack-only", help="Limit evaluation to slack sources only", action="store_true")
    parser.add_argument("--csv", help="Write test results to CSV file: test_results.csv", action="store_true", default=True)
    parser.add_argument("--tags", nargs="+",
                        default=[],
                        help="Select tests that have at least one of specified tags.  Default: no filtering")

    script_args = parser.parse_args()

    reasoning_llm_model_name = script_args.reasoning_llm
    evaluation_llm_model_name = script_args.evaluation_llm

    # Initialize config
    env_file = script_args.env_file
    if not env_file.startswith("/"):
        current_directory = os.path.dirname(__file__)
        env_file = os.path.join(current_directory, env_file)
    init_config(local_env_file=env_file)

    # Initialize weaviate store
    weaviate_store = WeaviateStore(
        instance_url=config.get("WEAVIATE_URL"),
        api_key=config.get("WEAVIATE_API_KEY"),
        openai_api_key=config.get("OPENAI_API_KEY"),
        namespace=config.get("DATA_NAMESPACE"),
        cohere_api_key=config.get("COHERE_API_KEY")
    )
    # Initialize a search engine
    weaviate_search_engine = WeaviateSearchEngine(weaviate_store=weaviate_store)
    # Initialize a reasoning LLM
    reasoning_llm = langchain.chat_models.ChatOpenAI(
        model_name=reasoning_llm_model_name,
        temperature=0.0,
        openai_api_key=config.get("OPENAI_API_KEY")
    )
    # Initialize the search agent with the search engine and reasoning llm
    # print(f"search_agent_features={script_args.search_agent_features}")
    search_agent_args = {
        "weaviate_search_engine": weaviate_search_engine,
        "reasoning_llm": reasoning_llm,
        # "features": script_args.search_agent_features
    }
    search_agent = SearchAgent(**search_agent_args)

    # Read and validate the JSON file
    if not evaluation_test_schema.EvaluationTestSchema.validate_test_file(script_args.test_file):
        print("validate_test_file failure!")
        raise Exception("validate_test_file failure!")
    # Load the content of the test file
    test_specs = load_data_from_json_file(script_args.test_file)
    # validate  test file contents
    check_test_file(test_specs)
    # select tests if requested in CLI
    if len(script_args.test_ids) > 0:
        test_specs = select_tests_to_run_by_id(test_specs, script_args.test_ids)
    if len(script_args.tags) > 0:
        test_specs = select_tests_to_run_by_tag(test_specs, script_args.tags)

    print("Questions!")
    for spec in test_specs:
        print(f"\tquestion: {spec['definition']['request']}")

    # Run all tests
    results = await run_search_agent_jobs(search_agent, test_specs)
    search_run_time = round((time.time() - start_time), 1)

    # Prepare structures for langchain evaluation
    examples = []
    predictions = []
    for count, spec in enumerate(test_specs):
        if not spec['definition']['enable']:
            continue
        example, prediction = {}, {}
        example['query'] = spec['definition']['request']
        example['answer'] = spec['definition']['expected_response']
        prediction['result'] = results[count]['answer']
        examples.append(example)
        predictions.append(prediction)

    # Initialize an evaluation LLM
    evaluation_llm = langchain.chat_models.ChatOpenAI(
        model_name=evaluation_llm_model_name,
        temperature=0.0,
        openai_api_key=config.get("OPENAI_API_KEY")
    )

    # Initialize the evaluation agent with evaluation llm
    eval_agent = evaluation_agent.EvaluationAgent(
        evaluation_llm=evaluation_llm
    )
    # Run all evaluations
    evaluations = await run_evaluation_agent_jobs(eval_agent, test_specs, predictions)

    # Create a complete evaluation structure and write it to a file
    test_results = []
    test_summary = {
        'evaluation_score': 0,
        'search_agent_tokens_used': 0,
        'search_agent_tokens_cost': 0,
        'evaluation_tokens_used': 0,
        'evaluation_tokens_cost': 0,
        'number_of_tests': 0,
        'cumulative_score': 0,
        'slowest_test': {'test_id': "", 'time': 0.0, "tokens": 0, "cost": 0.0},
        'priciest_test': {'test_id': "", 'time': 0.0, "tokens": 0, "cost": 0.0},
        'namespace': config.get("DATA_NAMESPACE"),
        'user': getpass.getuser(),
        'datetime': datetime.now().isoformat()}

    for idx, spec in enumerate(test_specs):
        test = {'definition': spec['definition'],
                'metadata': spec['metadata']}
        if not spec['definition']['enable']:
            test_results.append(test)
            continue
        test_summary['number_of_tests'] += 1
        test['result'] = results[idx]
        if test['result']['search_job_duration'] > test_summary['slowest_test']['time']:
            test_summary['slowest_test']['time'] = test['result']['search_job_duration']
            test_summary['slowest_test']['test_id'] = test['metadata']['test_id']
            test_summary['slowest_test']['tokens'] = test['result']['total_tokens_used']
            test_summary['slowest_test']['cost'] = test['result']['total_tokens_cost']
        if test['result']['total_tokens_used'] > test_summary['priciest_test']['tokens']:
            test_summary['priciest_test']['time'] = test['result']['search_job_duration']
            test_summary['priciest_test']['test_id'] = test['metadata']['test_id']
            test_summary['priciest_test']['tokens'] = test['result']['total_tokens_used']
            test_summary['priciest_test']['cost'] = test['result']['total_tokens_cost']
        test['evaluation'] = {}

        test['evaluation']['grade'] = evaluations[idx]['grade']
        test['evaluation']['score'] = evaluations[idx]['score']
        test['evaluation']['grade_explanation'] = evaluations[idx]['grade_explanation']
        test['evaluation']['score_explanation'] = evaluations[idx]['score_explanation']
        test['evaluation']['total_tokens_used'] = evaluations[idx]['total_tokens_used']
        test['evaluation']['total_tokens_cost'] = evaluations[idx]['total_tokens_cost']
        # update score if inverse
        if spec['definition']['inverse_test']:
            test['evaluation']['score'] = 100 - test['evaluation']['score']

        test_results.append(test)

        test_summary['cumulative_score'] += test['evaluation']['score']
        test_summary['search_agent_tokens_used'] += test['result']['total_tokens_used']
        test_summary['search_agent_tokens_cost'] += test['result']['total_tokens_cost']
        test_summary['evaluation_tokens_used'] += test['evaluation']['total_tokens_used']
        test_summary['evaluation_tokens_cost'] += test['evaluation']['total_tokens_cost']

    test_summary['search_agent_tokens_cost'] = round(test_summary['search_agent_tokens_cost'], 2)
    test_summary['evaluation_tokens_cost'] = round(test_summary['evaluation_tokens_cost'], 2)
    test_summary['evaluation_score'] = \
        int(round(test_summary['cumulative_score'] / test_summary['number_of_tests']))
    test_summary['reasoning_llm'] = reasoning_llm_model_name
    test_summary['evaluation_llm'] = evaluation_llm_model_name
    test_summary['search_run_time'] = search_run_time
    test_summary['run_time'] = round((time.time() - start_time), 1)

    evaluation = {'test_results': test_results, 'test_summary': test_summary}

    save_object_to_json_file(evaluation, SCORES_FILE)

    if script_args.verbose:
        for idx, test in enumerate(test_results):
            if not test['definition']['enable']:
                continue
            print(test_result_to_str(test, idx))
    print(f"Info: Saved evaluation results in {SCORES_FILE}")
    print(test_summary_to_str(evaluation['test_summary']))

    log_test_summary_to_file(test_results=test_results,
                             summary=evaluation['test_summary'],
                             script_args=script_args,
                             score_threshold=script_args.score_thresh,
                             max_str=160)

    # Backup test results
    back_up_test_results(script_args)

    if script_args.csv:
        write_results_to_csv_file(test_results)


def log_test_summary_to_file(test_results: dict,
                             summary: dict,
                             script_args: argparse.Namespace,
                             score_threshold: int,
                             max_str: int = 2000):
    """
    Logs test results and a summary to a specified file if the test score is equal to or less than
    the maximum score threshold.

    Parameters:
    test_results (dict): A dictionary that contains the test results.
    summary (dict): A dictionary that contains a summary of the tests.
    score_threshold (int): An integer representing the maximum score threshold.
                           Only test results where test score is equal to or less than this score will be logged.
    max_str (int): Set max string size in printed test results.

    Returns:
    None. The function writes to a file and does not return a value.

    Raises:
    IOError: If there's a problem opening or writing to the file.
    """

    try:
        # If score meets or exceeds max_score_threshold, write test_results and summary to the file
        with open(SUMMARY_FILE, 'w') as f:
            f.write(test_summary_to_str(summary))
            f.write(f"CLI arguments: {script_args}")
            f.write(f"\nTest results where test score is equal to or less than {score_threshold}:\n")
            for idx, test in enumerate(test_results):
                if test['evaluation']['score'] <= score_threshold:
                    f.write(test_result_to_str(test, idx, max_str))

    except IOError as e:
        print(f"Error writing to file: {e}")


def test_result_to_str(test: dict, idx: int, splice: int = 2000):
    grade_explanation = test['evaluation']['grade_explanation']
    score_explanation = test['evaluation']['score_explanation']
    if len(grade_explanation) > splice:
        grade_explanation = grade_explanation[:splice] + " ..."
    if len(score_explanation) > splice:
        score_explanation = score_explanation[:splice] + " ..."
    # sources = ', '.join([
    #     f"{source['source_info'].get('title') or source['source_info'].get('conversation_name')} "
    #     f"({source['source_info']['source']})"
    #     for source in test['result']['sources']
    # ])

    return f"""
Test {idx + 1}:
   Question: ................... {test['definition']['request']}
   Expected Response: .......... {test['definition']['expected_response']}
   Bot Response: ............. {test['result']['answer']}
   Evaluation Grade: ........... {test['evaluation']['grade']}
   Evaluation Score: ........... {test['evaluation']['score']}
   Evaluation Grade Explanation: {grade_explanation}
   Evaluation Score Explanation: {score_explanation}
   Search Time: ................ {test['result']['search_job_duration']}
   Test ID: .................... {test['metadata']['test_id']}
"""


def test_result_to_flat_dict(test: dict) -> dict:

    return {
        'Test ID': test['metadata']['test_id'],
        'Request': test['definition']['request'],
        'Expected Response': test['definition']['expected_response'],
        'Bot Response': test['result']['answer'],
        'Evaluation Grade': test['evaluation']['grade'],
        'Evaluation Score': test['evaluation']['score'],
        'Evaluation Grade Explanation': test['evaluation']['grade_explanation'],
        'Evaluation Score Explanation': test['evaluation']['score_explanation'],
        'Search Time': test['result']['search_job_duration'],
        'Search Tokens Used': test['result']['total_tokens_used'],
        'Search Tokens Cost': round(test['result']['total_tokens_cost'], 3),
        'Eval Tokens Used': test['evaluation']['total_tokens_used'],
        'Eval Tokens Cost': round(test['evaluation']['total_tokens_cost'], 3),
        'Expected Sources': "TBD",
    }


def test_summary_to_str(summary: dict):
    return f"""
______________________________________________________    
FULL EVALUATION SUMMARY:
    Evaluation Score: ........... {summary['evaluation_score']}
    Number of tests: ............ {summary['number_of_tests']}
    Cumulative score: ........... {summary['cumulative_score']}
    Namespace: .................. {summary['namespace']}
    User: ....................... {summary['user']}
    Date and time: .............. {summary['datetime']}
    Reasoning LLM: .............. {summary['reasoning_llm']}
    Evaluation LLM: ............. {summary['evaluation_llm']}
    Search agent tokens used: ... {summary['search_agent_tokens_used']}
    Search agent tokens cost: ... {summary['search_agent_tokens_cost']}
    Evaluation tokens used: ..... {summary['evaluation_tokens_used']}
    Evaluation tokens cost: ..... {summary['evaluation_tokens_cost']}
    Search run time (sec): ...... {summary['search_run_time']}
    Total run time (sec): ....... {summary['run_time']}
    Slowest test (search) ....... {summary['slowest_test']['test_id']}, time: {summary['slowest_test']['time']} secs, \
     tokens: {summary['slowest_test']['tokens']}, cost: ${round(summary['slowest_test']['cost'], 3)}
    Priciest test (search) ...... {summary['priciest_test']['test_id']}, time: {summary['priciest_test']['time']} secs,\
     tokens: {summary['priciest_test']['tokens']}, cost: ${round(summary['priciest_test']['cost'], 3)}
______________________________________________________
"""


def back_up_test_results(script_args: argparse.Namespace):
    """
    This function backs up test results by copying them in the archive directory.

    Args:
        script_args: Script arguments object.
    """

    # Create the archive directory if it does not exist
    os.makedirs(ARCHIVE_DIRECTORY, exist_ok=True)

    # Build a time string to be used in backup directory name. Using digits only for clarity.
    formatted_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Create a subdirectory in the archive directory with the formatted timestamp
    subdirectory = os.path.join(ARCHIVE_DIRECTORY, formatted_time)
    os.makedirs(subdirectory, exist_ok=True)

    files = [SCORES_FILE, SUMMARY_FILE]
    if script_args.csv:
        files.append(TEST_RESULTS_FILE)
    for file_name in files:
        if os.path.isfile(file_name):
            try:
                shutil.copy(file_name, os.path.join(subdirectory, file_name))
            except OSError as e:
                print(f"Error: {e.strerror}")
            except Exception as e:
                print(f"Unexpected error: {e}")
        else:
            print(f'File {file_name} does not exist.')
            continue


def write_results_to_csv_file(test_results: list[dict]):
    """
     Writes a list of dictionaries containing test results to a CSV file.

     Each dictionary in the list should correspond to a test result.

     This function writes each dictionary to a new row in the CSV file.

     The output CSV file is named 'test_results.csv' and is saved in the current directory.
     If a file with this name already exists, it is overwritten.

     Args:
         test_results (list[dict]): A list of dictionaries where each dictionary represents the results of a single test.
    """
    fieldnames = test_result_to_flat_dict(test_results[0]).keys()

    try:
        with open(TEST_RESULTS_FILE, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for test in test_results:
                if not test['definition']['enable']:
                    continue
                writer.writerow(test_result_to_flat_dict(test))
    except Exception as e:
        print(f"Unexpected error: {e}")
        return


def has_overlap(array1, array2):
    """
    This function checks if two Python arrays have any overlap.

    Args:
      array1: The first array.
      array2: The second array.

    Returns:
      True if the arrays have any overlap, False otherwise.

    Example:
      >>> has_overlap([1, 2, 3, 4, 5], [3, 4, 5, 6, 7])
      True
    """

    return any(element in array2 for element in array1)


if __name__ == '__main__':
    asyncio.run(main())