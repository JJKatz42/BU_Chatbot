import weaviate
import src.libs.storage.user_data_classes as data_classes
import src.libs.logging as logging


logger = logging.getLogger(__name__)


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
        self.openai_api_key = openai_api_key

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
            logger.error(f"Error creating schema: {e}")
            # Add further error handling or logging here as needed.

        try:
            self.client.schema.property.create(User.weaviate_class_name(self.namespace), {
                "name": "hasConversation",
                "dataType": [Conversation.weaviate_class_name(self.namespace)]
            })
        except:
            pass

        try:
            self.client.schema.property.create(User.weaviate_class_name(self.namespace), {
                "name": "hasProfileInformation",
                "dataType": [ProfileInformation.weaviate_class_name(self.namespace)]
            })
        except:
            pass

        try:
            self.client.schema.property.create(ProfileInformation.weaviate_class_name(self.namespace), {
                "name": "hasUser",
                "dataType": [User.weaviate_class_name(self.namespace)]
            })

        except:
            pass

        try:
            self.client.schema.property.create(Conversation.weaviate_class_name(self.namespace), {
                "name": "messages",
                "dataType": [
                        UserMessage.weaviate_class_name(namespace=self.namespace),
                        BotMessage.weaviate_class_name(namespace=self.namespace)
                    ]
            })
        except:
            pass
        try:
            self.client.schema.property.create(Conversation.weaviate_class_name(self.namespace), {
                "name": "hasUser",
                "dataType": [User.weaviate_class_name(self.namespace)]
            })
        except:
            pass

        try:
            self.client.schema.property.create(UserMessage.weaviate_class_name(self.namespace), {
                "name": "hasBotMessage",
                "dataType": [BotMessage.weaviate_class_name(self.namespace)]
            })

        except:
            pass

        try:
            self.client.schema.property.create(UserMessage.weaviate_class_name(self.namespace), {
                "name": "hasConversation",
                "dataType": [Conversation.weaviate_class_name(self.namespace)]
            })

        except:
            pass

        try:
            self.client.schema.property.create(BotMessage.weaviate_class_name(self.namespace), {
                "name": "hasUserMessage",
                "dataType": [UserMessage.weaviate_class_name(self.namespace)]
            })
        except:
            pass


        try:
            self.client.schema.property.create(BotMessage.weaviate_class_name(self.namespace), {
                "name": "hasConversation",
                "dataType": [Conversation.weaviate_class_name(self.namespace)]
            })
        except:
            pass


    def user_exists(self, gmail: str) -> bool:
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

        if results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)]:
            return True

        return False

    def create_user(self, user: User) -> bool:
        """
        Create a User in Weaviate and initialize a Conversation and ProfileInformation object for them
        Args:
            user: The User object to create in Weaviate

        Returns:
            The UUID of the created User object
        """
        if self.user_exists(gmail=user.gmail):
            logger.warning(f"User with Gmail {user.gmail} already exists")
            return True

        else:
            try:
                user_uuid = self.client.data_object.create(
                    class_name=User.weaviate_class_name(self.namespace),
                    uuid=user.weaviate_id,
                    data_object=user.to_weaviate_object()
                )
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                return False

            # Initialize an empty Conversation object and cross-reference it with the User
            for conversation in user.conversations:
                try:
                    conversation_uuid = self.client.data_object.create(
                        class_name=Conversation.weaviate_class_name(self.namespace),
                        uuid=conversation.weaviate_id,
                        data_object=conversation.to_weaviate_object()
                    )

                    # Create a bidirectional cross-reference between User and Conversation
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
                    logger.error(f"Error creating conversation: {e}")
                    self.client.data_object.delete(user_uuid)
                    return False

        return True

    def insert_message(self, user_message: UserMessage, bot_message: BotMessage, gmail: str):
        user_message_uuid = ""
        bot_message_uuid = ""
        conversation_uuid = ""

        try:
            conversation_uuid = self._get_conversation_id(gmail=gmail)
        except Exception as e:
            logger.error(f"Error getting conversation ID: {e}")

        try:
            user_message_uuid = self.client.data_object.create(
                class_name=UserMessage.weaviate_class_name(self.namespace),
                uuid=user_message.weaviate_id,
                data_object=user_message.to_weaviate_object()
            )
        except Exception as e:
            logger.error(f"Error adding user_message: {e}")

        try:
            # Create a bot message
            bot_message_uuid = self.client.data_object.create(
                class_name=BotMessage.weaviate_class_name(self.namespace),
                uuid=bot_message.weaviate_id,
                data_object=bot_message.to_weaviate_object()
            )

            # Create a bidirectional cross-reference between UserMessage and BotMessage
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
            logger.error(f"Error adding bot messages and creating references: {e}")

        try:
            # Create a bidirectional cross-reference between UserMessage and BotMessage with Conversation
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
            logger.error(f"Error creating references between messages and conversation: {e}")

        return bot_message_uuid

    def insert_bad_query(self, query_str: str, gmail: str):
        pass
        # TODO


    def insert_liked(self, liked: bool, bot_message_id: str):
        try:
            current_liked_state = self._get_current_liked_state(bot_message_id=bot_message_id)
            if current_liked_state == str(liked):
                self.client.data_object.update(
                    uuid=bot_message_id,
                    class_name=BotMessage.weaviate_class_name(self.namespace),
                    data_object={
                        'is_liked': None,
                    },
                )
            else:
                self.client.data_object.update(
                    uuid=bot_message_id,
                    class_name=BotMessage.weaviate_class_name(self.namespace),
                    data_object={
                        'is_liked': str(liked),
                    },
                )

        except Exception as e:
            logger.error(f"Error inserting liked message: {e}")
            return ""

    # def is_bad_query(self, query_str: str):
    #     # openai.api_key = self.openai_api_key
    #     # try:
    #     #     completion = openai.ChatCompletion.create(
    #     #         model="gpt-3.5-turbo",
    #     #         temperature=0,
    #     #         messages=[
    #     #             {"role": "system", "content": "You are a competant University chatbot. You can only respond with True or False. You're job is to determine whether a student's question is related to any topic corresponding to their university. You are given a question if it is not related to any aspect of a university then respond with 'False' if it is related to any aspect of a university response with 'True'."},
    #     #             {"role": "user", "content": query_str}
    #     #         ]
    #     #     )
    #     #
    #     #     logger.info(completion.choices[0].message)
    #     #     return completion.choices[0].message["content"]
    #     # except Exception as e:
    #     #     logger.error(e)
    #     #     return "Couldn't do it"
    #     return "True"

    def get_messages_for_user(self, gmail: str):
        """
        Get the messages for a user based on their Gmail

        Args:
            gmail: The Gmail of the user whose messages to get

        Returns:
            A list of messages for the user
        """

        message_list = []
        # Fetch the conversations associated with the user based on Gmail
        results = (
            self.client.query
            .get(User.weaviate_class_name(namespace=self.namespace), ["hasConversation {... on Jonahs_weaviate_userdb_Conversation { messages { ... on Jonahs_weaviate_userdb_UserMessage { query_str, _additional { id }, hasBotMessage {... on Jonahs_weaviate_userdb_BotMessage { response_str, _additional { id } } } } } } }"])
            .with_where({"path": ["gmail"], "operator": "Equal", "valueText": gmail})
            .do()
        )

        # Extract and log the messages
        try:
            message_objects = results['data']['Get'][User.weaviate_class_name(namespace=self.namespace)][0]['hasConversation'][0]['messages']
            if message_objects == []:
                logger.info(f"No messages for user {gmail}: {message_objects}")

            else:
                for message in message_objects:

                    tup = []
                    u_tup = []
                    b_tup = []

                    u_tup.append(message['query_str'])
                    u_tup.append(message['_additional']['id'])

                    b_tup.append(message['hasBotMessage'][0]['response_str'])
                    b_tup.append(message['hasBotMessage'][0]['_additional']['id'])

                    tup.append(u_tup)
                    tup.append(b_tup)

                    message_list.append(tup)

                return message_list

        except Exception as e:
            logger.warning(f"No User object found with the Gmail: {gmail}")
            return message_list

    def clear_conversation(self, gmail: str):
        """
        Clear the conversation for a user based on their Gmail

        Args:
            gmail: The Gmail of the user whose conversation to clear
        """
        try:
            conversation_id = self._get_conversation_id(gmail=gmail)

            self.client.data_object.update(
                uuid=conversation_id,
                class_name=Conversation.weaviate_class_name(self.namespace),
                data_object={
                    'messages': None,
                },
            )

            self.client.data_object.update(
                uuid=conversation_id,
                class_name=Conversation.weaviate_class_name(self.namespace),
                data_object={
                    'messages': [],
                },
            )
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")

        results = (
            self.client.query
            .get(User.weaviate_class_name(namespace=self.namespace), [
                "hasConversation {... on Jonahs_weaviate_userdb_Conversation { messages { ... on Jonahs_weaviate_userdb_UserMessage { query_str, created_time } ... on Jonahs_weaviate_userdb_BotMessage { response_str, created_time } } } }"])
            .with_where({"path": ["gmail"], "operator": "Equal", "valueText": gmail})
            .do()
        )

        logger.info(results['data']['Get'][User.weaviate_class_name(namespace=self.namespace)][0]['hasConversation'][0]['messages'])

    def insert_profile_info(self, gmail: str, profile_info_lst: [ProfileInformation]):
        """
        Insert profile information for a user based on their Gmail

        Args:
            gmail: The Gmail of the user whose profile information to insert
            profile_info_lst: The list of profile information to insert
        """
        user_uuid = ""

        try:
            self.client.schema.property.create(ProfileInformation.weaviate_class_name(self.namespace), {
                "name": "hasUser",
                "dataType": [User.weaviate_class_name(self.namespace)]
            })
        except Exception as e:
            logger.error(f"Error creating properties (doesn't matter tho): {e}")

        try:
            user_uuid = self._get_user_id(gmail=gmail)
        except Exception as e:
            logger.error(f"Error getting conversation ID: {e}")

        try:
            for profile_information in profile_info_lst:


                profile_information_uuid = self.client.data_object.create(
                    class_name=ProfileInformation.weaviate_class_name(self.namespace),
                    uuid=profile_information.weaviate_id,
                    data_object=profile_information.to_weaviate_object()
                )

                # Create a bidirectional cross-reference between all profile information and the user
                self.client.data_object.reference.add(
                    from_class_name=profile_information.weaviate_class_name(self.namespace),
                    from_uuid=profile_information_uuid,
                    from_property_name="hasUser",
                    to_class_name=User.weaviate_class_name(self.namespace),
                    to_uuid=user_uuid
                )

                self.client.data_object.reference.add(
                    from_class_name=User.weaviate_class_name(self.namespace),
                    from_uuid=user_uuid,
                    from_property_name="hasProfileInformation",
                    to_class_name=profile_information.weaviate_class_name(self.namespace),
                    to_uuid=profile_information_uuid
                )

        except Exception as e:
            logger.error(f"Error adding user_message: {e}")

    def get_profile_info_for_user(self, gmail: str):
        """
        Get the profile information for a user based on their Gmail

        Args:
            gmail: The Gmail of the user whose profile information to get

        Returns:
            A dictionary of profile information for the user
        """
        profile_info_dict = {}
        # Fetch the conversations associated with the user based on Gmail
        results = (
            self.client.query
            .get(User.weaviate_class_name(namespace=self.namespace), [
                "hasProfileInformation {... on Jonahs_weaviate_userdb_ProfileInformation { key, value } }"])
            .with_where({"path": ["gmail"], "operator": "Equal", "valueText": gmail})
            .do()
        )

        # Extract and return profile information
        profile_info_objects = results['data']['Get'][User.weaviate_class_name(namespace=self.namespace)][0]['hasProfileInformation']
        if not profile_info_objects:
            logger.warning(f"No User object found with the Gmail: {gmail}")
            return profile_info_dict

        else:
            for profile_info in profile_info_objects:
                profile_info_dict[profile_info['key']] = profile_info['value']

            return profile_info_dict

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
            logger.error(f"Error creating cross-reference: {e}")

    def _get_conversation_id(self, gmail: str):
        """
        Get the conversation ID for a user based on their Gmail

        Args:
            gmail: The Gmail of the user whose conversation ID to get

        Returns:
            The conversation ID of the user
        """
        conversation_uuid = ""

        results = (
            self.client.query
            .get(User.weaviate_class_name(namespace=self.namespace),
                 ["gmail", "hasConversation {... on Jonahs_weaviate_userdb_Conversation { _additional { id } } }"])
            .with_where({"path": ["gmail"], "operator": "Equal", "valueText": gmail})
            .do()
        )

        if results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)][0]["hasConversation"]:
            conversation_uuid = results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)][0][
                'hasConversation'][0]["_additional"]["id"]

        return conversation_uuid

    def _get_user_id(self, gmail: str):
        """
        Get the user ID for a user based on their Gmail

        Args:
            gmail: The Gmail of the user whose user ID to get

        Returns:
            The user ID of the user
        """
        user_uuid = ""

        results = (
            self.client.query
            .get(User.weaviate_class_name(namespace=self.namespace),
                 ["gmail", "_additional { id }"])
            .with_where({"path": ["gmail"], "operator": "Equal", "valueText": gmail})
            .do()
        )

        if results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)]:
            user_uuid = results["data"]["Get"][User.weaviate_class_name(namespace=self.namespace)][0][
                '_additional']['id']

        return user_uuid

    def _get_current_liked_state(self, bot_message_id: str):
        try:
            results = (
                self.client.query
                .get(BotMessage.weaviate_class_name(namespace=self.namespace), ["is_liked"])
                .with_where({"path": ["id"], "operator": "Equal", "valueText": bot_message_id})
                .do()
            )

            result = results["data"]["Get"][BotMessage.weaviate_class_name(namespace=self.namespace)][0]["is_liked"]

            return result
        except Exception as e:
            logger.error(f"Error getting bot message with that ID: {e}")
            return ""
