import dataclasses
import hashlib
import uuid
import datetime
import dateutil
from dateutil import parser
from typing import List, Tuple

class WeaviateObject:
    @classmethod
    def weaviate_class_name(cls, namespace: str) -> str:
        return f"{namespace}_{cls.__name__}"

    @property
    def weaviate_id(self):
        return None

    def get_weaviate_datetime_values(self, var_names: list[str]):
        datetime_vars = {}
        for var_name in var_names:
            value = getattr(self, var_name)

            if isinstance(value, str) and value.isnumeric():
                value = float(value)

            if isinstance(value, (int, float)):
                value = datetime.datetime.fromtimestamp(
                    value, datetime.timezone.utc
                ).isoformat(timespec="microseconds")

            datetime_vars[var_name] = value

        return datetime_vars

@dataclasses.dataclass
class UserMessage(WeaviateObject):
    query_str: str
    is_bad_query: bool
    created_time: int | float | str

    @classmethod
    def weaviate_class_schema(cls, namespace: str):
        return {
            "class": cls.weaviate_class_name(namespace=namespace),
            "vectorizer": "none",
            "vectorIndexConfig": {
                "skip": True
            },
            "invertedIndexConfig": {
                "indexNullState": True,
            },
            "properties": [
                {
                    "name": "is_good_query",
                    "dataType": ["bool"],
                },
                {
                    "name": "query_str",
                    "dataType": ["text"],
                },
                {
                    "name": "created_time",
                    "dataType": ["date"],
                },
                {
                    "name": "hasConversation",
                    "dataType": [Conversation.weaviate_class_name(namespace=namespace)],
                },
                {
                    "name": "hasResponse",
                    "dataType": [BotMessage.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5(self.query_str.encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "query_str": self.query_str,
            "bad_query_tag": self.is_bad_query,
            "created_time": self.created_time,
        }


@dataclasses.dataclass
class BotMessage(WeaviateObject):
    response_str: str
    is_liked: bool
    created_time: int | float | str

    @classmethod
    def weaviate_class_schema(cls, namespace: str):
        return {
            "class": cls.weaviate_class_name(namespace=namespace),
            "vectorizer": "none",
            "vectorIndexConfig": {
                "skip": True
            },
            "invertedIndexConfig": {
                "indexNullState": True,
            },
            "properties": [
                {
                    "name": "response_str",
                    "dataType": ["text"],
                },
                {
                    "name": "is_liked",
                    "dataType": ["bool"],
                },
                {
                    "name": "created_time",
                    "dataType": ["date"],
                },
                {
                    "name": "hasConversation",
                    "dataType": [Conversation.weaviate_class_name(namespace=namespace)],
                },
                {
                    "name": "hasQuery",
                    "dataType": [UserMessage.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5(self.response_str.encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "is_liked": self.is_liked,
            "response_str": self.response_str,
            "created_time": self.created_time,
        }


@dataclasses.dataclass
class Conversation(WeaviateObject):
    messages: List[UserMessage | BotMessage]
    created_time: int | float | str

    @classmethod
    def weaviate_class_schema(cls, namespace: str):
        return {
            "class": cls.weaviate_class_name(namespace=namespace),
            "vectorizer": "none",
            "vectorIndexConfig": {
                "skip": True
            },
            "invertedIndexConfig": {
                "indexNullState": True,
            },
            "properties": [
                {
                    "name": "messages",
                    "dataType": [
                        UserMessage.weaviate_class_name(namespace=namespace),
                        BotMessage.weaviate_class_name(namespace=namespace)
                    ]
                },
                {
                    "name": "hasUser",
                    "dataType": [User.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        return uuid.uuid4()

    def to_weaviate_object(self) -> dict:
        return {
            "messages": self.messages,
            "created_time": self.created_time,
        }


class ProfileInformation(WeaviateObject):
    key: str
    value: str

    @classmethod
    def weaviate_class_schema(cls, namespace: str):
        return {
            "class": cls.weaviate_class_name(namespace=namespace),
            "vectorizer": "none",
            "vectorIndexConfig": {
                "skip": True
            },
            "invertedIndexConfig": {
                "indexNullState": True,
            },
            "properties": [
                {
                    "name": "key",
                    "dataType": ["text"],
                },
                {
                    "name": "value",
                    "dataType": ["text"],
                },
                {
                    "name": "hasUser",
                    "dataType": [User.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5((str(self.key) + str(self.value)).encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "key": self.key,
            "value": self.value
        }


@dataclasses.dataclass
class User(WeaviateObject):
    gmail: str
    created_time: int | float | str
    profile_information: list[ProfileInformation]
    conversations: list[Conversation]

    @classmethod
    def weaviate_class_schema(cls, namespace: str):
        return {
            "class": cls.weaviate_class_name(namespace=namespace),
            "vectorizer": "none",
            "vectorIndexConfig": {
                "skip": True
            },
            "invertedIndexConfig": {
                "indexNullState": True,
            },
            "properties": [
                {
                    "name": "gmail",
                    "dataType": ["text"],
                },
                {
                    "name": "created_time",
                    "dataType": ["date"],
                },
                {
                    "name": "hasProfileInformation",
                    "dataType": [ProfileInformation.weaviate_class_name(namespace=namespace)]
                },
                {
                    "name": "hasConversation",
                    "dataType": [Conversation.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5(self.gmail.encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "gmail": self.gmail,
            "created_time": self.created_time,
        }


class CrossReference:
    def __init__(self, from_class: str, from_uuid: str, from_property: str, to_class: str, to_uuid: str):
        self.from_class = from_class
        self.from_uuid = from_uuid
        self.from_property = from_property
        self.to_class = to_class
        self.to_uuid = to_uuid
