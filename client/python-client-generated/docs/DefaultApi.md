# swagger_client.DefaultApi

All URIs are relative to *https://api.yourdomain.com/v1*

Method | HTTP request | Description
------------- | ------------- | -------------
[**auth_callback_get**](DefaultApi.md#auth_callback_get) | **GET** /auth/callback | Callback endpoint for Google&#x27;s OAuth 2.0 authentication
[**chat_post**](DefaultApi.md#chat_post) | **POST** /chat | Send a question to the chatbot
[**chat_response_id_result_get**](DefaultApi.md#chat_response_id_result_get) | **GET** /chat/{responseID}/result | Poll for the chatbot&#x27;s response using the responseID
[**feedback_post**](DefaultApi.md#feedback_post) | **POST** /feedback | Provide feedback on the chatbot&#x27;s response
[**login_get**](DefaultApi.md#login_get) | **GET** /login | Redirect to Google&#x27;s OAuth 2.0 authentication

# **auth_callback_get**
> UserInfoResponse auth_callback_get(code)

Callback endpoint for Google's OAuth 2.0 authentication

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure OAuth2 access token for authorization: GoogleOAuth
configuration = swagger_client.Configuration()
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# create an instance of the API class
api_instance = swagger_client.DefaultApi(swagger_client.ApiClient(configuration))
code = 'code_example' # str | Authorization code from Google.

try:
    # Callback endpoint for Google's OAuth 2.0 authentication
    api_response = api_instance.auth_callback_get(code)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->auth_callback_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **code** | **str**| Authorization code from Google. | 

### Return type

[**UserInfoResponse**](UserInfoResponse.md)

### Authorization

[BearerToken](../README.md#BearerToken), [GoogleOAuth](../README.md#GoogleOAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **chat_post**
> IncompleteResponse chat_post(body, authorization)

Send a question to the chatbot

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure OAuth2 access token for authorization: GoogleOAuth
configuration = swagger_client.Configuration()
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# create an instance of the API class
api_instance = swagger_client.DefaultApi(swagger_client.ApiClient(configuration))
body = swagger_client.ChatRequestWithSession() # ChatRequestWithSession | 
authorization = 'authorization_example' # str | JWT token for authentication.

try:
    # Send a question to the chatbot
    api_response = api_instance.chat_post(body, authorization)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->chat_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ChatRequestWithSession**](ChatRequestWithSession.md)|  | 
 **authorization** | **str**| JWT token for authentication. | 

### Return type

[**IncompleteResponse**](IncompleteResponse.md)

### Authorization

[BearerToken](../README.md#BearerToken), [GoogleOAuth](../README.md#GoogleOAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **chat_response_id_result_get**
> ChatResponse chat_response_id_result_get(response_id)

Poll for the chatbot's response using the responseID

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure OAuth2 access token for authorization: GoogleOAuth
configuration = swagger_client.Configuration()
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# create an instance of the API class
api_instance = swagger_client.DefaultApi(swagger_client.ApiClient(configuration))
response_id = 'response_id_example' # str | The unique ID of the chatbot's initial acknowledgment.

try:
    # Poll for the chatbot's response using the responseID
    api_response = api_instance.chat_response_id_result_get(response_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->chat_response_id_result_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **response_id** | **str**| The unique ID of the chatbot&#x27;s initial acknowledgment. | 

### Return type

[**ChatResponse**](ChatResponse.md)

### Authorization

[BearerToken](../README.md#BearerToken), [GoogleOAuth](../README.md#GoogleOAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **feedback_post**
> feedback_post(body, authorization)

Provide feedback on the chatbot's response

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure OAuth2 access token for authorization: GoogleOAuth
configuration = swagger_client.Configuration()
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# create an instance of the API class
api_instance = swagger_client.DefaultApi(swagger_client.ApiClient(configuration))
body = swagger_client.FeedbackRequest() # FeedbackRequest | 
authorization = 'authorization_example' # str | JWT token for authentication.

try:
    # Provide feedback on the chatbot's response
    api_instance.feedback_post(body, authorization)
except ApiException as e:
    print("Exception when calling DefaultApi->feedback_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**FeedbackRequest**](FeedbackRequest.md)|  | 
 **authorization** | **str**| JWT token for authentication. | 

### Return type

void (empty response body)

### Authorization

[BearerToken](../README.md#BearerToken), [GoogleOAuth](../README.md#GoogleOAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **login_get**
> login_get()

Redirect to Google's OAuth 2.0 authentication

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure OAuth2 access token for authorization: GoogleOAuth
configuration = swagger_client.Configuration()
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# create an instance of the API class
api_instance = swagger_client.DefaultApi(swagger_client.ApiClient(configuration))

try:
    # Redirect to Google's OAuth 2.0 authentication
    api_instance.login_get()
except ApiException as e:
    print("Exception when calling DefaultApi->login_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

[BearerToken](../README.md#BearerToken), [GoogleOAuth](../README.md#GoogleOAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

