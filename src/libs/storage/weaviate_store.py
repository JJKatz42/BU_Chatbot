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
from datetime import datetime, timezone, timedelta


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
            },
            timeout_config=(30, 30)
        )
        self.client.batch.configure(
            batch_size=100,
            num_workers=4,
            timeout_retries=1,
            connection_error_retries=1
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
            time.sleep(0.5)
            for webpage in tqdm.tqdm(webpages, total=len(webpages), desc="webpages"):
                time.sleep(0.4)
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
            time.sleep(0.1)
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
            .get(Webpage.weaviate_class_name(namespace=self.namespace), ["_additional { id }"])
            .with_where({"path": ["url"], "operator": "Equal", "valueText": url})
            .do()
        )

        # Check if webpage exists
        if webpage_result['data']['Get']:
            webpage_uuid = webpage_result['data']['Get']['Jonahs_weaviate_infodb_Webpage'][0]['_additional']['id']

            # Before deleting the webpage object, we delete all the TextContent objects related to it

            text_content_results = (
                self.client.query
                .get(TextContent.weaviate_class_name(namespace=self.namespace), ["_additional { id }"])
                .with_where({
                    "path": ["contentOf", "Jonahs_weaviate_infodb_Webpage", "url"],
                    "operator": "Like",
                    "valueText": url
                })
                .do()
            )
            try:
                for text_content in text_content_results['data']['Get']['Jonahs_weaviate_infodb_TextContent']:
                    self.client.data_object.delete(
                        class_name=TextContent.weaviate_class_name(namespace=self.namespace),
                        uuid=text_content["_additional"]["id"]
                    )
            except Exception as e:
                print(f"No text content found for webpage {url} or error {e}")

            # Finally, delete the webpage object
            try:
                self.client.data_object.delete(
                    class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                    uuid=webpage_uuid
                )

                logger.info(f"Webpage with url {url} has been deleted from Weaviate")
            except Exception as e:
                logger.warning(f"Webpage with url {url} could not be deleted from Weaviate or error {e}")

        else:
            logger.warning(f"Webpage with url {url} does not exist in Weaviate database")

    def delete_webpages_containing_mit(self):
        """Prints out a list of all Webpage objects with a URL containing 'mit' from Weaviate."""

        # We use the 'Like' operator with '%mit%' to match any part of the URL containing 'mit'
        webpage_results = (
            self.client.query
            .get(Webpage.weaviate_class_name(namespace=self.namespace), ["url"])
            .with_where({
                "path": ["url"],
                "operator": "Like",
                "valueString": "%mit%"
            })
            .do()
        )

        # Check if any webpages were found
        try:
            for webpage in webpage_results['data']['Get']['Jonahs_weaviate_infodb_Webpage']:
                if "mit.edu" in webpage['url']:
                    self.delete_webpage(webpage['url'])
                else:
                    pass
        except Exception as e:
            print(f"No webpages containing 'mit' were found in the Weaviate database or error {e}.")

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

    def print_webpage_count(self):
        """Print the number of Webpage objects in Weaviate."""
        results = (
            self.client.query
            .aggregate(Webpage.weaviate_class_name(namespace=self.namespace))
            .with_fields('meta { count }')
            .do()
        )

        # Correctly access the count based on the structure of results
        count = results["data"]["Aggregate"]["Jonahs_weaviate_infodb_Webpage"][0]["meta"]["count"]

        print(f"Number of Webpage objects: {count}")

    def print_textcontent_count(self):
        """Print the number of Webpage objects in Weaviate."""
        results = (
            self.client.query
            .aggregate(TextContent.weaviate_class_name(namespace=self.namespace))
            .with_fields('meta { count }')
            .do()
        )

        # Correctly access the count based on the structure of results
        count = results["data"]["Aggregate"]["Jonahs_weaviate_infodb_TextContent"][0]["meta"]["count"]

        print(f"Number of Webpage objects: {count}")

    def delete_webpages_from_university_before_specific_time(self):
        """Delete all Webpage objects from Weaviate that are associated with 'CAL' university
        and have a last updated timestamp (stored as a string) of less than March 2nd, 2024, 10 AM Eastern Standard Time,
        along with their related TextContent objects."""
        total_deleted_webpages = 0
        total_deleted_text_contents = 0

        # Convert specific time to Unix timestamp
        specific_time = datetime(2024, 3, 2, 10, 0,
                                 tzinfo=timezone(timedelta(hours=-5)))  # Eastern Standard Time (UTC-5)
        specific_time_unix = str(int(specific_time.timestamp()))

        while True:
            # Query for Webpage objects with 'CAL' university, limited by batch size (e.g., 100)
            webpages_result = (
                self.client.query
                .get("Jonahs_weaviate_infodb_Webpage",  # Use the correct class name
                     ["_additional { id, creationTimeUnix }", "url",
                      "textContents { ... on Jonahs_weaviate_infodb_TextContent { _additional { id } } }"])
                .with_where({
                    "path": ["university"],
                    "operator": "Equal",
                    "valueString": "CAL"
                })
                .with_limit(100)  # Adjust the limit as appropriate for your application
                .do()
            )

            webpages = webpages_result.get("data", {}).get("Get", {}).get("Jonahs_weaviate_infodb_Webpage", [])

            if not webpages:
                break  # Exit the loop if no more webpages are found

            for webpage in webpages:
                webpage_uuid = webpage["_additional"]["id"]
                webpage_url = webpage["url"]
                creationTimeUnix = webpage["_additional"]["creationTimeUnix"]

                CreationTimeUnix_seconds = int(creationTimeUnix) // 1000
                # Convert lastUpdateTimeUnix to integer and compare
                if int(CreationTimeUnix_seconds) < int(specific_time_unix):
                    # Delete related TextContent objects
                    if "textContents" in webpage and webpage["textContents"]:
                        for text_content in webpage["textContents"]:
                            text_content_uuid = text_content["_additional"]["id"]
                            self.client.data_object.delete(
                                class_name="Jonahs_weaviate_infodb_TextContent",  # Use the correct class name
                                uuid=text_content_uuid
                            )
                            total_deleted_text_contents += 1

                    # Delete the webpage object
                    self.client.data_object.delete(
                        class_name="Jonahs_weaviate_infodb_Webpage",  # Use the correct class name
                        uuid=webpage_uuid
                    )

                    print(f"Webpage with id {webpage_url} deleted")
                    total_deleted_webpages += 1

            # Optional: Add a short delay to avoid overwhelming the server
            time.sleep(0.5)

        print(f"Total TextContent objects deleted: {total_deleted_text_contents}")
        print(f"Total webpages from 'CAL' university before specific time deleted: {total_deleted_webpages}")

    def delete_webpages_containing_berkeley(self):
        """Delete all Webpage objects from Weaviate that contain 'berkeley' in their URL, along with their related TextContent objects."""
        total_deleted_webpages = 0
        total_deleted_text_contents = 0

        while True:
            # Query for Webpage objects with 'berkeley' in their URL, limited by batch size (e.g., 100)
            webpages_result = (
                self.client.query
                .get(Webpage.weaviate_class_name(namespace=self.namespace),
                     ["_additional { id }", "textContents { ... on Jonahs_weaviate_infodb_TextContent { _additional { id } } }"])
                .with_where({
                    "path": ["url"],
                    "operator": "Like",
                    "valueText": "*berkeley*"
                })
                .with_limit(100)  # Adjust the limit as appropriate for your application
                .do()
            )

            webpages = webpages_result["data"]["Get"][Webpage.weaviate_class_name(namespace=self.namespace)]

            if not webpages:
                break  # Exit the loop if no more webpages are found

            for webpage in webpages:
                webpage_uuid = webpage["_additional"]["id"]

                # Delete related TextContent objects
                if "textContents" in webpage and webpage["textContents"]:
                    for text_content in webpage["textContents"]:
                        text_content_uuid = text_content["_additional"]["id"]
                        self.client.data_object.delete(
                            class_name=TextContent.weaviate_class_name(namespace=self.namespace),
                            uuid=text_content_uuid
                        )
                        total_deleted_text_contents += 1

                # Delete the webpage object
                self.client.data_object.delete(
                    class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                    uuid=webpage_uuid
                )
                total_deleted_webpages += 1

            # Optional: Add a short delay to avoid overwhelming the server
            time.sleep(0.5)
            print(f"Total TextContent objects deleted: {total_deleted_text_contents}")

        print(f"Total TextContent objects deleted: {total_deleted_text_contents}")
        print(f"Total webpages containing 'berkeley' deleted: {total_deleted_webpages}")

    def create_embedding(self, text: str) -> list[list[float]]:
        """Get the embedding for a text using OpenAI Embedding API"""
        return self._embeddings_client.create_embedding(text=text)
