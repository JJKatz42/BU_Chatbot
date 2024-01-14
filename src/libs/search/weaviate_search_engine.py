import typing

import llama_index
import llama_index.data_structs
import llama_index.indices.base_retriever as base_retriever
import weaviate.gql.get

from src.libs.search import search_data_classes as search_data_classes
from src.libs.storage import storage_data_classes as storage_data_classes
from src.libs.storage import weaviate_store
import src.libs.logging as logging


logger = logging.getLogger(__name__)


# Aliases
WeaviateObject = storage_data_classes.WeaviateObject
TextContent = storage_data_classes.TextContent
Webpage = storage_data_classes.Webpage

SearchResult = search_data_classes.SearchResult
Answer = search_data_classes.Answer
Summarization = search_data_classes.Summarization


class WeaviateSearchEngine(base_retriever.BaseRetriever):
    """Search interface to Weaviate vector database.

    This class implements the Llama Index retriever interface, so it can be plugged into
    the framework and work with other modules like QueryEngine's.
    """

    def __init__(self, weaviate_store: weaviate_store.WeaviateStore):
        self._weaviate_store = weaviate_store

    def _retrieve(self, query_bundle: llama_index.QueryBundle) -> list[llama_index.schema.NodeWithScore]:
        """This function is required to implement the Llama Index Retriever interface"""
        search_results = self.search(query_str=query_bundle.query_str)
        llama_index_search_results = [
            llama_index.schema.NodeWithScore(
                node=llama_index.schema.TextNode(
                    text=search_result.text
                )
            )
            for search_result in search_results
        ]
        return llama_index_search_results

    def search(
            self,
            query_str: str,
            mode: typing.Literal["semantic", "hybrid", "keyword"] = "hybrid",
            top_k: int = 3,
            alpha: float = 0.75,
            beta: float = 0.05,
            personalized_info_vector: list[float] = None,
            re_rank: bool = False,
            filters: dict = None
    ) -> list[SearchResult]:
        """Search for most relevant information to the query

        Args:
            query_str: The search query
            mode: Either "semantic", "keyword" or "hybrid". If "semantic", the search will be a pure vector search.
                If "keyword", it will be a keyword search.
                If "hybrid", both vector and keyword search will be used together.
            top_k: Number of most relevant results to return
            alpha: Only relevant for hybrid mode searches: https://weaviate.io/developers/weaviate/search/hybrid#weight-keyword-vs-vector-results
            beta: The weight of the personalized info vector
            personalized_info_vector: The centroid vector of the users personalized information
            re_rank: Re-rank results using Cohere API
            filters: Additional filters in the Weaviate format: https://weaviate.io/developers/weaviate/search/filters
query = query.with_autocut(1)
        Returns:
            List of SearchResult objects representing the top_k results returned by the search
        """
        query_str = query_str.replace('\n', ' ')
        # Build the core search query
        query = self._build_search_query(
            query_str=query_str,
            mode=mode,
            top_k=top_k,
            alpha=alpha,
            beta=beta,
            personalized_info_vector=personalized_info_vector,
            re_rank=re_rank,
            filters=filters
        )

        # Execute the query
        response = query.do()

        try:
            raw_results = response["data"]["Get"][
                TextContent.weaviate_class_name(namespace=self.namespace)
            ]
        except KeyError:
            logger.error(response["data"]["Get"])
            raise
        search_results = []
        for raw_result in raw_results:
            if re_rank:
                score = raw_result["_additional"]["rerank"][0]["score"]
            elif mode == "semantic":
                score = raw_result["_additional"]["certainty"]
            else:
                score = float(raw_result["_additional"]["score"])

            url = raw_result["contentOf"][0]["url"]
            search_result = SearchResult(
                text=raw_result["text"],
                url=url,
                score=score
            )
            search_results.append(search_result)

        return search_results

    def ask(
            self,
            ask_str: str,
            mode: typing.Literal["semantic", "hybrid", "keyword"] = "hybrid",
            top_k: int = 3,
            filters: dict = None
    ) -> Answer:
        """Answer a question by passing search results + question to LLM.

        The LLM call is happening on Weaviate via the generative-openai module: https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai

        Args:
            ask_str: The question to answer
            mode: Either "semantic", "keyword" or "hybrid". If "semantic", the search will be a pure vector search.
                If "keyword", it will be a keyword search.
                If "hybrid", both vector and keyword search will be used together.
            top_k: Number of most relevant results to return
            filters: Additional filters in the Weaviate format: https://weaviate.io/developers/weaviate/search/filters

        Returns:
            Answer object which contains the answer and list of SearchResult objects representing the top_k results returned by the search
        """
        # Build the core search query
        query = self._build_search_query(
            query_str=ask_str,
            mode=mode,
            top_k=top_k,
            filters=filters
        )

        # Augment the search query to generate the answer by grouping all the text properties
        # of search results into a single prompt.
        query = query.with_generate(
            grouped_task="You are a helpful, knowledgeable and confident university chatbot. "
                         "Your task is to respond to the student's question with a helpful "
                         "and accurate answer based only on the information contained in context. "
                         "The context is only visible to you, all the student will see is your answer.\n"
                         f"Question: {ask_str}\n"
                         "Context: ",
            grouped_properties=["text"]
        )

        # Execute the query
        response = query.do()

        # Parse into search results and answer
        raw_results = response["data"]["Get"][
            TextContent.weaviate_class_name(namespace=self.namespace)
        ]
        search_results = []
        answer_str = ""
        for raw_result in raw_results:
            if raw_result["_additional"].get("generate"):
                answer_str = raw_result["_additional"]["generate"]["groupedResult"]
                error = raw_result["_additional"]["generate"]["error"]
                if error:
                    logger.error(f"Error generating an answer: {error}")
            search_result = SearchResult(
                text=raw_result["text"],
                url=raw_result["contentOf"][0]["url"],
                score=(
                    raw_result["_additional"]["distance"]
                    if mode == "semantic"
                    else float(raw_result["_additional"]["score"])
                )
            )
            search_results.append(search_result)

        answer = Answer(answer=answer_str, search_results=search_results)

        return answer

    def summarize(
            self,
            query_str: str,
            mode: typing.Literal["semantic", "hybrid", "keyword"] = "hybrid",
            top_k: int = 5,
            filters: dict = None
    ) -> Summarization:
        """Summarize search results by passing search results + question to LLM.

        The LLM call is happening on Weaviate via the generative-openai module: https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai

        Args:
            query_str: The query to run. The search results from the query are what is summarized.
            mode: Either "semantic", "keyword" or "hybrid". If "semantic", the search will be a pure vector search.
                If "keyword", it will be a keyword search.
                If "hybrid", both vector and keyword search will be used together.
            top_k: Number of most relevant results to return
            filters: Additional filters in the Weaviate format: https://weaviate.io/developers/weaviate/search/filters

        Returns:
            Summarization object which contains the summary and list of SearchResult objects representing the top_k results returned by the search
        """
        # Build the core search query
        query = self._build_search_query(
            query_str=query_str,
            mode=mode,
            top_k=top_k,
            filters=filters
        )

        # Augment the search query to generate the summary by grouping all the text properties
        # of search results into a single prompt.
        query = query.with_generate(
            grouped_task="You are a helpful, knowledgeable and confident university chatbot. "
                         "I am an student at the university.\n"
                         "Please respond with a concise and accurate summary of the below information.\n"
                         "Information: ",
            grouped_properties=["text"]
        )

        # Execute the query
        response = query.do()

        # Parse into search results and answer
        raw_results = response["data"]["Get"][
            TextContent.weaviate_class_name(namespace=self.namespace)
        ]
        search_results = []
        summary_str = ""
        for raw_result in raw_results:
            if raw_result["_additional"].get("generate"):
                summary_str = raw_result["_additional"]["generate"]["groupedResult"]
                error = raw_result["_additional"]["generate"]["error"]
                if error:
                    logger.error(f"Error generating a summary: {error}")

            search_result = SearchResult(
                text=raw_result["text"],
                url=raw_result["contentOf"][0]["url"],
                score=(
                    raw_result["_additional"]["distance"]
                    if mode == "semantic"
                    else float(raw_result["_additional"]["score"])
                )
            )
            search_results.append(search_result)

        summarization = Summarization(summary=summary_str, search_results=search_results)

        return summarization

    @property
    def namespace(self):
        return self._weaviate_store.namespace

    def _build_search_query(
            self,
            query_str: str,
            mode: typing.Literal["semantic", "hybrid", "keyword"] = "hybrid",
            top_k: int = 3,
            alpha: float = 0.75,
            beta: float = 0.01,
            personalized_info_vector: list[float] = None,
            re_rank: bool = False,
            filters: dict = None,
    ) -> weaviate.gql.get.GetBuilder:
        """Build a search query for most relevant information to the query

        Args:
            query_str: The search query
            mode: Either "semantic", "keyword" or "hybrid". If "semantic", the search will be a pure vector search.
                If "keyword", it will be a keyword search.
                If "hybrid", both vector and keyword search will be used together.
            top_k: Number of most relevant results to return
            alpha: Only relevant for hybrid mode searches: https://weaviate.io/developers/weaviate/search/hybrid#weight-keyword-vs-vector-results
            beta: The weight of the personalized info vector
            personalized_info_vector: The centroid vector of the users personalized information
            re_rank: Re-rank results using Cohere API
            filters: Additional filters in the Weaviate format: https://weaviate.io/developers/weaviate/search/filters

        Returns:
            Weaviate QueryBuilder object
        """

        query = (
            self._weaviate_store.client.query
            .get(TextContent.weaviate_class_name(namespace=self.namespace),
                 ["index", "text", "contentOf { ... on Jonahs_weaviate_infodb_Webpage { url, webpage_id, mimeType, university } }"])
        )

        query = query.with_additional(properties=["id"])

        query = query.with_additional(properties=["certainty", "score"])

        query = query.with_limit(limit=top_k)

        # # Use the appropriate Weaviate search method
        if mode == "semantic":
            query = query.with_near_text(content={"concepts": [query_str]})
        elif mode == "hybrid":
            if not personalized_info_vector:
                query = query.with_hybrid(query=query_str, properties=["text"], alpha=alpha)
                query = query.with_autocut(1)
            else:
                weighted_vector = self._build_weighted_vector(query_str=query_str, personalized_info_vector=personalized_info_vector, beta=beta)
                query = query.with_hybrid(query=query_str, properties=["text"], alpha=alpha, vector=weighted_vector)
                query = query.with_autocut(1)
        elif mode == "keyword":
            query = query.with_bm25(query=query_str, properties=["text"])

        if re_rank:
            query = query.with_additional(
                properties=[
                    f"rerank (property: \"text\", query: \"{query_str}\") {{ score }}"
                ]
            )

        # Check for university filter in filters
        if filters and "university" in filters:
            university_filter = {
                "path": [
                    "contentOf",
                    "Jonahs_weaviate_infodb_Webpage",
                    "university"
                ],
                "operator": "Equal",
                "valueText":  filters["university"]
            }

            query = query.with_where(university_filter)

        return query

    def _build_weighted_vector(self, query_str: str, personalized_info_vector: list[float] = None, beta: float = 0.01):
        """
        Build a weighted vector from the centroid vector and the query string.

        Args:
            query_str: The search query
            personalized_info_vector: The centroid vector of the user's personalized information
            beta: The weight of the personalized info vector
        """
        # personalized_info_vector = self._weaviate_store.create_embedding("I am a student at Questrom school of business")[0]
        query_vector = self._weaviate_store.create_embedding(query_str)[0]
        weighted_vector = [(1 - beta) * query_vector[i] + beta * personalized_info_vector[i] for i in range(len(query_vector))]
        return weighted_vector
