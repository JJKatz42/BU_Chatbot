import random
import string
import urllib.parse


def generate_google_auth_url(client_id: str, redirect_uri: str) -> str:
    """
    Generate a Google OAuth2.0 authentication URL.

    This function creates an authentication URL for Google's OAuth2.0 endpoint.
    The generated URL is used to direct users for granting permissions
    and getting authorization codes.

    Args:
    - client_id (str): The client ID from the Google Developer Console.
    - redirect_uri (str): The URI where the user will be redirected after
                          granting/denying permission.

    Returns:
    - str: A fully formed Google OAuth2.0 authentication URL.

    Note:
    The 'state' parameter is a random string used to protect against
    cross-site request forgery attacks.
    """

    # Google's OAuth 2.0 endpoint.
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    # OAuth 2.0 scope. This specifies what data you want to access.
    scope = "openid profile email"

    # OAuth 2.0 response type. Here we want an authorization code.
    response_type = "code"

    # Generate a random state string for CSRF protection.
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # Set the query parameters for the authentication URL.
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": response_type,
        "state": state
    }

    # Construct the full authentication URL.
    auth_url = base_url + "?" + urllib.parse.urlencode(params)

    return auth_url
