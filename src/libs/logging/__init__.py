"""Configure logging."""
import logging.config
import logging
import os

# Aliases
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG


def get_log_level_from_env(env_var_name: str, default: str = "INFO") -> str:
    if os.environ.get(env_var_name, "") in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}:
        log_level = os.environ.get(env_var_name)
    else:
        log_level = default

    return log_level


ROOT_LOG_LEVEL_ENV_VAR_NAME = "ROOT_LOG_LEVEL"
ROOT_LOG_LEVEL = get_log_level_from_env("ROOT_LOG_LEVEL", "WARNING")

CHATBOT_LOG_LEVEL_ENV_VAR_NAME = "CHATBOT_LOG_LEVEL"
CHATBOT_LOG_LEVEL = get_log_level_from_env("CHATBOT_LOG_LEVEL")

CHATBOT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s][%(filename)s:%(lineno)d][%(process)d - %(processName)s][%(funcName)s][%(levelname)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "[%(asctime)s][%(filename)s:%(lineno)d][%(process)d - %(processName)s][%(funcName)s]%(log_color)s[%(levelname)s]%(reset)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "colored",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "root": {
            "handlers": ["default"],
            "level": ROOT_LOG_LEVEL,
        },
        "local_webapp": {
            "level": CHATBOT_LOG_LEVEL,
        },
        "src": {
            "level": CHATBOT_LOG_LEVEL,
        },
        "scripts": {
            "level": CHATBOT_LOG_LEVEL,
        },
        "__main__": {
            "level": CHATBOT_LOG_LEVEL,
        },
        "local_chatbot_webapp_demo_local_API": {
            "level": CHATBOT_LOG_LEVEL,
        },
        "testing": {
            "level": CHATBOT_LOG_LEVEL,
        }
    },
}

logging.config.dictConfig(CHATBOT_LOGGING_CONFIG)

getLogger = logging.getLogger
