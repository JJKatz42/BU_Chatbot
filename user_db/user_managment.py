import uuid
import weaviate
import requests
import json
import tenacity
import tqdm
import hashlib
import BU_info_db.storage.storage_data_classes as data_classes

# Aliases for clarity
User = data_classes.User
Message = data_classes.Message
ProfileInformation = data_classes.ProfileInformation

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

class UserDatabaseManager:
    def __init__(self, instance_url: str, api_key: str, openai_api_key: str, cohere_api_key: str, namespace: str | None = None):
        weaviate.client.Batch = RetryableBatch
        self.client = weaviate.Client(
            url=instance_url,
            auth_client_secret=weaviate.AuthApiKey(api_key=api_key),
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key,
                "X-Cohere-Api-Key": cohere_api_key
            }
        )
        self.namespace = namespace

    def create_user_schema(self, delete_if_exists: bool = False):
        """Create schema for User, Message, and ProfileInformation in Weaviate"""
        user_related_classes = [User, Message, ProfileInformation]

        for user_class in user_related_classes:
            user_class_name = user_class.weaviate_class_name(namespace=self.namespace)
            if self.client.schema.exists(user_class_name):
                if delete_if_exists:
                    self.client.schema.delete_class(user_class_name)
                else:
                    raise Exception(f"Can't create schema because {user_class_name} already exists. "
                                    f"Set delete_if_exists=True to re-create the schema.")

        self.client.schema.create({
            "classes": [
                user_class.weaviate_class_schema(namespace=self.namespace)
                for user_class in user_related_classes
            ]
        })

    def insert_user(self, user: User):
        """Insert a new User into Weaviate"""
        self.client.data_object.create(
            class_name=User.weaviate_class_name(namespace=self.namespace),
            data_object=user.to_weaviate_object(),
            uuid=user.weaviate_id or str(uuid.uuid4())
        )

    def insert_message(self, message: Message):
        """Insert a new Message into Weaviate"""
        self.client.data_object.create(
            class_name=Message.weaviate_class_name(namespace=self.namespace),
            data_object=message.to_weaviate_object(),
            uuid=message.weaviate_id or str(uuid.uuid4())
        )

    def update_profile_information(self, user_id: str, new_profile_info: ProfileInformation):
        """Update the profile information of a given user"""
        profile_info_uuid = new_profile_info.weaviate_id or str(uuid.uuid4())

        # First, add the new ProfileInformation to Weaviate
        self.client.data_object.create(
            class_name=ProfileInformation.weaviate_class_name(namespace=self.namespace),
            data_object=new_profile_info.to_weaviate_object(),
            uuid=profile_info_uuid
        )

        # Then, update the user's ProfileInformation reference
        self.client.data_object.update(
            class_name=User.weaviate_class_name(namespace=self.namespace),
            uuid=user_id,
            data_object={
                "profileInformation": {
                    "beacon": f"weaviate://{self.namespace}/ProfileInformation/{profile_info_uuid}"
                }
            }
        )
