# Setup
## Install 3rd party requirements:
```shell
pip install -r 3rdparty/python/requirements.txt
```
## Configs
- `DATA_NAMESPACE`: Defaults to "Default". This is a namespace used to isolate data in Weaviate, so that you can run multiple experiments storing/indexing data without worrying about overwriting data from other experiments.
- `WEAVIATE_URL`: This is the remote Weavitate instance URL to connect to.
- `WEAVIATE_API_KEY`. This is the API key used for authenticating to remote Weaviate instance.
- `OPENAI_API_KEY`: OpenAI API key
- `COHERE_API_KEY`: Cohere API key (for rerankings)

Create .env file with config values:
```
OPENAI_API_KEY=Jonah will give
DATA_NAMESPACE=Jonah_da_bomb (put something else here, it is just an example)
WEAVIATE_URL=https://chatbot-dev-ebe7avc4.weaviate.network (put something else here, it is just an example)
WEAVIATE_API_KEY=Jonah will give
COHERE_API_KEY=Jonah will give
```

# Run the script
## See how to use the script
```
python BU_info_db/search/demo2.py --help
```
## Examples
### Build search indexes
```
python BU_info_db/search/demo2.py build-indexes --env-file /Users/jonahkatz/Desktop/BU_Chatbot/BU_info_db/search/.env
```
### Run a search
```
python BU_info_db/search/demo2.py search "How do I apply for financial aid?" --env-file /Users/jonahkatz/Desktop/BU_Chatbot/BU_info_db/search/.env
```
### Ask a question
```
python BU_info_db/search/demo2.py ask "Which dining halls are open right now" --env-file /Users/jonahkatz/Desktop/BU_Chatbot/BU_info_db/search/.env
```
### Summarize information
```
python BU_info_db/search/demo2.py summarize "requirements for computer engineering" --top-k=10 --env-file /Users/jonahkatz/Desktop/BU_Chatbot/BU_info_db/search/.env
```
