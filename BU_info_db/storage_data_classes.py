import dataclasses
import datetime
import dateutil
import enum
import hashlib
import uuid


class MimeType(str, enum.Enum):
    TEXT = "text/plain"
    MARKDOWN = "text/markdown"


class WeaviateObject:
    @classmethod
    def weaviate_class_name(cls, namespace: str):
        return f"{namespace}_{cls.__name__}"

    @property
    def weaviate_id(self):
        return None

    # def get_weaviate_datetime_values(self, var_names: list[str]):
    #     datetime_vars = {}
    #     for var_name in var_names:
    #         value = getattr(self, var_name)

    #         # Handle converting cases where a system may have returned a UNIX timestamp as a JSON string
    #         if isinstance(value, str) and value.isnumeric():
    #             value = int(float(value))

    #         # If the value is an int, convert to an ISO timestamp string
    #         if isinstance(value, int):
    #             value = datetime.datetime.fromtimestamp(
    #                 value, datetime.timezone.utc
    #             ).isoformat(timespec="microseconds")

    #         datetime_vars[var_name] = value

    #     return datetime_vars


@dataclasses.dataclass
class TextContent(WeaviateObject):
    text: str
    index: int
    vector: list[float] | None = None
    metadata: dict = dataclasses.field(default_factory=dict)

    def __lt__(self, other):
        # To enable sorting
        return self.index < other.index

    @property
    def metadata_str(self):
        return "\n".join(f'{k}: {v}' for k, v in self.metadata.items())

    @classmethod
    def weaviate_class_schema(cls, namespace: str):
        # TODO: Automate the generation of this based on dataclass
        return {
            "class": cls.weaviate_class_name(namespace=namespace),
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {
                    "model": "ada",
                    "modelVersion": "002",
                    "type": "text"
                },
                "generative-openai": {
                    "model": "gpt-3.5-turbo",
                    "temperatureProperty": 0.0,
                }
            },
            "properties": [
                {
                    "name": "text",
                    "dataType": ["text"],
                },
                {
                    "name": "index",
                    "dataType": ["int"],
                },
                {
                    "name": "contentOf",
                    "dataType": [
                        Webpage.weaviate_class_name(namespace=namespace)
                    ],
                }
            ]
        }

    def to_weaviate_object(self) -> dict:
        return {
            "text": f"{self.metadata_str}\n{self.text}" if self.metadata else self.text,
            "index": self.index
        }


@dataclasses.dataclass
class Webpage(WeaviateObject):
    id: str
    url: str
    mime_type: MimeType
    html_content: str
    text_contents: list[TextContent]

    @classmethod
    def weaviate_class_schema(cls, namespace: str):
        # TODO: Automate the generation of this based on dataclass
        return {
            "class": cls.weaviate_class_name(namespace=namespace),
            "vectorizer": "ref2vec-centroid",
            "vectorIndexConfig": {
                "efConstruction": 32,
                "maxConnections": 16
            },
            "moduleConfig": {
                "ref2vec-centroid": {
                    "referenceProperties": ["textContents"],
                    "method": "mean"
                }
            },
            "invertedIndexConfig": {
                "indexNullState": True,
            },
            "properties": [
                {
                    "name": "webpage_id",
                    "dataType": ["text"],
                },
                {
                    "name": "url",
                    "dataType": ["text"],
                },
                # {
                #     "name": "createdTime",
                #     "dataType": ["date"],
                # },
                # {
                #     "name": "updatedTime",
                #     "dataType": ["date"],
                # },
                {
                    "name": "html_content",
                    "dataType": ["text"],
                },
                {
                    "name": "textContents",
                    "dataType": [TextContent.weaviate_class_name(namespace=namespace)],
                }
            ]
        }

    @property
    def weaviate_id(self):
        hex_string = hashlib.md5(self.id.encode()).hexdigest()
        return uuid.UUID(hex=hex_string)

    def to_weaviate_object(self) -> dict:
        # Handle converting datetime values as necessary
        # datetime_values = self.get_weaviate_datetime_values(["created_time", "updated_time"])

        return {
            "webpage_id": self.id,
            "url": self.url,
            "mimeType": self.mime_type,
            "html_content": self.html_content,
            # "createdTime": datetime_values["created_time"],
            # "updatedTime": datetime_values["updated_time"],
        }


@dataclasses.dataclass
class CrossReference:
    from_uuid: str
    from_class: str
    from_property: str
    to_uuid: str
    to_class: str