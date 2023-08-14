# BUChatbot 🧠
Main repo for all chatbot beta source code.

This project consists of 4 main subdirectories:

- `BU_info_db` - Source code for storing BU information in and searching through the Weaviate database
- `user_info_db` - Source code for handling user interactions with the product
- `test_crawler` - Scrapy crawler for storing webpages
- `webapp_demo` - demonstration of the chatbot using a local webapp


## Getting Started with Local Development
### Install Python 3.10.11
1. Install [pyenv](https://github.com/pyenv/pyenv)
2. Install python 3.10.11 `pyenv install 3.10.11`
3. Create virtual environment `pyenv virtualenv 3.10.11 BUChatbot`
4. Activate virtual environment `source ~/.pyenv/versions/3.10.11/envs/BUChatbot/bin/activate`
5. (optional) Configure pyenv for terminal activation.  Add `eval "$(pyenv init --path)"` to `~/.zprofile`, as well as
`eval "$(pyenv init -)"` and `eval "$(pyenv virtualenv-init -)"` to `~/.zshrc`.  Then you can run `pyenv activate BUChatbot`
5. Configure IDE python interpreter to point to `/Users/<your user>/.pyenv/versions/3.10.11/envs/BUChatbot/bin/python`
