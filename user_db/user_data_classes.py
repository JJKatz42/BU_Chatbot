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
class User(WeaviateObject):
    id: str
    gmail: str
    password_hash: str
    bad_queries_count: int
    total_queries_count: int
    profile_information: 'ProfileInformation'
    conversation: 'Conversation'

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
                    "name": "bad_queries_count",
                    "dataType": ["int"],
                },
                {
                    "name": "total_queries_count",
                    "dataType": ["int"],
                },
                {
                    "name": "profile_information",
                    "dataType": [ProfileInformation.weaviate_class_name(namespace=namespace)]
                },
                {
                    "name": "conversation",
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
            "bad_queries_count": self.bad_queries_count,
            "total_queries_count": self.total_queries_count,
        }

@dataclasses.dataclass
class Conversation(WeaviateObject):
    id: str
    user_id: str
    messages: List[Tuple['UserQuery', 'BotResponse']]

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
                    "name": "messages",
                    "dataType": [f"Tuple[{UserQuery.weaviate_class_name(namespace=namespace)}, {BotResponse.weaviate_class_name(namespace=namespace)}]"],
                },
                {
                    "name": "hasUser",
                    "dataType": [User.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5((self.user_id + str(self.messages)).encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "user_id": self.user_id
        }

@dataclasses.dataclass
class UserQuery(WeaviateObject):
    id: str
    user_id: str
    query: str
    created_time: datetime.datetime

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
                    "name": "user_id",
                    "dataType": ["text"],
                },
                {
                    "name": "query",
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
                    "dataType": [BotResponse.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5(self.query.encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "message_id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "created_time": self.created_time,
        }

@dataclasses.dataclass
class BotResponse(WeaviateObject):
    id: str
    user_id: str
    response: str
    created_time: datetime.datetime

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
                    "name": "user_id",
                    "dataType": ["text"],
                },
                {
                    "name": "response",
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
                    "name": "hasQuery",
                    "dataType": [UserQuery.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5(self.response.encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        return {
            "message_id": self.id,
            "user_id": self.user_id,
            "response": self.response,
            "created_time": self.created_time,
        }

class ProfileInformation(WeaviateObject):
    # TODO: add support for user profile information
    pass

class CrossReference:
    def __init__(self, from_class: str, from_uuid: str, from_property: str, to_class: str, to_uuid: str):
        self.from_class = from_class
        self.from_uuid = from_uuid
        self.from_property = from_property
        self.to_class = to_class
        self.to_uuid = to_uuid
