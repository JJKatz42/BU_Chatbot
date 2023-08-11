import uuid
import weaviate
import requests
import json
import tenacity
import tqdm
import hashlib
import user_db.user_data_classes as data_classes

# Aliases for clarity
User = data_classes.User
Conversation = data_classes.Conversation
UserQuery = data_classes.UserQuery
BotResponse = data_classes.BotResponse
ProfileInformation = data_classes.ProfileInformation
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

class UserDatabaseManager:
    def __init__(
            self,
            instance_url: str,
            api_key: str,
            openai_api_key: str,
            cohere_api_key: str,
            namespace: str | None = None):
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
            timeout_retries=5,
            connection_error_retries=5
        )
        self.namespace = namespace

    def create_user_schema(self, delete_if_exists: bool = False):
        """Create schema for User, Message, and ProfileInformation in Weaviate"""
        user_related_classes = [User, Conversation, UserMessage, BotMessage ProfileInformation]

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
        with self.client.batch as batch:
            user_uuid = batch.add_data_object(
                class_name=User.weaviate_class_name(namespace=self.namespace),
                data_object=user.to_weaviate_object(),
                uuid=user.weaviate_id or str(uuid.uuid4())
            )

            for conversation in user.conversations:
                conversation_uuid = batch.add_data_object(
                    class_name=Conversation.weaviate_class_name(namespace=self.namespace),
                    uuid=conversation.weaviate_id,
                    data_object=conversation.to_weaviate_object()
                )
                batch.add_reference(
                    from_object_class_name=User.weaviate_class_name(namespace=self.namespace),
                    from_object_uuid=user_uuid,
                    from_property_name="hasConversation",
                    to_object_class_name=Conversation.weaviate_class_name(namespace=self.namespace),
                    to_object_uuid=conversation_uuid
                )
                batch.add_reference(
                    from_object_class_name=Conversation.weaviate_class_name(namespace=self.namespace),
                    from_object_uuid=conversation_uuid,
                    from_property_name="hasUser",
                    to_object_class_name=User.weaviate_class_name(namespace=self.namespace),
                    to_object_uuid=user_uuid
                )



            for profile_info in user.profile_information:
                profile_info_uuid = batch.add_data_object(
                    class_name=ProfileInformation.weaviate_class_name(namespace=self.namespace),
                    data_object=profile_info.to_weaviate_object(),
                    uuid=profile_info.weaviate_id or str(uuid.uuid4())
                )

                batch.add_reference(
                    from_object_class_name=User.weaviate_class_name(namespace=self.namespace),
                    from_object_uuid=user_uuid,
                    from_property_name="hasProfileInformation",
                    to_object_class_name=ProfileInformation.weaviate_class_name(namespace=self.namespace),
                    to_object_uuid=profile_info_uuid
                )

                batch.add_reference(
                    from_object_class_name=ProfileInformation.weaviate_class_name(namespace=self.namespace),
                    from_object_uuid=profile_info_uuid,
                    from_property_name="hasUser",
                    to_object_class_name=User.weaviate_class_name(namespace=self.namespace),
                    to_object_uuid=user_uuid
                )

        # update user with conversation and profile information references
        self.client.data_object.update(
            class_name=User.weaviate_class_name(namespace=self.namespace),
            uuid=user_uuid,
            data_object={
                "hasConversation": []
            }
        )

        self.client.data_object.update(
            class_name=User.weaviate_class_name(namespace=self.namespace),
            uuid=user_uuid,
            data_object={
                "hasProfileInformation": []
            }
        )

    def insert_message(self, query: UserQuery, response: BotResponse, user_id: str):
        """Insert a new Message into Weaviate"""
        with self.client.batch as batch:
            query_uuid = batch.add_data_object(
                class_name=UserMessage.weaviate_class_name(namespace=self.namespace),
                data_object=query.to_weaviate_object(),
                uuid=query.weaviate_id or str(uuid.uuid4())
            )

            response_uuid = batch.add_data_object(
                class_name=BotResponse.weaviate_class_name(namespace=self.namespace),
                data_object=response.to_weaviate_object(),
                uuid=response.weaviate_id or str(uuid.uuid4())
            )

            batch.add_reference(
                from_object_class_name=UserQuery.weaviate_class_name(namespace=self.namespace),
                from_object_uuid=query_uuid,
                from_property_name="hasResponse",
                to_object_class_name=BotResponse.weaviate_class_name(namespace=self.namespace),
                to_object_uuid=response_uuid
            )

            batch.add_reference(
                from_object_class_name=BotResponse.weaviate_class_name(namespace=self.namespace),
                from_object_uuid=response_uuid,
                from_property_name="hasQuery",
                to_object_class_name=UserQuery.weaviate_class_name(namespace=self.namespace),
                to_object_uuid=query_uuid
            )
        # update user with conversation and profile information references
        self.client.data_object.update(
            class_name=UserMessage.weaviate_class_name(namespace=self.namespace),
            uuid=query_uuid,
            data_object={
                "hasConversation": []
            }
        )

        self.client.data_object.update(
            class_name=UserMessage.weaviate_class_name(namespace=self.namespace),
            uuid=query_uuid,
            data_object={
                "hasResponse": []
            }
        )

        self.client.data_object.update(
            class_name=BotMessage.weaviate_class_name(namespace=self.namespace),
            uuid=query_uuid,
            data_object={
                "hasConversation": []
            }
        )

        self.client.data_object.update(
            class_name=BotMessage.weaviate_class_name(namespace=self.namespace),
            uuid=query_uuid,
            data_object={
                "hasQuery": []
            }
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
