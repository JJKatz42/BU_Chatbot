# coding: utf-8

"""
    Chatbot API with Google Authentication

    An API for interacting with our chatbot, providing feedback, and managing sessions.  # noqa: E501

    OpenAPI spec version: 1.0.2
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""

import pprint
import re  # noqa: F401

import six

class UserInfoResponse(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    """
    Attributes:
      swagger_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    swagger_types = {
        'token': 'str',
        'email': 'str',
        'first_name': 'str',
        'last_name': 'str'
    }

    attribute_map = {
        'token': 'token',
        'email': 'email',
        'first_name': 'first_name',
        'last_name': 'last_name'
    }

    def __init__(self, token=None, email=None, first_name=None, last_name=None):  # noqa: E501
        """UserInfoResponse - a model defined in Swagger"""  # noqa: E501
        self._token = None
        self._email = None
        self._first_name = None
        self._last_name = None
        self.discriminator = None
        if token is not None:
            self.token = token
        if email is not None:
            self.email = email
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name

    @property
    def token(self):
        """Gets the token of this UserInfoResponse.  # noqa: E501

        JWT token for the user.  # noqa: E501

        :return: The token of this UserInfoResponse.  # noqa: E501
        :rtype: str
        """
        return self._token

    @token.setter
    def token(self, token):
        """Sets the token of this UserInfoResponse.

        JWT token for the user.  # noqa: E501

        :param token: The token of this UserInfoResponse.  # noqa: E501
        :type: str
        """

        self._token = token

    @property
    def email(self):
        """Gets the email of this UserInfoResponse.  # noqa: E501

        User's email address.  # noqa: E501

        :return: The email of this UserInfoResponse.  # noqa: E501
        :rtype: str
        """
        return self._email

    @email.setter
    def email(self, email):
        """Sets the email of this UserInfoResponse.

        User's email address.  # noqa: E501

        :param email: The email of this UserInfoResponse.  # noqa: E501
        :type: str
        """

        self._email = email

    @property
    def first_name(self):
        """Gets the first_name of this UserInfoResponse.  # noqa: E501

        User's first name.  # noqa: E501

        :return: The first_name of this UserInfoResponse.  # noqa: E501
        :rtype: str
        """
        return self._first_name

    @first_name.setter
    def first_name(self, first_name):
        """Sets the first_name of this UserInfoResponse.

        User's first name.  # noqa: E501

        :param first_name: The first_name of this UserInfoResponse.  # noqa: E501
        :type: str
        """

        self._first_name = first_name

    @property
    def last_name(self):
        """Gets the last_name of this UserInfoResponse.  # noqa: E501

        User's last name.  # noqa: E501

        :return: The last_name of this UserInfoResponse.  # noqa: E501
        :rtype: str
        """
        return self._last_name

    @last_name.setter
    def last_name(self, last_name):
        """Sets the last_name of this UserInfoResponse.

        User's last name.  # noqa: E501

        :param last_name: The last_name of this UserInfoResponse.  # noqa: E501
        :type: str
        """

        self._last_name = last_name

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(UserInfoResponse, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, UserInfoResponse):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
