import concurrent.futures
import re

import openai
import tenacity
import tqdm
import tqdm.asyncio

import BU_info_db.storage.storage_data_classes as data_classes


class wait_openai_ratelimit(tenacity.wait_exponential):
    @classmethod
    def _get_duration_and_unit(cls, s: str) -> tuple[float, str]:
        for i, c in enumerate(reversed(s)):
            if c.isdigit():
                break

        duration = float(s[:-i])
        unit = s[-i:].lstrip()

        return duration, unit

    def __call__(self, retry_state: tenacity.RetryCallState) -> float:
        exc = retry_state.outcome.exception()

        if not isinstance(exc, openai.error.RateLimitError):
            return super().__call__(retry_state=retry_state)

        ratelimit_type = exc.json_body["error"]["type"]
        if ratelimit_type == "tokens":
            # ratelimit_remaining_tokens = int(exc.headers["x-ratelimit-remaining-tokens"])
            ratelimit_tokens: str = exc.headers["x-ratelimit-limit-tokens"]
            ratelimit_reset_tokens: str = exc.headers["x-ratelimit-reset-tokens"]
            reached_ratelimit_limit_message = f"Reached tokens per minute limit ({ratelimit_tokens}/min)"
            duration, unit = self._get_duration_and_unit(ratelimit_reset_tokens)
        else:
            # ratelimit_remaining_requests = exc.headers["x-ratelimit-remaining-requests"]
            ratelimit_requests: str = exc.headers["x-ratelimit-limit-requests"]
            ratelimit_reset_requests: str = exc.headers["x-ratelimit-reset-requests"]
            reached_ratelimit_limit_message = f"Reached requests per minute limit ({ratelimit_requests}/min)"
            duration, unit = self._get_duration_and_unit(ratelimit_reset_requests)

        if unit == "ms":
            duration = duration / 1000
        elif unit == "s":
            duration = duration
        else:
            print(
                f"Unknown ratelimit reset duration unit: {unit}, defaulting to exponential backoff logic.")
            return super().__call__(retry_state=retry_state)

        print(f"{reached_ratelimit_limit_message}. Sleeping for {duration} seconds until ratelimit is reset..")

        return duration


# Retry config recommended by OpenAI:
# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_handle_rate_limits.ipynb
openai_retry_config = tenacity.retry(
    wait=wait_openai_ratelimit(min=1, max=60),
    stop=tenacity.stop_after_attempt(6),
    retry=tenacity.retry_if_exception_type(
        (
            openai.error.Timeout,
            openai.error.APIError,
            openai.error.APIConnectionError,
            openai.error.RateLimitError,
            openai.error.ServiceUnavailableError,
        )
    )
)


class EmbeddingsClient:
    def __init__(self, openai_api_key: str, batch_size: int = 10, model_name: str = "text-embedding-ada-002"):
        self._openai_api_key = openai_api_key
        self._batch_size = batch_size
        self._model_name = model_name

    @openai_retry_config
    def _create_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Create embedding using OpenAI Embedding API"""
        resp = openai.Embedding.create(
            input=texts,
            model=self._model_name,
            api_key=self._openai_api_key
        )
        embeddings = [data["embedding"] for data in resp["data"]]
        return embeddings

    @openai_retry_config
    async def _acreate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Create embedding using OpenAI Embedding API"""
        resp = await openai.Embedding.acreate(
            input=texts,
            model=self._model_name,
            api_key=self._openai_api_key
        )
        embeddings = [data["embedding"] for data in resp["data"]]
        return embeddings

    @classmethod
    def _get_texts_to_embed(cls, weaviate_object: data_classes.Webpage) -> list[str]:
        """Returns the texts to use for generating the embedding based on the content type"""
        # If it's a CSV, create the embedding from the document metadata, otherwise use the content itself
        texts_to_embed = [text_content.text for text_content in weaviate_object.text_contents]

        return texts_to_embed

    def _create_embeddings_batched(self, weaviate_object: data_classes.Webpage) -> list[list[float]]:
        """Batch up and create embedding using OpenAI Embedding API"""
        embeddings = []
        texts_to_embed = self._get_texts_to_embed(weaviate_object)
        for i in range(0, len(texts_to_embed), self._batch_size):
            texts_batch = texts_to_embed[i: i + self._batch_size]
            embeddings_batch = self._create_embeddings(texts=texts_batch)
            embeddings.extend(embeddings_batch)

        return embeddings

    async def _acreate_embeddings_batched(self, weaviate_object: data_classes.Webpage) -> list[list[float]]:
        """Batch up and create embedding using OpenAI Embedding API"""
        embeddings = []
        texts_to_embed = self._get_texts_to_embed(weaviate_object)
        for i in range(0, len(texts_to_embed), self._batch_size):
            texts_batch = texts_to_embed[i: i + self._batch_size]
            embeddings_batch = await self._acreate_embeddings(texts=texts_batch)
            embeddings.extend(embeddings_batch)

        return embeddings

    def create_weaviate_object_embeddings(self, weaviate_objects: list[data_classes.Webpage]):
        """Populate embeddings for text contents of weaviate objects using OpenAI Embedding API.

        Args:
            weaviate_objects: List of Thread of Document objects each containing the list of text contents to compute embeddings for.

        Returns:
            None, this function will fill in the _vector property of all TextContent objects contained in each Thread/Document.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = pool.map(self._create_embeddings_batched, weaviate_objects)
            for weaviate_object, embeddings in tqdm.tqdm(
                zip(weaviate_objects, results),
                total=len(weaviate_objects),
                desc="Object embeddings"
            ):
                for text_content, embedding in zip(weaviate_object.text_contents, embeddings):
                    text_content.vector = embedding

    async def acreate_weaviate_object_embeddings(self, weaviate_objects: list[data_classes.Webpage]):
        """Populate embeddings for text contents of weaviate objects using OpenAI Embedding API.

        Args:
            weaviate_objects: List of Thread of Document objects each containing the list of text contents to compute embeddings for.

        Returns:
            None, this function will fill in the _vector property of all TextContent objects contained in each Thread/Document.
        """
        results = await tqdm.asyncio.tqdm.gather(
            *[
                self._acreate_embeddings_batched(weaviate_object)
                for weaviate_object in weaviate_objects
            ],
            total=len(weaviate_objects),
            desc="Object embeddings"
        )
        for weaviate_object, embeddings in zip(weaviate_objects, results):
            for text_content, embedding in zip(weaviate_object.text_contents, embeddings):
                text_content.vector = embedding
