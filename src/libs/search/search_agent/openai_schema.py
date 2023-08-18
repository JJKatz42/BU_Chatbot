import copy
import json

import langchain.schema
import pydantic 


class OpenAISchemaException(Exception):
    """Exception class for OpenAISchema"""


class OpenAISchema(pydantic.BaseModel):
    @classmethod
    @property
    def openai_schema(cls) -> dict:
        """Convert Pydantic model to OpenAI Function spec.

        Returns:
            Dictionary adhering to OpenAI Function spec
        """
        # Convert Pydantic model to JSON schema format
        schema = copy.deepcopy(cls.schema())
        # Remove title from JSON schema (the Pydantic model's class name)
        title = schema.pop("title")
        # Remove the description from JSON schema (the Pydantic model's class docstring)
        description = schema.pop("description")
        # Remove any titles (Pydantic model class name) recursively in the case that this model refers to other
        # pydantic models.
        _remove_a_key(schema, "title")
        return {
            "name": title,
            "description": description,
            "parameters": schema,
        }

    @classmethod
    def from_response(cls, message: langchain.schema.BaseMessage, throw_error=True) -> "OpenAISchema":
        """Load Pydantic model from OpenAI function call.

        Args:
            message: The LLMs message containing function call
            throw_error: Raise exception if the expected function call is not in the LLMs message.

        Returns:
            Pydantic model object populated with data from the OpenAI function call
        """
        if throw_error:
            if "function_call" not in message.additional_kwargs:
                raise OpenAISchemaException("No function call detected")
            if message.additional_kwargs["function_call"]["name"] != cls.openai_schema["name"]:
                raise OpenAISchemaException(
                    f"Function called by OpenAI {message.additional_kwargs['function_call']['name']} "
                    f"does not match {cls.openai_schema['name']}"
                )

        function_call = message.additional_kwargs["function_call"]
        arguments = json.loads(function_call["arguments"])
        return cls(**arguments)


def _remove_a_key(d, remove_key) -> None:
    """Remove a key from a dictionary recursively"""
    if isinstance(d, dict):
        for key in list(d.keys()):
            if key == remove_key:
                del d[key]
            else:
                _remove_a_key(d[key], remove_key)