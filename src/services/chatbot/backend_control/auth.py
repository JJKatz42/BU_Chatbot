import random
import string
import urllib.parse


def generate_google_auth_url(client_id: str, redirect_uri: str) -> str:
    # Constants
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    client_id = client_id
    redirect_uri = redirect_uri
    scope = "openid profile email"  # These are the scopes you mentioned in your spec
    response_type = "code"

    # Generate a random state token
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # Construct the parameters
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": response_type,
        "state": state
    }

    # Construct the full URL
    auth_url = base_url + "?" + urllib.parse.urlencode(params)

    return auth_url
