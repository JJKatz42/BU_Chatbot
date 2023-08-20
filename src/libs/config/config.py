"""Loads config vars for app from GCP secret manager or local env."""
import dataclasses
import os
import json
import typing

import dotenv
import requests

import src.libs.logging as logging


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ConfigVarMetadata:
    var_name: str
    is_json: bool = False
    transformer: typing.Optional[callable] = None


# Define global config cache
_config: typing.Union[typing.Dict, None] = None


# Define global registry of metadata about each config var and how it should be processed. Must add these values to .env
# If you want to be able to run the application locally
_config_vars_registry: typing.Union[list[ConfigVarMetadata], None] = None


# Define global project name var so we can cache it from metadata service


class ConfigError(Exception):
    """Custom error class for errors raised by the config library."""


def init(metadata: list[ConfigVarMetadata], local_env_file: str = None):
    """Initialize the config vars registered for this app.

    :param metadata: ConfigVarMetadata describing the config vars the app can access and how to process them
    :param local_env_file: Path to local file (like a .env) containing vars to load into env for use with config
    """
    # Initialize _config_vars_registry with provided metadata arg
    global _config_vars_registry
    _config_vars_registry = metadata

    # If local_env_file was provided trigger loading vars with dotenv
    if local_env_file:
        loaded = dotenv.load_dotenv(local_env_file)
        if not loaded:
            logger.warning(f"No config vars set from {local_env_file}. Does the file exist and have values?")


def is_local_env() -> bool:
    """Returns if the current environment is a local environment based on
    standard local env flag var.

    :return: Flag indicating if this is a local env.
    """
    return os.environ.get("W3B_IS_LOCAL_ENV", "").upper() == "TRUE"


def clear():
    """Invalidate cached config values and configuration."""
    global _config
    _config = None
    global _config_vars_registry
    _config_vars_registry = None


def get(var_name: str, default: typing.Any = None) -> typing.Any:
    """Returns the value from the config of the requested var.

    :param var_name: The value to get from the config
    :param default: Default value to return if var is not found
    :return: The value of the config var or None
    """
    # Config var registry must be initialized before getting config vars
    if not _config_vars_registry:
        raise ConfigError("Cannot call `get` before calling `init` to set config var registry.")

    global _config
    if not _config:
        # Get the environment config no matter what
        environment_config = _get_environment_config()

        # Combine the configs giving preference for secret manager values and set on local cache
        _config = {**environment_config}

    # Return the requested config var value
    return _config.get(var_name, default)


def _get_environment_config() -> typing.Dict:
    """Returns the config vars from the local environment."""
    # Loop through config var registry checking if values are in the environment
    config_vars = {}
    for metadata in _config_vars_registry:
        env_value = os.environ.get(metadata.var_name)

        # If value is in environment process it and set it on config vars to return
        if env_value:
            env_value = _process_config_value(env_value, metadata)
            config_vars[metadata.var_name] = env_value

    return config_vars


def _process_config_value(value: str, metadata: ConfigVarMetadata):
    """Processes the raw config value based on metadata.

    :param value: The value to be processed
    :param metadata: The metadata of the var to be processes
    :return: The processed value
    """
    # If var is marked as JSON parse the JSON string
    if metadata.is_json:
        value = json.loads(value)

    # If var has a transformer defined on metadata run it on the value
    if metadata.transformer:
        value = metadata.transformer(value)

    return value