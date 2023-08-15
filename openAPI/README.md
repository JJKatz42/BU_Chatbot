# OpenAPI specification for the API used by the beta version of BUsearch

## Breakdown of the API
### Metadata Information:
- OpenAPI version used: 3.0.0
- API title: Chatbot API with Google Authentication
- API description: An interface for interacting with a chatbot, obtaining feedback, and managing sessions.
- Version: 1.0.2 
- External documentation link: https://example.com

### Server Information:
- Base URL for the API: https://api.yourdomain.com/v1

### Paths/Endpoints:
- **Login Endpoint (/login)**:
  - **GET**: Redirects users to Google's OAuth 2.0 authentication. 
  - Expected responses include a successful redirection, unauthorized, bad request, forbidden, and internal server error.
- **Chat Endpoint (/chat):**

  - **POST**: Allows users to send questions to the chatbot.
  - Accepts a JSON payload with a `sessionID` and `question`. 
  - Expected responses include processing being incomplete, bad request, unauthorized, too many requests, and internal server error. 

- **Chat Response Polling Endpoint (/chat/{responseID}/result):**
  - **GET**: Polls for the chatbot's response using a given responseID. 
  - Requires `responseID` in the path and `sessionID` in the header. 
  - Expected responses include a successful response, processing ongoing, responseID not found, unauthorized, and internal server error. 
- **Feedback Endpoint (/feedback):**
  - **POST**: Enables users to provide feedback on the chatbot's response. 
  - Accepts a JSON payload with `responseID` and a boolean value `liked`. 
  - Expected responses include feedback recorded successfully, bad request, unauthorized, and internal server error.
### Components:
- **Schemas**:
  - **ChatRequestWithSession**: Describes a chat request containing a session ID and a user question. 
  - **ChatResponse**: Represents the chatbot's response and its unique ID. 
  - **FeedbackRequest**: Represents user feedback on the chatbot's response. 
  - **ErrorResponse**: Represents error information with a message and a code. 
  - **IncompleteResponse**: Represents a response requiring further information or clarification from the user. 
- **Security Schemes**:
  - **GoogleOAuth**: An implicit OAuth2 flow with Google authentication. Includes scopes for Google login (`openid`) and profile information (`profile`).

### Security:
- The API is secured using the Google OAuth implicit flow.