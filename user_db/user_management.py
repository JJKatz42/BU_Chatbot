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

    def insert_message(self, user_message: UserMessage, bot_message: BotMessage, gmail: str):
        user_message_uuid = ""
        bot_message_uuid = ""
        conversation_uuid = ""

        try:
            self.client.schema.property.create(BotMessage.weaviate_class_name(self.namespace), {
                "name": "hasConversation",
                "dataType": [Conversation.weaviate_class_name(self.namespace)]
            })

            self.client.schema.property.create(UserMessage.weaviate_class_name(self.namespace), {
                "name": "hasConversation",
                "dataType": [Conversation.weaviate_class_name(self.namespace)]
            })

            self.client.schema.property.create(UserMessage.weaviate_class_name(self.namespace), {
                "name": "hasBotMessage",
                "dataType": [BotMessage.weaviate_class_name(self.namespace)]
            })

            self.client.schema.property.create(BotMessage.weaviate_class_name(self.namespace), {
                "name": "hasUserMessage",
                "dataType": [UserMessage.weaviate_class_name(self.namespace)]
            })
        except Exception as e:
            print(f"Error creating properties (doesn't matter tho): {e}")

        try:
            results = (
                self.client.query
                .get(User.weaviate_class_name(namespace=self.namespace), ["gmail", "hasConversation {... on Jonahs_weaviate_userdb_Conversation { _additional { id } } }"])
                .with_where({"path": ["gmail"], "operator": "Equal", "valueText": gmail})
                .do()
            )

            if results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)] != [] or results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)][0]["hasConversation"] != []:
                conversation_uuid = results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)][0]["hasConversation"][0]["_additional"]["id"]
        except Exception as e:
            print(f"Error getting conversation ID: {e}")

        try:
            user_message_uuid = self.client.data_object.create(
                class_name=UserMessage.weaviate_class_name(self.namespace),
                uuid=user_message.weaviate_id,
                data_object=user_message.to_weaviate_object()
            )
        except Exception as e:
            print(f"Error adding user_message: {e}")

        try:
            # Create a bot message
            bot_message_uuid = self.client.data_object.create(
                class_name=BotMessage.weaviate_class_name(self.namespace),
                uuid=bot_message.weaviate_id,
                data_object=bot_message.to_weaviate_object()
            )

            # Create a bi-directional cross-reference between UserMessage and BotMessage
            self.client.data_object.reference.add(
                from_class_name=user_message.weaviate_class_name(self.namespace),
                from_uuid=user_message_uuid,
                from_property_name="hasBotMessage",
                to_class_name=bot_message.weaviate_class_name(self.namespace),
                to_uuid=bot_message_uuid
            )

            self.client.data_object.reference.add(
                from_class_name=bot_message.weaviate_class_name(self.namespace),
                from_uuid=bot_message_uuid,
                from_property_name="hasUserMessage",
                to_class_name=user_message.weaviate_class_name(self.namespace),
                to_uuid=user_message_uuid
            )
        except Exception as e:
            print(f"Error adding bot messages and creating references: {e}")

        try:
            # Create a bi-directional cross-reference between UserMessage and BotMessage with Conversation

            print("Conversation class name: ", Conversation.weaviate_class_name(namespace=self.namespace))
            print("Conversation UUID: ", conversation_uuid)

            self.client.data_object.reference.add(
                from_class_name=user_message.weaviate_class_name(self.namespace),
                from_uuid=user_message_uuid,
                from_property_name="hasConversation",
                to_class_name=Conversation.weaviate_class_name(namespace=self.namespace),  # check dis
                to_uuid=conversation_uuid
            )

            self.client.data_object.reference.add(
                from_class_name=Conversation.weaviate_class_name(self.namespace),
                from_uuid=conversation_uuid,
                from_property_name="messages",
                to_class_name=UserMessage.weaviate_class_name(namespace=self.namespace),  # check dis
                to_uuid=user_message_uuid
            )

            self.client.data_object.reference.add(
                from_class_name=bot_message.weaviate_class_name(self.namespace),
                from_uuid=bot_message_uuid,
                from_property_name="hasConversation",
                to_class_name=Conversation.weaviate_class_name(namespace=self.namespace),  # check dis
                to_uuid=conversation_uuid
            )

            self.client.data_object.reference.add(
                from_class_name=Conversation.weaviate_class_name(self.namespace),
                from_uuid=conversation_uuid,
                from_property_name="messages",
                to_class_name=BotMessage.weaviate_class_name(namespace=self.namespace),  # check dis
                to_uuid=bot_message_uuid
            )

        except Exception as e:
            print(f"Error creating references between messages and conversation: {e}")


# def add_profile_information(self, user_id: str, profile_information: ProfileInformation):
#         for profile_info in profile_information_list:
#             try:
#                 profile_info_obj = profile_info.to_weaviate_object()
#                 self.client.data_object.create(profile_info_obj, profile_info.weaviate_class_name(self.namespace))
#                 try:
#                     conversation_id = self.client.data_object.create(
#                         conversation_obj,
#                         conversation.weaviate_class_name(self.namespace),
#                         conversation.weaviate_id
#                     )
#                 except Exception as e:
#                     print(f"Error creating conversation: {e}")
#                     return user_id
#
#                 # Create a bi-directional cross-reference between User and Conversation
#                 user_conversation_cross_ref = CrossReference(
#                     from_class=user.weaviate_class_name(self.namespace),
#                     from_uuid=user_id,
#                     from_property="hasConversation",
#                     to_class=conversation.weaviate_class_name(self.namespace),
#                     to_uuid=conversation_id
#                 )
#                 self._create_cross_reference(user_conversation_cross_ref)
#                 user_conversation_reverse_cross_ref = CrossReference(
#                     from_class=conversation.weaviate_class_name(self.namespace),
#                     from_uuid=conversation_id,
#                     from_property="hasUser",
#                     to_class=user.weaviate_class_name(self.namespace),
#                     to_uuid=user_id
#                 )
#                 self._create_cross_reference(user_conversation_reverse_cross_ref)
#             except Exception as e:
#                 print(f"Error creating profile information: {e}")

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

    def get_messages(self):
        # Fetch the conversations associated with the user based on Gmail
        results = (
            self.client.query
            .get(User.weaviate_class_name(namespace=self.namespace), ["hasConversation {... on Jonahs_weaviate_userdb_Conversation { messages { ... on Jonahs_weaviate_userdb_UserMessage { query_str, created_time } ... on Jonahs_weaviate_userdb_BotMessage { response_str, created_time } } } }"])
            .do()
        )

        # Extract and print the messages
        message_objects = results['data']['Get'][User.weaviate_class_name(namespace=self.namespace)][0]['hasConversation'][0]['messages']
        if not message_objects:
            print(f"No User object found with Gmail: ")
            return

        for message in message_objects:
            if 'query_str' in message:
                print(f" query_str = {message['query_str']}")  # Print user message content
            elif 'response_str' in message:
                print(f" response_str = {message['response_str']}")  # Print bot message text

# When you integrate this into your main code, consider adding unit tests to ensure
# all methods work as expected.
