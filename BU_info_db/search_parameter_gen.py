import enum

import pydantic

import openai_schema as openai_schema


class SearchMode(str, enum.Enum):
    semantic = "semantic"
    hybrid = "hybrid"
    keyword = "keyword"


class SearchParameters(openai_schema.OpenAISchema):
    """Class representing a queries search parameters."""
    top_k: int = pydantic.Field(
        default=3,
        le=10,
        ge=1,
        description="Number of most relevant search results to return."
    )
    mode: SearchMode = pydantic.Field(
        default=SearchMode.hybrid,
        description="The search mode can be semantic, keyword or both (hybrid). "
                    "Semantic searches are done by embedding the search query text "
                    "into a vector and doing a KNN similarity search against the vectors of "
                    "all possible results to get top_k results. "
                    "Keyword searches are done by using the BM25 ranking function to get top_k results. "
                    "Hybrid searches uses a combination of semantic and keyword search to get top_k results."
    )
    alpha: float = pydantic.Field(
        default=0.75,
        le=1.0,
        ge=0.0,
        description="You can use the alpha parameter for hybrid search mode to tune the weighting "
                    "of keyword (bm25) vs semantic (vector) search results. An alpha of 0.5 would weight "
                    "semantic and keyword searches equally, 0 would be a pure keyword search and "
                    "1 would be a pure semantic search."
    )

    class Config:
        use_enum_values = True