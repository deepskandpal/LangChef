# Authentication API Documentation

This document describes the authentication API endpoints for the LLM Workflow Platform.

## Base URL

All endpoints are relative to the base URL: `/api/auth`

## Endpoints

### AWS Login

Logs in using AWS credentials configured in the application.

- **URL**: `/aws-login`
- **Method**: `POST`
- **Auth required**: No
- **Permissions required**: None
- **Note**: This endpoint uses the AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN) configured in the application to authenticate the user.

#### Success Response

- **Code**: `200 OK`
- **Content example**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "aws-user",
    "email": "aws-user@example.com",
    "full_name": "AWS User"
  }
}
```

#### Error Response

- **Code**: `400 Bad Request`
- **Content example**:

```json
{
  "detail": "AWS credentials not provided"
}
```

OR

- **Code**: `500 Internal Server Error`
- **Content example**:

```json
{
  "detail": "Failed to login with AWS credentials: [error message]"
}
```

### Register Client

Registers a client with AWS SSO OIDC.

- **URL**: `/register-client`
- **Method**: `POST`
- **Auth required**: No
- **Permissions required**: None

#### Success Response

- **Code**: `200 OK`
- **Content example**:

```json
{
  "client_id": "abcdef123456",
  "client_secret": "secret123456",
  "expiration": "2023-03-13T12:00:00Z"
}
```

#### Error Response

- **Code**: `500 Internal Server Error`
- **Content example**:

```json
{
  "detail": "Failed to register with AWS SSO"
}
```

### Device Authorization

Starts the device authorization flow.

- **URL**: `/device-authorization`
- **Method**: `POST`
- **Auth required**: No
- **Permissions required**: None
- **Data constraints**:

```json
{
  "client_id": "[string]",
  "client_secret": "[string]"
}
```

#### Success Response

- **Code**: `200 OK`
- **Content example**:

```json
{
  "device_code": "device-code-123",
  "user_code": "USER-CODE",
  "verification_uri": "https://device.sso.us-east-1.amazonaws.com",
  "verification_uri_complete": "https://device.sso.us-east-1.amazonaws.com?user_code=USER-CODE",
  "expires_in": 600,
  "interval": 5
}
```

#### Error Response

- **Code**: `500 Internal Server Error`
- **Content example**:

```json
{
  "detail": "Failed to start device authorization"
}
```

### Create Token

Creates a token from a device code.

- **URL**: `/token`
- **Method**: `POST`
- **Auth required**: No
- **Permissions required**: None
- **Data constraints**:

```json
{
  "client_id": "[string]",
  "client_secret": "[string]",
  "device_code": "[string]"
}
```

#### Success Response

- **Code**: `200 OK`
- **Content example**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "john.doe",
    "email": "john.doe@example.com",
    "full_name": "John Doe"
  }
}
```

#### Error Response

- **Code**: `408 Request Timeout`
- **Content example**:

```json
{
  "detail": "Authorization timed out"
}
```

OR

- **Code**: `500 Internal Server Error`
- **Content example**:

```json
{
  "detail": "Failed to create token from device code"
}
```

### Get Current User

Gets the current user's information.

- **URL**: `/me`
- **Method**: `GET`
- **Auth required**: Yes
- **Permissions required**: None

#### Success Response

- **Code**: `200 OK`
- **Content example**:

```json
{
  "id": "123456",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "is_active": true
}
```

#### Error Response

- **Code**: `401 Unauthorized`
- **Content example**:

```json
{
  "detail": "Could not validate credentials"
}
```

### Refresh Token

Refreshes the JWT token.

- **URL**: `/refresh`
- **Method**: `POST`
- **Auth required**: Yes
- **Permissions required**: None

#### Success Response

- **Code**: `200 OK`