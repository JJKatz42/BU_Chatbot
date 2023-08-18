import dataclasses
import typing

import pydantic

from src.libs.search.search_agent import openai_schema as openai_schema
import src.libs.search.weaviate_search_engine as weaviate_search_engine


@dataclasses.dataclass
class QueryResult:
    """Container for results of a query."""
    query: "Query"
    result: str
    sources: list[weaviate_search_engine.SearchResult]
    search_parameters: dict


@dataclasses.dataclass
class QueryResults:
    """Container for list of query results."""
    results: list[QueryResult]


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

        assert len(candidate_root_queries) == 1

        return candidate_root_queries.pop()

    def insert_at_root(self, query_str: str, raise_if_exists: bool = False):
        """Insert a query at the root of the query plan's computational graph.

        Args:
            query_str: The query to insert
            raise_if_exists: Raise an exception if the query already exists in the graph
        """
        max_query_id = 0
        question_already_exists = False
        candidate_top_level_queries = set([query.id for query in self.query_graph])
        for query in self.query_graph:
            question_already_exists = query.question == query_str
            if question_already_exists and raise_if_exists:
                raise ValueError(f"Query '{query_str}' is already in the query graph.")

            max_query_id = max(query.id, max_query_id)

            for sub_query_id in query.sub_queries:
                try:
                    candidate_top_level_queries.remove(sub_query_id)
                except KeyError:
                    pass

        if question_already_exists:
            return

        new_root_query = Query(
            id=max_query_id + 1,
            question=query_str,
            sub_queries=list(candidate_top_level_queries)
        )

        self.query_graph.append(new_root_query)

    def get_execution_order(self) -> list[int]:
        """Returns the order in which the queries should be executed using topological sort.

        Args:
            Return list of query IDs in topological order
        """
        tmp_dep_graph = {item.id: set(item.sub_queries) for item in self.query_graph}

        def topological_sort(
            dep_graph: dict[int, set[int]]
        ) -> typing.Generator[set[int], None, None]:
            while True:
                ordered = set(item for item, dep in dep_graph.items() if len(dep) == 0)
                if not ordered:
                    break
                yield ordered
                dep_graph = {
                    item: (dep - ordered)
                    for item, dep in dep_graph.items()
                    if item not in ordered
                }
            if len(dep_graph) != 0:
                raise ValueError(
                    f"Circular dependencies exist among these items: {{{', '.join(f'{key}:{value}' for key, value in dep_graph.items())}}}"
                )

        result = []
        for d in topological_sort(tmp_dep_graph):
            result.extend(sorted(d))
        return result