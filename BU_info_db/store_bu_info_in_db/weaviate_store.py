import json
import uuid

import dateutil.parser
import requests
import tenacity
import tqdm
import weaviate


import data_classes
import embeddings


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
        # cohere_api_key: str,
        namespace: str | None = None
    ):
        weaviate.client.Batch = RetryableBatch
        self.client = weaviate.Client(
            url=instance_url,
            auth_client_secret=weaviate.AuthApiKey(api_key=api_key),
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key,
                # "X-Cohere-Api-Key": cohere_api_key
            }
        )
        self.client.batch.configure(
            batch_size=100,
            num_workers=4,
            timeout_retries=5,
            connection_error_retries=5
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


    def insert_webpage(self, webpages: list[Webpage]):
        # We build a list of the webpages we've inserted to refresh at the end to create the centroid vectors
        webpages_to_refresh_centroid_vector = []

        # Insert all data objects and references that support batching with batch
        print("Creating webpage objects in Weaviate")
        with self.client.batch as batch:
            # Compute the embeddings for all TextContents on each Webpage
            self._embeddings_client.create_weaviate_object_embeddings(webpages)

            for webpage in tqdm.tqdm(webpages, total=len(webpages), desc="Webpages"):
                # Add the webpage object
                webpage_uuid = batch.add_data_object(
                    class_name=Webpage.weaviate_class_name(namespace=self.namespace),
                    uuid=webpage.weaviate_id,
                    data_object=webpage.to_weaviate_object(),
                )
                webpages_to_refresh_centroid_vector.append(webpage_uuid)


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

        print("Created webpage objects and references in Weaviate")

        # Add the references from Webpage -> TextContent. These need to be added outside the batch because
        # ref2vec-centroid does not support batch updates
        print("Refreshing centroid vectors")
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
        print("Refreshed centroid vectors")

    def insert_references(self, references: list[CrossReference]):
        print("Creating references in Weaviate")
        with self.client.batch as batch:
            for reference in references:
                batch.add_reference(
                    from_object_class_name=reference.from_class,
                    from_object_uuid=reference.from_uuid,
                    from_property_name=reference.from_property,
                    to_object_class_name=reference.to_class,
                    to_object_uuid=reference.to_uuid
                )

        print("Created references in Weaviate")