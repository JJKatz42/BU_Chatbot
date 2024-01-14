import dataclasses
import enum
import json
import typing
import uuid

import pydantic

import src.libs.search.search_agent.openai_schema as openai_schema


# Search Engine interface schemas
class SearchEngineClassNames(str, enum.Enum):
    Document = "Webpage"


class TextContentMetadataMode(str, enum.Enum):
    ALL = enum.auto()
    EMBED = enum.auto()
    LLM = enum.auto()
    NONE = enum.auto()


class TextContent(pydantic.BaseModel):
    """Database class representing a text content (chunk) in a document or thread."""

    object_id: uuid.UUID
    index: int = pydantic.Field(default=0)
    text: str = pydantic.Field(default="")
    metadata_json: str = pydantic.Field(default="{}")

    @property
    def metadata(self) -> dict:
        return json.loads(self.metadata_json)

    def get_content(self, metadata_mode: TextContentMetadataMode = TextContentMetadataMode.NONE) -> str:
        """Get object content."""
        return self.text


class TextContentWithScore(pydantic.BaseModel):
    """Text content returned in search results, with relevance scores."""

    text_content: TextContent
    embedding_relevance: float
    cross_encoder_relevance: float | None = pydantic.Field(default=None)


class MimeType(str, enum.Enum):
    """Enum of MIME types supported by the Search Engine."""

    TEXT = "text/plain"
    MARKDOWN = "text/markdown"


class SourceIntegration(str, enum.Enum):
    """Enum of source integrations supported by the Search Engine."""

    DIRECT_UPLOAD = "direct_upload"


class WebpageSourceInfo(pydantic.BaseModel):
    """Information about document returned in search results."""

    object_id: uuid.UUID
    url: str
    mime_type: MimeType


SourceInfo = WebpageSourceInfo


class SearchResult(pydantic.BaseModel):
    """A search result."""

    document_source_info: WebpageSourceInfo | None = pydantic.Field(default=None)
    text_contents: list[TextContentWithScore]
    score: float

    @property
    def source_info(self) -> SourceInfo | None:
        """The source info of the search result."""
        return self.document_source_info

    def __eq__(self, other: "SearchResult"):
        """Compare two search results."""
        source_info = self.document_source_info
        other_source_info = other.document_source_info
        return source_info == other_source_info


class SearchReRankingConfig(pydantic.BaseModel):
    """Configuration for re-ranking search results."""

    cross_encoder_weight: float = pydantic.Field(default=1.0, ge=0.0, le=1.0)
    page_rank_weight: float = pydantic.Field(default=0.0, ge=0.0, le=1.0)
    recency_weight: float = pydantic.Field(default=0.0, ge=0.0, le=1.0)

    @pydantic.root_validator
    def check_conflicts(cls, values):
        """Check that the weights sum to 1."""
        if sum(values.values()) != 1.0:
            raise ValueError("SearchReRankingConfig weights must sum to 1.")
        return values


class SearchEngineQueryConfig(pydantic.BaseModel):
    """Configuration for a search engine query."""

    re_ranking_config: SearchReRankingConfig | None = pydantic.Field(
        default=SearchReRankingConfig(cross_encoder_weight=1.0),
    )
    min_embedding_relevance: float = pydantic.Field(default=0, ge=0, le=1)
    min_cross_encoder_relevance: float = pydantic.Field(default=0, ge=0, le=1)
    autocut: int | None = pydantic.Field(default=3, ge=1)
    num_sources_limit: int | None = pydantic.Field(default=None, ge=1)
    num_text_content_tokens_limit: int | None = pydantic.Field(default=None, ge=1)
    vector_to_keyword_weight: float = pydantic.Field(default=0.8, ge=0.0, le=1.0)
    custom_filters: dict | None = pydantic.Field(default=None)
    enable_query_reformulation: bool = pydantic.Field(default=False)
    metadata_keyword_search_power: int = pydantic.Field(default=1)
    content_keyword_search_power: int = pydantic.Field(default=1)
    source_integrations_filter: list[SourceIntegration] | None = pydantic.Field(default=None)


class SearchEngineQuery(pydantic.BaseModel):
    """A search query to the search engine."""

    query_str: str
    config: SearchEngineQueryConfig = pydantic.Field(default_factory=SearchEngineQueryConfig)


class Query(openai_schema.OpenAISchema):
    """Class representing a single query in a query plan."""

    id: int = pydantic.Field(..., description="Unique id of the query.")
    question: str = pydantic.Field(
        ...,
        description="Question we are asking using a question answer system. "
        "If there are multiple queries, this query can only be executed "
        "when all dependant sub-queries have been answered.",
    )
    sub_queries: list[int] = pydantic.Field(
        default_factory=list,
        description="List of the IDs of sub-queries that need to be answered "
        "before we can answer this question. Use a sub-query when "
        "anything may be unknown and we need to ask multiple questions "
        "to get the answer. Dependencies must only be other queries.",
    )


@dataclasses.dataclass
class QueryResult:
    """Container for results of a query."""

    query: Query
    result: "GenerateAnswer"
    sources: list[SearchResult]


@dataclasses.dataclass
class QueryResults:
    """Container for list of query results."""

    results: list[QueryResult]


