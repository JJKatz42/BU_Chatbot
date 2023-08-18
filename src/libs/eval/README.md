# Evaluation Framework README

This Python framework performs **BUChatbot** testing and evaluation tasks using Agents and LLMs. The script supports various flags and test definition files to customize the execution. Below are examples of how to run the script, an explanation of the flags, and an overview of the definition files.

## Examples

To run the script with default parameters, use the following command:

```shell
python evaluate.py
```

To specify a custom environment file and test file, use the `--env-file` and `--test-file` flags, respectively:
```shell
python script.py --env-file=myenv.env --test-file=custom_tests.json
```

You can enable verbose output by using the `--verbose` flag:
```shell
python script.py --verbose
```

You can sub-select a specific test(s) by test-ids `--test-ids` flag:
```shell
python script.py --test-ids tid-11 tid-23
```

## Files and Directories
Directories
* `definitions` is a directory containing test files 
* `archive` is a directory containing archives of previous test runs
* `schema` is a directory containing schema software modules and JSON schema file. 

Each test run produces two output files:  
* `summary.txt` has a test summary
* `scores.json` has a comprehensive set of inputs, search results, and evaluation information

See the **scores.json** section below for the specification.

## Flags

The script supports the following flags:

- `--env-file`: Specifies the path to a local `.env` file containing configuration values. Default: `.env`
- `--test-file`: Specifies the test definitions file. Default: `/Users/jonahkatz/Desktop/BU_Chatbot/BU_info_db/eval/test_registry.json`
- `--reasoning-llm`: Specifies the name of the Reasoning LLM model. Default: `gpt-3.5-turbo-0613`
- `--evaluation-llm`: Specifies the name of the Evaluation LLM model. Default: `gpt-4-0613`
- `--search-agent-features`: Specifies the list of Search Agent features. Default: `CROSS_ENCODER_RE_RANKING, QUERY_PLANNING`
- `--score-thresh`: Specifies the score threshold. Test results with a score equal to or less than this threshold will be logged to the `summary.txt` file. Default: `100`
- `--verbose`: Enables verbose output to stdout.
- `--test-ids` Allows user to specify specific test(s) from the test registry
- `--csv` Enables writing of test results to CSV file: test_results.csv
- `--tags` Selects tests that have at least one of specified tags. Default: no filtering

## Test Definition Files

The script uses definition files to define test cases. These files are in JSON format and contain an array of test definitions. 


## Results File: scores.json Specification
### JSON structure
The comprehensive test results file (`scores.json`) follows the following structure:
```json
{
  "test_results": [
    {
      "definition": { ... },
      "metadata": { ... },
      "result": { ... },
      "evaluation": { ... }
    },
    {
      "definition": { ... },
      "metadata": { ... },
      "result": { ... },
      "evaluation": { ... }
    }
  ],
  "test_summary": {
    "evaluation_score": 50,
    "search_agent_tokens_used": 6391,
    "search_agent_tokens_cost": 0.01,
    "evaluation_tokens_used": 836,
    "evaluation_tokens_cost": 0.03,
    "number_of_tests": 2,
    "cumulative_score": 100,
    "namespace": "jonah_da_bomb",
    "user": "jonahkatz",
    "datetime": "2023-07-12T12:44:08.628210",
    "reasoning_llm": "gpt-3.5-turbo-0613",
    "evaluation_llm": "gpt-4-0613"
    "run_time": "49.2"
  }
}
```
Please note that the placeholders { ... } indicate that the specific content for the properties should be added according to your test results.

### Test Results
The `test_results` field is an array containing objects representing individual test cases. Each test case has the following properties:

* `definition`: Represents the definition or input of the test.
* `metadata`: Contains the metadata associated with the file
* `result`: Represents the generated result by the SearchAgent.
* `evaluation`: Represents the evaluation or analysis of the generated result

### Test Summary
The `test_summary` field contains summarized information about the tests performed. It includes the following properties:

* `evaluation_score`: Represents the overall evaluation score of the tests.
* `search_agent_tokens_used`: Represents the number of tokens the search agent consumed.
* `search_agent_tokens_cost`: Represents the cost (in tokens) incurred by the search agent.
* `evaluation_tokens_used`: Represents the number of tokens used for evaluation.
* `evaluation_tokens_cost`: Represents the cost (in tokens) incurred for evaluation.
* `number_of_tests`: Represents the total number of tests performed.
* `cumulative_score`: Represents the cumulative score achieved across all tests.
* `namespace`: Represents the namespace or project identifier.
* `user`: Represents the username of the test executor.
* `datetime`: Represents the date and time when the tests were conducted.
* `reasoning_llm`: Represents the version of the language model used for reasoning.
* `evaluation_llm`: Represents the version of the language model used for evaluation.
* `run_time`: Represents the total execution time


