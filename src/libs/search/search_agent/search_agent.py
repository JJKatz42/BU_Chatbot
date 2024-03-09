import asyncio
import dataclasses
import datetime
import enum
import typing

import langchain.callbacks
import langchain.chat_models
import langchain.schema
import llama_index.llms.openai_utils as openai_utils
import numpy as np

import src.libs.search.search_agent.query_planning as query_planning
import src.libs.search.search_agent.search_parameter_gen as search_parameter_gen
import src.libs.search.weaviate_search_engine as weaviate_search_engine
import src.libs.search.search_agent.answer_formatting as answer_formatting
import src.libs.storage.storage_data_classes as storage_data_classes
import src.libs.logging as logging


logger = logging.getLogger(__name__)


SOURCE_TYPE = typing.Type[storage_data_classes.Webpage]
SOURCE_TYPE_TO_NULL_CHECK_PROPERTY = {
    storage_data_classes.Webpage: "Webpage_id"
}

# Re-ranking config constants
RELEVANCE_RE_RANKING_WEIGHT = 1.0


class SearchAgent:
    """Agent that answers questions.

    This agent provides answers to queries by first searching for relevant information
    as context then generating an answer.

    Args:
        weaviate_search_engine: Instance of the WeaviateSearchEngine used for executing searches
        reasoning_llm: LLM object used for tasks requiring high degree of reasoning capabilities
        qa_llm: LLM object used for the task of generating answer given relevant information as context
        features: List of features to enable on the agent. Features are disabled, unless explicitly provided.
        include_source_types: Limit source types used as context for answering queries.
            Defaults to using all source types.
    """
    def __init__(
        self,
        weaviate_search_engine: weaviate_search_engine.WeaviateSearchEngine,
        university: str,
        reasoning_llm: langchain.chat_models.ChatOpenAI,
        qa_llm: langchain.chat_models.ChatOpenAI | None = None,
        features: list["SearchAgentFeatures"] | None = None,
        include_source_types: list[SOURCE_TYPE] | None = None
    ):
        self._weaviate_search_engine = weaviate_search_engine
        self._university_type_filter = university
        self._reasoning_llm = reasoning_llm
        self._qa_llm = qa_llm or reasoning_llm
        self._features = features or []

        self._include_source_types = include_source_types

        self._source_type_filter = self._build_source_type_filter()

        # LLM used when prompt size is larger than the QA LLM supported context size
        self._fallback_qa_llm_model_name = "gpt-3.5-turbo-16k"
        # self._fallback_qa_llm_model_name = "gpt-4-32k"
        # Get the max context sizes for LLMs
        self._reasoning_llm_context_size = openai_utils.openai_modelname_to_contextsize(
            self._reasoning_llm.model_name
        )
        self._qa_llm_context_size = openai_utils.openai_modelname_to_contextsize(
            self._qa_llm.model_name
        )
        self._fallback_qa_llm_context_size = openai_utils.openai_modelname_to_contextsize(
            self._fallback_qa_llm_model_name
        )

    async def run(
            self,
            query: str,
            current_profile_info: dict,
            profile_info_vector: list[float],
            context: "Context" = None
    ) -> "AgentResult":
        """Get an answer to a query by searching for information then generating response

        Args:
            query: The query posed as a question
            current_profile_info: The current profile information for the user.
            profile_info_vector: The current profile information for the user.
            context: Context related to the query used for disambiguation

        Returns:
            An AgentResult object which contains the answer, sources used and various debug details
        """
        with langchain.callbacks.get_openai_callback() as cb:
            # Default query plan consists of just the original query passed to run()
            query_plan = query_planning.QueryPlan(
                query_graph=[
                    query_planning.Query(
                        id=1,
                        question=query,
                        sub_queries=[]
                    )
                ]
            )
            # If query planning feature is enabled, auto generate a query plan
            if self.is_enabled(SearchAgentFeatures.QUERY_PLANNING):
                query_plan = await self.build_query_plan(query=query)

            # Execute the query plan
            query_plan_results = await self.execute_query_plan(
                query_plan=query_plan,
                current_profile_info=current_profile_info,
                profile_info_vector=profile_info_vector,
                context=context
            )

            # Capture the total number of LLM tokens used over the course of query plan execution
            total_tokens_used = cb.total_tokens
            total_tokens_cost = cb.total_cost

        # Get the result for the root query in the query plan which will be the original query passed to this run()
        root_query_id = query_plan.get_root_query_id()
        root_query_result = query_plan_results[root_query_id]

        # Get list of all sources used in the execution of query plan
        all_sources = []
        for _, query_result in query_plan_results.items():
            for source in query_result.sources:
                if source not in all_sources:
                    all_sources.append(source)

        formatted_answer = await answer_formatting.format_answer(
            generated_answer=root_query_result.result,
            sources=all_sources,
            llm=self._qa_llm,
            fallback_llm=self._reasoning_llm,
            query=query,
        )

        return AgentResult(
            query=query,
            answer=formatted_answer,
            sources=all_sources,
            query_plan=query_plan,
            query_plan_results=query_plan_results,
            features=self._features,
            context=context,
            total_tokens_used=total_tokens_used,
            total_tokens_cost=total_tokens_cost
        )

    async def execute_query_plan(
        self,
        query_plan: query_planning.QueryPlan,
        current_profile_info: dict,
        profile_info_vector: list[float],
        context: "Context"
    ) -> dict[int, query_planning.QueryResult]:
        """Executes the queries in the query plan in the correct order.

        Args:
            query_plan: The query plan to execute
            current_profile_info: The current profile information for the user.
            profile_info_vector:
            context: Context in which to run queries

        Returns:
            Dictionary mapping query ID to query result for each query in the query plan.
        """
        execution_order: list[int] = query_plan.get_execution_order()
        queries: dict[int, query_planning.Query] = {q.id: q for q in query_plan.query_graph}
        query_results: dict[int: query_planning.QueryResult] = {}
        while True:
            ready_to_execute = [
                queries[task_id]
                for task_id in execution_order
                if task_id not in query_results
                and all(
                    sub_query_id in query_results for sub_query_id in queries[task_id].sub_queries
                )
            ]
            logger.info(f"Queries ready to execute: {ready_to_execute}")

            computed_query_results: list[query_planning.QueryResult] = await asyncio.gather(
                *[
                    self.execute_query(
                        query=query,
                        current_profile_info=current_profile_info,
                        profile_info_vector=profile_info_vector,
                        sub_query_results=query_planning.QueryResults(
                            results=[
                                result
                                for result in query_results.values()
                                if result.query.id in query.sub_queries
                            ]
                        ),
                        context=context
                    )
                    for query in ready_to_execute
                ]
            )
            for query_result in computed_query_results:
                query_results[query_result.query.id] = query_result
            if len(query_results) == len(execution_order):
                break
        return query_results

    async def execute_query(
        self,
        query: query_planning.Query,
        sub_query_results: query_planning.QueryResults,
        current_profile_info: dict,
        profile_info_vector: list[float],
        context: "Context"
    ) -> query_planning.QueryResult:
        """Execute a query in the query plan.

        Args:
            query: The query to execute
            sub_query_results: The results of sub-queries for this query that will be used
                to generate an answer for this query.
            current_profile_info: The current profile information for the user.
            profile_info_vector:
            context: Context in which to run the query

        Returns:
            A QueryResult object which is a container for the generated answer with sources used.
        """
        # If the automatic search param generation feature is enabled, use LLM to pick optimal params

        if self.is_enabled(SearchAgentFeatures.AUTO_SEARCH_PARAMETER_GEN):
            search_parameters = await self._generate_search_parameters(query=query.question)
        else:
            search_parameters = search_parameter_gen.SearchParameters().dict()

        # Number of search results used to generate answer
        num_results_for_gen = search_parameters["top_k"]

        search_parameters["personalized_info_vector"] = profile_info_vector

        search_parameters["filters"] = {"university": self._university_type_filter}

        # If the cross encoder re-ranking feature is enabled, increase number of search
        # results retrieved from search engine to cast a wider initial net.
        if self.is_enabled(SearchAgentFeatures.CROSS_ENCODER_RE_RANKING):
            search_parameters["top_k"] = 50

        # If the Agent is configured to only use specific source types, apply the filter to the search query
        if self._source_type_filter:
            search_parameters["filters"].append(self._source_type_filter)

        # Get main loop so the synchronous Weaviate search function can be
        # run async in the default loop's executor (ThreadPoolExecutor)
        loop = asyncio.get_running_loop()
        sources = await loop.run_in_executor(
            None,
            lambda: self._weaviate_search_engine.search(
                query_str=query.question,
                re_rank=self.is_enabled(SearchAgentFeatures.CROSS_ENCODER_RE_RANKING),
                **search_parameters
            )
        )

        # Re-rank and get top K sources
        sources = self._re_rank(sources=sources, top_k=num_results_for_gen)

        # Build up the sources context string from the sources returned by search
        source_texts = []
        for source in sources:
            # For CSV data, only take the first 10k characters so as to not exceed context token limit with large CSVs
            source_texts.append(source.text)
        sources_context = "\n\n".join([
            f'Search Result {idx + 1}:\n"""\n{source_text}\n"""'
            for idx, source_text in enumerate(source_texts)
        ])

        # If this query has results for sub-queries, use those as context as well
        sub_query_results_context = "\n\n".join([
            f"Question: {sub_query_result.query.question}\nMy Answer: {sub_query_result.result}"
            for sub_query_result in sub_query_results.results
        ])

        # Construct LLM prompt using combination of system, user and AI messages.
        # Use "system" messages for setting ground rules and providing a role for AI
        # Use "human" messages for input coming from user
        # Use "AI" messages for the AI's responses to system/human messages

        # First system message explains to LLM its role and the job to be done.
        role_prompt_message = langchain.schema.SystemMessage(
            content="You are a helpful, knowledgeable and confident university chatbot. "
                    "Your task is to respond to the student's question with a helpful, "
                    "accurate and concise answer based only on the information that can be "
                    "found in the university data. Before answering the student's question, "
                    "first search for supporting information from the university's data."
            )

        # User message provides the query
        question_prompt_message = langchain.schema.HumanMessage(content=f"Question: {query.question}")

        # AI message (impersonate the AI) containing the search results
        search_results_prompt_message = langchain.schema.AIMessage(
            content="I searched the university's data for supporting information and found the "
                    "following results related to your question. "
                    f"The search results are in order of trustworthiness:\n{sources_context}"
        )

        # AI message (impersonate the AI) containing answers to sub-queries
        sub_query_results_prompt_message = langchain.schema.AIMessage(
            content="I have also previously answered these questions that may be relevant to "
                    f"answering your question:\n{sub_query_results_context}"
        ) if sub_query_results_context else None

        # Another system message to re-enforce the rules of the AI's answer
        answer_rules_prompt_message = langchain.schema.SystemMessage(
            content=f"Use the above search results "
                    f"{'and answers to related questions ' if sub_query_results_prompt_message else ''}"
                    f"to provide a helpful, accurate and concise answer to the student's question. "
                    f"If there is conflicting information between search results, "
                    f"use the more trustworthy result (higher up in search results). "
                    "If you can't answer the question, be honest and tell the student what information "
                    "you were able to find and what information is missing to answer their question."
        )

        user_personal_information = langchain.schema.SystemMessage(
            content=f"If a user asks about themselves or uses 'I' in their question, use the following "
                    f"information provided in the dictionary below to answer the question: \n"
                    f"{current_profile_info}"
        )

        # Create the artificial history of messages to prompt LLM
        llm_prompt_messages = [
            role_prompt_message,
            question_prompt_message,
            search_results_prompt_message,
            user_personal_information
        ]
        if sub_query_results_prompt_message:
            llm_prompt_messages.append(sub_query_results_prompt_message)
        llm_prompt_messages.append(answer_rules_prompt_message)

        # If the prompt is too large for the LLM's max context size, automatically switch to a larger LLM.
        llm_override_params = {}
        num_tokens_in_prompt = self._qa_llm.get_num_tokens_from_messages(llm_prompt_messages)
        if num_tokens_in_prompt > (self._qa_llm_context_size - 500):
            if num_tokens_in_prompt > (self._fallback_qa_llm_context_size - 500):
                # TODO: Auto retry with fewer search results instead of throwing exception?
                logger.warning(
                    f"Query {query.id} prompt has {num_tokens_in_prompt} tokens which is larger "
                    f"than maximum supported context size ({self._fallback_qa_llm_context_size})."
                )

            logger.warning(
                f"Query {query.id} prompt has {num_tokens_in_prompt} tokens which is larger than "
                f"the QA LLM's context size, switching to {self._fallback_qa_llm_model_name}."
            )
            llm_override_params = {"model": self._fallback_qa_llm_model_name}

        llm_answer_message = await self._qa_llm.apredict_messages(messages=llm_prompt_messages, **llm_override_params)

        return query_planning.QueryResult(
            query=query,
            result=llm_answer_message.content,
            sources=sources,
            search_parameters=search_parameters
        )

    async def build_query_plan(self, query: str) -> query_planning.QueryPlan:
        """Build a computational graph of queries and sub-queries needed to answer the query.

        This function uses an LLM to reason about what the query plan should be.

        Args:
            query: The original query to create query plan for

        Returns:
            QueryPlan object which contains the computational graph or queries and sub-queries
        """
        llm_prompt_messages = [
            langchain.schema.SystemMessage(
                content="You are a world class query planning algorithm capable of "
                        "breaking apart questions into dependant sub-questions, such that "
                        "the answers can be used to inform the parent question. "
                        "Do not answer the questions, simply provide "
                        "a correct compute graph with good specific questions to ask "
                        "and relevant sub-questions. Before you call the function, "
                        "think step by step to get a better understanding the problem.",
            ),
            langchain.schema.HumanMessage(content=query),
        ]

        llm_query_plan_response_message = await self._reasoning_llm.apredict_messages(
            messages=llm_prompt_messages,
            functions=[query_planning.QueryPlan.openai_schema],
            function_call={"name": query_planning.QueryPlan.openai_schema["name"]},
        )

        query_plan = query_planning.QueryPlan.from_response(llm_query_plan_response_message)

        query_plan.insert_at_root(query_str=query)

        return query_plan

    def _re_rank(
        self,
        sources: list[weaviate_search_engine.SearchResult],
        top_k: int
    ) -> list[weaviate_search_engine.SearchResult]:
        """Re-rank search results then filter to top k.

        The re-ranking is done by taking a weighted sum of 1 or more of the following:
        - relevance score (returned by Weaviate as a result of keyword/vector/hybrid search + optional cross-encoder)
        - number of references score (using # document references metric)
        - update recency score (using the inverse of last updated time metric)
        - content type score (weights certain type of content higher than others. Ex: document > message)

        Args:
            sources: List of search results to re-rank
            top_k: The number of search results to return after re-ranking

        Returns:
            Top k search results
        """
        scores = np.zeros(len(sources))

        # Relevance scores returned by Weaviate are always used to rank sources
        relevance_scores = np.array([source.score for source in sources])
        relevance_scores = self._normalize_values(relevance_scores)
        # TODO: weights should be configurable
        scores += relevance_scores * RELEVANCE_RE_RANKING_WEIGHT

        sources_with_scores = zip(sources, scores)

        re_ranked_sources = sorted(sources_with_scores, key=lambda x: x[1], reverse=True)

        top_k_sources = [source_with_score[0] for source_with_score in re_ranked_sources[:top_k]]

        return top_k_sources

    @staticmethod
    def _normalize_values(data: np.array) -> np.array:
        """Normalize the values in a list to a range from 0 to 1.

        Normalization is based on minimum and maximum values present in the data.

        Args:
            data: Array of data values

        Returns:
            Normalized array of data values where each item is between 0 and 1
        """
        min_val = np.min(data)
        max_val = np.where(np.max(data) - min_val == 0, min_val + 0.001, np.max(data))  # 0.001 to avoid division by zero
        normalized_data = (data - min_val) / (max_val - min_val)
        return normalized_data

    async def _generate_search_parameters(self, query: str) -> dict:
        """Generate optimal Weaviate query engine search parameters for the given query.

        Args:
            query: The query to optimize search parameters for

        Returns:
            Dictionary of search parameters that can be passed to WeaviateSearchEngine.search()
        """
        llm_prompt_messages = [
            langchain.schema.SystemMessage(
                content="You are a world class search optimization algorithm capable of "
                        "tuning search parameters to return the most relevant and comprehensive search results"
                        "for a given query. The query will be sent to the database as is, you can't modify it. "
                        "The search query along with the parameters you select will be executed against a "
                        "database containing rows of text data that are either a single slack message or "
                        "a chunk of a Google document. Do not answer the query, simply provide the optimal "
                        "search parameters that would result in the most relevant and comprehensive search results. "
                        "Before you call the function, think step by step to get a better understanding the problem.",
            ),
            langchain.schema.HumanMessage(content=f"Query: {query}"),
        ]

        llm_search_params_response_message = await self._reasoning_llm.apredict_messages(
            messages=llm_prompt_messages,
            functions=[search_parameter_gen.SearchParameters.openai_schema],
            function_call={
                "name": search_parameter_gen.SearchParameters.openai_schema["name"]
            },
        )

        search_query_params = search_parameter_gen.SearchParameters.from_response(
            llm_search_params_response_message
        )

        return search_query_params.dict()

    def _build_source_type_filter(self) -> dict | None:
        """Build Weaviate filters for including specific source types"""
        if not self._include_source_types:
            return

        source_type_filters = {
            "operator": "Or",
            "operands": [
                {
                    "path": [
                        "contentOf",
                        source_type.weaviate_class_name(namespace=self._weaviate_search_engine.namespace),
                        SOURCE_TYPE_TO_NULL_CHECK_PROPERTY[source_type]
                    ],
                    "operator": "IsNull",
                    "valueBoolean": False
                } for source_type in self._include_source_types
            ]
        }
        return source_type_filters

    def is_enabled(self, feature: "SearchAgentFeatures") -> bool:
        """Check if a particular feature is enabled on this instance of SearchAgent

        Args:
            feature: A feature to check

        Returns:
            True if the feature is enabled, False otherwise
        """
        return feature in self._features


