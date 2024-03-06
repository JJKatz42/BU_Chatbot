import json
import time
from typing import List

import requests
import tenacity
import tqdm
import weaviate

import src.libs.storage.storage_data_classes as data_classes
import src.libs.storage.embeddings as embeddings
import src.libs.logging as logging


logger = logging.getLogger(__name__)


# Aliases
WeaviateObject = data_classes.WeaviateObject
TextContent = data_classes.TextContent
Webpage = data_classes.Webpage
CrossReference = data_classes.CrossReference


class RetryableBatch(weaviate.batch.Batch):
    """Subclass Weaviate's Batch class, so we can inject retries on exceptions not handled by the library"""
    @tenacity.retry(
        wait=tenacity.wait_exponential_jitter(max=20),
        stop=tenacity.stop_after_attempt(5),
        retry=tenacity.retry_if_exception_type((json.JSONDecodeError, requests.exceptions.JSONDecodeError))
    )
    def _flush_in_thread(self, *args, **kwargs):
        """This function is called whenever a Batch has accumulated enough items and
        needs to be flushed (written to Weaviate). This seemed like the best place to add retry with
        backoff when there are ephemeral server errors."""
        return super()._flush_in_thread(*args, **kwargs)


class WeaviateStore:
    def __init__(
        self,
        instance_url: str,
        api_key: str,
        openai_api_key: str,
        cohere_api_key: str,
        namespace: str | None = None
    ):
        weaviate.client.Batch = RetryableBatch
        self.client = weaviate.Client(
            url=instance_url,
            auth_client_secret=weaviate.AuthApiKey(api_key=api_key),
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key,
                "X-Cohere-Api-Key": cohere_api_key
            }
        )
        self.client.batch.configure(
            batch_size=100,
            num_workers=4,
            timeout_retries=30,
            connection_error_retries=30
        )
        self.namespace = namespace

        self._embeddings_client = embeddings.EmbeddingsClient(openai_api_key=openai_api_key)
        self.open_api_key = openai_api_key

    def create_schema(self, delete_if_exists: bool = False):
        """Create all classes in Weaviate schema

        Args:
            delete_if_exists: If class already exists and this is True, re-create it. If False, do nothing.
        """
        weaviate_classes = [TextContent, Webpage]

        for weaviate_class in weaviate_classes:
            weaviate_class_name = weaviate_class.weaviate_class_name(namespace=self.namespace)
            if self.client.schema.exists(weaviate_class_name):
                if delete_if_exists:
                    self.client.schema.delete_class(weaviate_class_name)
                else:
                    raise Exception(f"Can't create schema because {weaviate_class_name} already exists. "
                                    f"Set delete_if_exists=True to re-create the schema.")

        self.client.schema.create({
            "classes": [
                weaviate_class.weaviate_class_schema(namespace=self.namespace)
                for weaviate_class in weaviate_classes
            ]
        })

    def insert_webpages(self, webpages: list[Webpage]):
        # We build a list of the webpages we've inserted to refresh at the end to create the centroid vectors
        webpages_to_refresh_centroid_vector = []
        webpages_that_failed = []

        # Insert all data objects and references that support batching with batch
        logger.info("Creating webpage objects in Weaviate")
        with self.client.batch as batch:
            # Compute the embeddings for all TextContents on each Webpage
            self._embeddings_client.create_weaviate_object_embeddings(webpages)

            for webpage in tqdm.tqdm(webpages, total=len(webpages), desc="webpages"):
                time.sleep(.44)
                # Add the webpage object
                webpage_uuid = batch.add_data_object(
                    class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                    uuid=webpage.weaviate_id,
                    data_object=webpage.to_weaviate_object(),
                )
                webpages_to_refresh_centroid_vector.append(webpage_uuid)
                webpages_that_failed.append(webpage_uuid)

                try:
                    # Add the TextContent objects for each chunk of the webpage and the reference/from the Webpage
                    for text_content in webpage.text_contents:
                        text_content_uuid = batch.add_data_object(
                            class_name=TextContent.weaviate_class_name(namespace=self.namespace),
                            data_object=text_content.to_weaviate_object(),
                            vector=text_content.vector
                        )
                        batch.add_reference(
                            from_object_class_name=TextContent.weaviate_class_name(namespace=self.namespace),
                            from_object_uuid=text_content_uuid,
                            from_property_name="contentOf",
                            to_object_class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                            to_object_uuid=webpage_uuid
                        )
                        batch.add_reference(
                            from_object_class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                            from_object_uuid=webpage_uuid,
                            from_property_name="textContents",
                            to_object_class_name=TextContent.weaviate_class_name(namespace=self.namespace),
                            to_object_uuid=text_content_uuid
                        )
                    webpages_that_failed.remove(webpage_uuid)
                except:
                    logger.warning(f"This webpage failed {webpages_that_failed}")

        logger.info("Created webpage objects and references in Weaviate")

        # Add the references from Webpage -> TextContent. These need to be added outside the batch because
        # ref2vec-centroid does not support batch updates
        logger.info("Refreshing centroid vectors")
        for webpage_uuid in tqdm.tqdm(
            webpages_to_refresh_centroid_vector,
            total=len(webpages_to_refresh_centroid_vector),
            desc="Webpage -> TextContent centroid vectors"
        ):
            self.client.data_object.update(
                class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                uuid=webpage_uuid,
                data_object={"textContents": []}
            )
        logger.info("Refreshed centroid vectors")

    def insert_references(self, references: list[CrossReference]):
        logger.info("Creating references in Weaviate")
        with self.client.batch as batch:
            for reference in references:
                batch.add_reference(
                    from_object_class_name=reference.from_class,
                    from_object_uuid=reference.from_uuid,
                    from_property_name=reference.from_property,
                    to_object_class_name=reference.to_class,
                    to_object_uuid=reference.to_uuid
                )

        logger.info("Created references in Weaviate")

    def delete_webpage(self, url: str):
        """Delete a Webpage object from Weaviate given its URL

        Args:
            url: The URL of the Webpage object to delete
        """
        # We first get the Webpage object to find its uuid
        # The where filter is used to match the webpage url
        webpage_result = (
            self.client.query
            .get(Webpage.weaviate_class_name(namespace=self.namespace), ["webpage_id"])
            .with_where({"path": ["url"], "operator": "Equal", "valueText": url})
            .do()
        )

        # Check if webpage exists
        if webpage_result in webpage_result['data']['Get']:
            webpage_uuid = webpage_result['data']['webpage_id']

            # Before deleting the webpage object, we delete all the TextContent objects related to it

            text_content_results = (
                self.client.query
                .get(TextContent.weaviate_class_name(namespace=self.namespace), ["_additional { id }"])
                .with_where({
                    "path": ["contentOf", "Webpage", "url"],
                    "operator": "Like",
                    "valueText": url
                })
                .do()
            )

            for text_content in text_content_results:
                self.client.data_object.delete(
                    class_name=TextContent.weaviate_class_name(namespace=self.namespace),
                    uuid=text_content["_additional"]["id"]
                )

            # Finally, delete the webpage object
            self.client.data_object.delete(
                class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                uuid=webpage_uuid
            )
        else:
            logger.warning(f"Webpage with url {url} does not exist in Weaviate database")

    def get_duplicate_webpage(self, url: str) -> list:
        """Check if a Webpage object exists in Weaviate

        Returns:
            True if the Webpage object exists, False otherwise
        """
        results = (
            self.client.query
            .get(Webpage.weaviate_class_name(namespace=self.namespace), ["url", "html_content"])
            .with_where({"path": ["url"], "operator": "Equal", "valueText": url})
            .do()
        )

        if results["data"]["Get"][Webpage.weaviate_class_name(namespace=self.namespace)]:
            html_content = results["data"]["Get"][Webpage.weaviate_class_name(namespace=self.namespace)][0][
                "html_content"]
            return [url, html_content]

        return []

    def create_embedding(self, text: str) -> list[list[float]]:
        """Get the embedding for a text using OpenAI Embedding API"""
        return self._embeddings_client.create_embedding(text=text)
