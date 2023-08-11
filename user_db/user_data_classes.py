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
    id: str
    user_id: str
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
                    "name": "message_id",
                    "dataType": ["text"],
                },
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
            "message_id": self.id,
            "query_str": self.query_str,
            "bad_query_tag": self.is_bad_query,
            "created_time": self.created_time,
        }


@dataclasses.dataclass
class BotMessage(WeaviateObject):
    id: str
    user_id: str
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
                    "name": "message_id",
                    "dataType": ["text"],
                },
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
            "message_id": self.id,
            "is_liked": self.is_liked,
            "response_str": self.response_str,
            "created_time": self.created_time,
        }


@dataclasses.dataclass
class Conversation(WeaviateObject):
    id: str
    user_id: str
    messages: List[UserMessage, BotMessage]

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
                    "name": "conversation_id",
                    "dataType": ["text"],
                },
                {
                    "name": "messages",
                    "dataType": [f"List[{UserMessage.weaviate_class_name(namespace=namespace)}, {BotMessage.weaviate_class_name(namespace=namespace)}]"]
                },
                {
                    "name": "hasUser",
                    "dataType": [User.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5((self.id + str(self.messages)).encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "conversation_id": self.id,
        }


class ProfileInformation(WeaviateObject):
    id: str
    user_id: str
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
                    "name": "_id",
                    "dataType": ["text"],
                },
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
        hex_string = hashlib.md5((self.id + str(self.value) + str(self.value)).encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "_id": self.id,
            "key": self.key,
            "information": self.value
        }


@dataclasses.dataclass
class User(WeaviateObject):
    id: str
    gmail: str
    password_hash: str
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
                    "name": "user_id",
                    "dataType": ["text"],
                },
                {
                    "name": "gmail",
                    "dataType": ["text"],
                },
                {
                    "name": "password_hash",
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
        hex_string = hashlib.md5(self.id.encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "user_id": self.id,
            "gmail": self.gmail,
            "password_hash": self.password_hash,
            "created_time": self.created_time,
        }


class CrossReference:
    def __init__(self, from_class: str, from_uuid: str, from_property: str, to_class: str, to_uuid: str):
        self.from_class = from_class
        self.from_uuid = from_uuid
        self.from_property = from_property
        self.to_class = to_class
        self.to_uuid = to_uuid