class SearchAgentFeatures(enum.Enum):
    """Feature flags for the search agent"""
    # Implemented
    AUTO_SEARCH_PARAMETER_GEN = "AUTO_SEARCH_PARAMETER_GEN"
    QUERY_PLANNING = "QUERY_PLANNING"
    CROSS_ENCODER_RE_RANKING = "CROSS_ENCODER_RE_RANKING"
    # Not implemented
    MESSAGE_DISAMBIGUATION = "MESSAGE_DISAMBIGUATION"
    AUTO_SEARCH_FILTER_GEN = "AUTO_SEARCH_FILTER_GEN"
    ADAPTIVE_QUERY_PLANNING = "ADAPTIVE_QUERY_PLANNING"

TODO: determine usability of this class for conversationality Context. If usable, add conversationality functionality
@dataclasses.dataclass
class Context:
    """Container for context used by Agent to run a query"""
    user_name: str
    user_email: str
    current_date: datetime.datetime
    user_id: str = None


@dataclasses.dataclass
class AgentResult:
    """Container for result of running an Agent on a query."""
    answer: str
    sources: list[weaviate_search_engine.SearchResult]

    # Debug details
    context: Context
    query: str
    query_plan: query_planning.QueryPlan
    query_plan_results: dict[int: query_planning.QueryResult]
    features: list[SearchAgentFeatures]
    total_tokens_used: int
    total_tokens_cost: int
