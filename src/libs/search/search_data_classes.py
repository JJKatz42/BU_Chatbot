import dataclasses

import pydantic

from src.libs.storage import storage_data_classes as storage_data_classes

# Redeclare Source and MimeType in local scope, so it can be imported from here directly in search modules
MimeType = storage_data_classes.MimeType


@dataclasses.dataclass
class WebpageSourceInfo:
    id: str
    title: str
    num_references: int
    mime_type: MimeType


SourceInfo = WebpageSourceInfo


@dataclasses.dataclass
class SearchResult:
    """Container for Search Engine search results"""
    text: str
    url: str
    score: float | None = None
    source_info: SourceInfo | None = None


@dataclasses.dataclass
class Answer:
    answer: str
    search_results: list[SearchResult]


@dataclasses.dataclass
class Summarization:
    summary: str
    search_results: list[SearchResult]