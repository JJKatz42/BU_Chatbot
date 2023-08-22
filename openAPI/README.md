# Chatbot API with Google Authentication

## Overview

An API for interacting with our chatbot, providing feedback, and managing sessions.

**Version:** 1.0.2

[Find more info here](https://example.com)

## Base URL

http://127.0.0.1:8000

## Endpoints

### 1. `/login`

**Method:** GET

**Summary:** Redirect to Google's OAuth 2.0 authentication

**Responses:**
- `302`: Redirect to Google's authentication page
- `400`: Bad request - Malformed request or validation error
- `401`: Unauthorized - Authentication failed
- `403`: Forbidden - Access denied
- `500`: Internal server error

### 2. `/auth/callback`

**Method:** GET

**Summary:** Callback endpoint for Google's OAuth 2.0 authentication

**Parameters:**
- `code` (query): Authorization code from Google. (Required)

**Responses:**
- `200`: Successful authentication and user information returned
- `401`: Unauthorized - Authentication failed or non-BU email used
- `500`: Internal server error

### 3. `/chat`

**Method:** POST

**Summary:** Send a question to the chatbot

**Request Body:**
- `Authorization`: JWT token for the user.
- `question`: The question posed by the user.

**Responses:**
- `202`: Accepted but processing incomplete. More information needed.
- `400`: Bad request - Malformed request or validation error
- `401`: Unauthorized - Missing, invalid token, or session expired
- `429`: Too many requests
- `500`: Internal server error

### 4. `/feedback`

**Method:** POST

**Summary:** Provide feedback on the chatbot's response

**Request Body:**
- `Authorization`: JWT token for the user.
- `responseID`: The ID of the response being rated.
- `liked`: True if the user liked the response, false otherwise.

**Responses:**
- `200`: Feedback recorded successfully
- `400`: Bad request - Malformed request or validation error
- `401`: Unauthorized - Missing or invalid token/session
- `500`: Internal server error

## Schemas

### ChatRequest
- `Authorization`: JWT token for the user.
- `question`: The question posed by the user.

### ChatResponse
- `response`: The chatbot's response.
- `responseID`: A unique ID for the response.

### FeedbackRequest
- `Authorization`: JWT token for the user.
- `responseID`: The ID of the response being rated.
- `liked`: True if the user liked the response, false otherwise.

### ErrorResponse
- `error`: A descriptive error message.
- `code`: A specific error code for more detailed debugging.

### IncompleteResponse
- `message`: Information or clarification needed from the user.

### UserInfoResponse
- `token`: JWT token for the user.
- `email`: User's email address.
- `first_name`: User's first name.
- `last_name`: User's last name.

## Security Schemes

### GoogleOAuth
- **Type:** oauth2
- **Authorization URL:** [https://accounts.google.com/o/oauth2/v2/auth](https://accounts.google.com/o/oauth2/v2/auth)
- **Scopes:**
  - `openid`: Google login
  - `profile`: Google profile information

### BearerToken
- **Type:** http
- **Scheme:** bearer
- **Bearer Format:** JWT

## Security
- GoogleOAuth
- BearerToken