class QueryPlan(openai_schema.OpenAISchema):
    """Container class representing a tree of queries and sub-queries. \
Make sure every query is in the tree and every query is done only once."""

    query_graph: list[Query] = pydantic.Field(
        ...,
        description="List of the queries and sub-queries that need to be done to complete the main query. "
        "Consists of the main query and its dependencies.",
    )

    def get_root_query_id(self) -> int:
        """Get the ID for query that sits at root of the computational graph.

        Returns:
            ID of the query
        """
        candidate_root_queries = set([query.id for query in self.query_graph])
        for query in self.query_graph:
            for sub_query_id in query.sub_queries:
                try:
                    candidate_root_queries.remove(sub_query_id)
                except KeyError:
                    pass

        if len(candidate_root_queries) != 1:
            raise ValueError("There can only be 1 root query")

        return candidate_root_queries.pop()

    def insert_at_root(self, query_str: str, ignore_exists_check: bool = True):
        """Insert a query at the root of the query plan's computational graph.

        Args:
            query_str: The query to insert
            ignore_exists_check: If True, ignore the check that the query is not already in the graph

        Returns:
            None, updates the graph in place
        """
        max_query_id = 0
        question_already_at_root = False
        candidate_top_level_queries = set([query.id for query in self.query_graph])
        for query in self.query_graph:
            # If the query is already at the root of the graph, we don't need to insert it
            if query.question.lower().rstrip("?") == query_str.lower().rstrip("?"):
                try:
                    if self.get_root_query_id() == query.id:
                        question_already_at_root = True
                except ValueError:
                    pass

            max_query_id = max(query.id, max_query_id)

            for sub_query_id in query.sub_queries:
                try:
                    candidate_top_level_queries.remove(sub_query_id)
                except KeyError:
                    pass

        if question_already_at_root and not ignore_exists_check:
            return

        new_root_query = Query(id=max_query_id + 1, question=query_str, sub_queries=list(candidate_top_level_queries))

        self.query_graph.append(new_root_query)

    def get_execution_order(self) -> list[int]:
        """Returns the order in which the queries should be executed using topological sort.

        Args:
            Return list of query IDs in topological order
        """
        tmp_dep_graph = {item.id: set(item.sub_queries) for item in self.query_graph}

        def topological_sort(dep_graph: dict[int, set[int]]) -> typing.Generator[set[int], None, None]:
            while True:
                ordered = set(item for item, dep in dep_graph.items() if len(dep) == 0)
                if not ordered:
                    break
                yield ordered
                dep_graph = {item: (dep - ordered) for item, dep in dep_graph.items() if item not in ordered}
            if len(dep_graph) != 0:
                raise ValueError(
                    f"Circular dependencies exist among these items: "
                    f"{{{', '.join(f'{key}:{value}' for key, value in dep_graph.items())}}}"
                )

        result = []
        for d in topological_sort(tmp_dep_graph):
            result.extend(sorted(d))
        return result


class SearchMode(str, enum.Enum):
    semantic = "semantic"
    hybrid = "hybrid"
    keyword = "keyword"


class SearchParameters(openai_schema.OpenAISchema):
    """Class representing a queries search parameters."""

    top_k: int = pydantic.Field(default=3, le=10, ge=1, description="Number of most relevant search results to return.")
    mode: SearchMode = pydantic.Field(
        default=SearchMode.hybrid,
        description="The search mode can be semantic, keyword or both (hybrid). "
        "Semantic searches are done by embedding the search query text "
        "into a vector and doing a KNN similarity search against the vectors of "
        "all possible results to get top_k results. "
        "Keyword searches are done by using the BM25 ranking function to get top_k results. "
        "Hybrid searches uses a combination of semantic and keyword search to get top_k results.",
    )
    alpha: float = pydantic.Field(
        default=0.75,
        le=1.0,
        ge=0.0,
        description="You can use the alpha parameter for hybrid search mode to tune the weighting "
        "of keyword (bm25) vs semantic (vector) search results. An alpha of 0.5 would weight "
        "semantic and keyword searches equally, 0 would be a pure keyword search and "
        "1 would be a pure semantic search.",
    )

    class Config:
        use_enum_values = True


class GenerateAnswer(openai_schema.OpenAISchema):
    """Generate a helpful, accurate and concise answer to the employees question."""

    answer: str = pydantic.Field(
        default=..., description="Helpful, accurate and concise answer to the employees question."
    )
    excerpt: str | None = pydantic.Field(
        default=None,
        description="Short snippet or quote from the sources that contains the answer. "
        "If there is no such excerpt, this field is null.",
    )


class SearchAgentFeatures(enum.Enum):
    """Feature flags for the search agent."""

    # Implemented
    AUTO_SEARCH_PARAMETER_GEN = "AUTO_SEARCH_PARAMETER_GEN"
    QUERY_PLANNING = "QUERY_PLANNING"
    RE_RANKING = "RE_RANKING"
    SEARCH_QUERY_REFORMULATION = "SEARCH_QUERY_REFORMULATION"
    ADVANCED_LLM_SPREADSHEET_QA = "ADVANCED_LLM_SPREADSHEET_QA"
    # Not implemented
    AUTO_SEARCH_FILTER_GEN = "AUTO_SEARCH_FILTER_GEN"
    ADAPTIVE_QUERY_PLANNING = "ADAPTIVE_QUERY_PLANNING"


@dataclasses.dataclass
class Context:
    """Container for context used by Agent to run a query."""

    application_user_id: str = None
    organization_name: str = None
    sources: list[SearchResult] = None


@dataclasses.dataclass
class AgentResult:
    """Container for result of running an Agent on a query."""

    answer: GenerateAnswer
    sources: list[SearchResult]

    # Debug details
    context: Context
    query: str
    query_plan: QueryPlan
    query_plan_results: dict[int:QueryResult]
    features: list[SearchAgentFeatures]
    total_tokens_used: int
    total_tokens_cost: int