import datetime
import uuid
import weaviate
import requests
import json
import tenacity
import user_db.user_data_classes as data_classes

# Aliases for clarity
User = data_classes.User
Conversation = data_classes.Conversation
UserMessage = data_classes.UserMessage
BotMessage = data_classes.BotMessage
ProfileInformation = data_classes.ProfileInformation
CrossReference = data_classes.CrossReference


class UserDatabaseManager:
    def __init__(
            self,
            instance_url: str,
            api_key: str,
            openai_api_key: str,
            cohere_api_key: str,
            namespace: str):
        self.client = weaviate.Client(
            url=instance_url,
            auth_client_secret=weaviate.AuthApiKey(api_key=api_key),
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key,
                "X-Cohere-Api-Key": cohere_api_key
            }
        )
        self.namespace = namespace

    def create_schema(self, delete_if_exists: bool = False):
        """Create schema for User, Message, and ProfileInformation in Weaviate"""
        user_related_classes = [User, Conversation, UserMessage, BotMessage, ProfileInformation]

        for user_class in user_related_classes:
            user_class_name = user_class.weaviate_class_name(namespace=self.namespace)
            if self.client.schema.exists(user_class_name):
                if delete_if_exists:
                    self.client.schema.delete_class(user_class_name)
                else:
                    raise Exception(f"Can't create schema because {user_class_name} already exists. "
                                    f"Set delete_if_exists=True to re-create the schema.")

        try:
            self.client.schema.create({
                "classes": [
                    user_class.weaviate_class_schema(namespace=self.namespace)
                    for user_class in user_related_classes
                ]
            })
        except Exception as e:
            print(f"Error creating schema: {e}")
            # Add further error handling or logging here as needed.

    def create_user(self, user: User) -> str:
        """
        Create a User in Weaviate and initialize a Conversation and ProfileInformation object for them
        Args:
            user: The User object to create in Weaviate

        Returns:
            The UUID of the created User object
        """
        user_uuid = ""
        try:
            user_uuid = self.client.data_object.create(
                class_name=User.weaviate_class_name(self.namespace),
                uuid=user.weaviate_id,
                data_object=user.to_weaviate_object()
            )
        except Exception as e:
            print(f"Error creating user: {e}")
            return user_uuid

        # Initialize an empty Conversation object and cross-reference it with the User
        for conversation in user.conversations:
            try:
                conversation_uuid = self.client.data_object.create(
                    class_name=Conversation.weaviate_class_name(self.namespace),
                    uuid=conversation.weaviate_id,
                    data_object=conversation.to_weaviate_object()
                )

                # Create a bi-directional cross-reference between User and Conversation
                self.client.data_object.reference.add(
                    from_class_name=user.weaviate_class_name(self.namespace),
                    from_uuid=user_uuid,
                    from_property_name="hasConversation",
                    to_class_name=conversation.weaviate_class_name(self.namespace),
                    to_uuid=conversation_uuid
                )


                self.client.data_object.reference.add(
                    from_class_name=conversation.weaviate_class_name(self.namespace),
                    from_uuid=conversation_uuid,
                    from_property_name="hasUser",
                    to_class_name=user.weaviate_class_name(self.namespace),
                    to_uuid=user_uuid
                )
            except Exception as e:
                print(f"Error creating conversation: {e}")

        # Placeholder for ProfileInformation linking, can be expanded as required
        # Currently, it initializes an empty list and does nothing further.

        return user_uuid

    def add_message(self, query_str: str, is_bad_query: bool, response_str: str, user_id: str):
        try:
            user_message = UserMessage(
                query_str=query_str,
                is_bad_query=is_bad_query,
                created_time=datetime.datetime.utcnow().isoformat()
            )

            bot_message = BotMessage(
                response_str=response_str,
                is_liked=True,
                created_time=datetime.datetime.utcnow().isoformat()
            )

            user_msg_id = self.client.data_object.create(
                user_message.to_weaviate_object(),
                user_message.weaviate_class_name(self.namespace)
            )

            bot_msg_id = self.client.data_object.create(
                bot_message.to_weaviate_object(),
                bot_message.weaviate_class_name(self.namespace)
            )

            # Link user message and bot message to the conversation associated with the user
            conversation_id = self._get_conversation_id(user_id)

            user_message_cross_ref = CrossReference(
                from_class=Conversation.weaviate_class_name(self.namespace),
                from_uuid=conversation_id,
                from_property="hasMessages",
                to_class=UserMessage.weaviate_class_name(self.namespace),
                to_uuid=user_msg_id
            )
            self._create_cross_reference(user_message_cross_ref)

            bot_message_cross_ref = CrossReference(
                from_class=Conversation.weaviate_class_name(self.namespace),
                from_uuid=conversation_id,
                from_property="hasMessages",
                to_class=BotMessage.weaviate_class_name(self.namespace),
                to_uuid=bot_msg_id
            )
            self._create_cross_reference(bot_message_cross_ref)

        except Exception as e:
            print(f"Error adding messages: {e}")


    def add_profile_information(self, user_id: str, profile_information: ProfileInformation):
        for profile_info in profile_information_list:
            try:
                profile_info_obj = profile_info.to_weaviate_object()
                self.client.data_object.create(profile_info_obj, profile_info.weaviate_class_name(self.namespace))
                try:
                    conversation_id = self.client.data_object.create(
                        conversation_obj,
                        conversation.weaviate_class_name(self.namespace),
                        conversation.weaviate_id
                    )
                except Exception as e:
                    print(f"Error creating conversation: {e}")
                    return user_id

                # Create a bi-directional cross-reference between User and Conversation
                user_conversation_cross_ref = CrossReference(
                    from_class=user.weaviate_class_name(self.namespace),
                    from_uuid=user_id,
                    from_property="hasConversation",
                    to_class=conversation.weaviate_class_name(self.namespace),
                    to_uuid=conversation_id
                )
                self._create_cross_reference(user_conversation_cross_ref)
                user_conversation_reverse_cross_ref = CrossReference(
                    from_class=conversation.weaviate_class_name(self.namespace),
                    from_uuid=conversation_id,
                    from_property="hasUser",
                    to_class=user.weaviate_class_name(self.namespace),
                    to_uuid=user_id
                )
                self._create_cross_reference(user_conversation_reverse_cross_ref)
            except Exception as e:
                print(f"Error creating profile information: {e}")

    def _create_cross_reference(self, cross_ref: CrossReference):
        """
        Create a cross-reference between two Weaviate objects based on the CrossReference object provided.
        """
        try:
            # Create the forward cross-reference
            self.client.data_object.reference.add(
                cross_ref.from_class,
                cross_ref.from_uuid,
                cross_ref.from_property,
                cross_ref.to_class,
                cross_ref.to_uuid
            )
        except Exception as e:
            print(f"Error creating cross-reference: {e}")

    def _get_conversation_id(self, user_id: str) -> str:
        """Get the Conversation UUID associated with a User"""
        try:
            user_data = self.client.data_object.get_by_id(
                user_id,
                User.weaviate_class_name(self.namespace)
            )
            return user_data["hasConversation"][0]["beacon"].split("/")[-1]
        except Exception as e:
            print(f"Error getting conversation ID: {e}")
            return ""

    def is_duplicate_user(self, gmail: str) -> bool:
        """Check if a Webpage object exists in Weaviate

        Returns:
            True if the Webpage object exists, False otherwise
        """
        results = (
            self.client.query
            .get(User.weaviate_class_name(namespace=self.namespace), ["gmail"])
            .with_where({"path": ["gmail"], "operator": "Equal", "valueText": gmail})
            .do()
        )

        if results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)] != []:
            return True

        return False

# When you integrate this into your main code, consider adding unit tests to ensure
# all methods work as expected.