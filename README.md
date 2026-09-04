# API Key & Rate Limiting Gateway

A Django REST Framework backend service for issuing and managing API keys, authenticating API requests, enforcing request limits, tracking API usage, and logging requests.

The project demonstrates common API gateway concepts such as API key authentication, secure key storage, rate limiting, quotas, request logging, key expiration, and Redis-based usage tracking.

## Table of Contents

* [Overview](#overview)
* [Features](#features)
* [Tech Stack](#tech-stack)
* [How It Works](#how-it-works)
* [API Key Security](#api-key-security)
* [Rate Limiting](#rate-limiting)
* [Request Logging](#request-logging)
* [Docker and Redis](#docker-and-redis)
* [Installation](#installation)
* [Running the Project](#running-the-project)
* [API Usage](#api-usage)
* [Project Structure](#project-structure)
* [What I Learned](#what-i-learned)

## Overview

This project implements an API key gateway that controls access to protected API endpoints.

Authenticated users can generate API keys which are then used by clients to access protected resources. Each incoming request is validated using its API key before being allowed through the application.

Redis is used to maintain fast request counters for rate limiting and daily quotas, while the database stores persistent information such as API key ownership, expiration, status, and request logs.

## Features

* User authentication
* API key generation
* Secure SHA-256 API key hashing
* API key ownership
* API key expiration
* Active/inactive key status
* API key validation
* Requests-per-minute rate limiting
* Daily request quotas
* Redis-based request counters
* Request logging
* Per-key request history
* HTTP status tracking
* Middleware-based API key protection
* Dockerized Redis service
* Docker Compose configuration

## Tech Stack

| Technology            | Purpose                       |
| --------------------- | ----------------------------- |
| Python                | Backend programming language  |
| Django                | Web framework                 |
| Django REST Framework | REST API development          |
| SimpleJWT             | User authentication           |
| Redis                 | Rate-limit and quota counters |
| Docker                | Containerization              |
| Docker Compose        | Redis service orchestration   |
| SQLite/PostgreSQL     | Persistent application data   |

## How It Works

The application separates **user authentication** from **API authentication**.

Users first authenticate normally and generate an API key.

```text
User
  |
  | Login
  v
JWT Authentication
  |
  | Create API Key
  v
API Key Generated
```

The raw API key is returned to the user while its SHA-256 hash is stored in the database.

When accessing a protected endpoint:

```text
Client
  |
  | API-Key Header
  v
Django Middleware
  |
  |-- Key missing ----------> 401 Unauthorized
  |
  v
Hash API Key
  |
  v
Validate API Key
  |
  |-- Invalid/Inactive -----> Request rejected
  |
  |-- Expired -------------> 403 Forbidden
  |
  v
Check Redis Counters
  |
  |-- RPM exceeded ---------> 429 Too Many Requests
  |
  |-- Daily quota exceeded -> 429 Too Many Requests
  |
  v
Django View
  |
  v
Response
  |
  v
Request Log
```

## API Key Security

API keys are generated using Python's `secrets` module.

Example key format:

```text
mc_<random-token>
```

The raw API key is not stored directly in the database.

Instead, it is hashed using SHA-256:

```python
hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
```

Only the hash is persisted.

When a client sends an API key, the received key is hashed again and compared against the stored hash.

```text
Client API Key
      |
      v
   SHA-256
      |
      v
Hashed API Key
      |
      v
Database comparison
```

This prevents raw API keys from being exposed if the database is compromised.

## Rate Limiting

Redis is used for rate limiting because request counters need to be read and updated frequently.

The application tracks two main limits.

### Requests Per Minute

Each API key has a counter representing how many requests it has made during the current minute.

Example:

```text
rpm_time    = 202609041520
rpm_counter = 4
```

If another request arrives during the same minute, the counter is incremented.

```text
Request 1 -> 1
Request 2 -> 2
Request 3 -> 3
Request 4 -> 4
Request 5 -> 5
Request 6 -> 429 Too Many Requests
```

When a new minute begins, the counter is reset.

### Daily Quota

Redis also tracks the number of requests made by an API key during the current day.

Example:

```text
dq_day     = 20260904
dq_counter = 120
```

When the date changes, the daily counter is reset.

Rate limits are associated with individual API keys rather than users, allowing different keys belonging to the same user to maintain independent usage counters.

## Request Logging

Requests made through the gateway are stored in the database.

A request log can contain information such as:

```text
API Key
HTTP Method
Request Path
HTTP Status Code
Created At
```

Example:

```json
{
    "id": 1,
    "method": "GET",
    "path": "/api/get-data/",
    "status_code": 200,
    "created_at": "2026-09-04T14:20:00Z",
    "api_key": 4
}
```

Users can retrieve request history associated with their API key.

This provides basic API usage monitoring and auditing.

## Docker and Redis

Redis runs inside a Docker container rather than requiring Redis to be installed directly on the host machine.

Docker Compose is used to define and start the Redis service.

Example:

```yaml
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
```

Start Redis with:

```bash
docker compose up -d
```

Check running containers:

```bash
docker ps
```

Stop the services with:

```bash
docker compose down
```

The Django application can then communicate with Redis through port `6379`.

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

On Linux/macOS:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Start Redis

Make sure Docker is running, then:

```bash
docker compose up -d
```

### 6. Start Django

```bash
python manage.py runserver
```

The development server will be available at:

```text
http://127.0.0.1:8000/
```

## Running the Project

The basic usage flow is:

```text
1. Register user
        |
        v
2. Login
        |
        v
3. Receive JWT
        |
        v
4. Create API key
        |
        v
5. Receive raw API key
        |
        v
6. Send API key with protected requests
        |
        v
7. Gateway validates key
        |
        v
8. Redis checks usage limits
        |
        v
9. Request is processed
        |
        v
10. Request is logged
```

## API Usage

### Authentication

Register an account and login to receive an access token.

The JWT access token is used for API key management operations.

```http
Authorization: Bearer <access_token>
```

### Create an API Key

An authenticated user can generate an API key.

Example response:

```json
{
    "api_key": "mc_example_api_key"
}
```

The raw key should be stored securely because the database stores only its hash.

### Access a Protected Endpoint

Include the API key in the request headers:

```http
API-Key: mc_example_api_key
```

The gateway validates the key before allowing access to the protected resource.

### Rate Limit Response

If the API key exceeds its allowed request rate:

```json
{
    "error": "max requests per minute hit"
}
```

The server responds with:

```text
429 Too Many Requests
```

### Expired API Key

Expired API keys are rejected:

```json
{
    "error": "Key has expired"
}
```

### Request Logs

Request history can be retrieved for an API key.

Example:

```json
{
    "data": [
        {
            "id": 1,
            "method": "GET",
            "path": "/api/get-data/",
            "status_code": 200,
            "created_at": "2026-09-04T14:20:00Z",
            "api_key": 4
        }
    ]
}
```

## Project Structure

A simplified project structure:

```text
project/
|
├── accounts/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
|
├── gateway/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── middleware.py
│   └── urls.py
|
├── project/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
|
├── docker-compose.yml
├── requirements.txt
├── manage.py
└── README.md
```

## What I Learned

This project demonstrates practical backend engineering concepts beyond basic CRUD APIs, including:

* Designing API key authentication systems
* Generating cryptographically secure API keys
* Hashing credentials before database storage
* Separating user authentication from API authentication
* Using Django middleware for centralized request processing
* Implementing per-key rate limiting
* Designing daily API quotas
* Using Redis for high-frequency counters
* Understanding Redis hashes and atomic counters
* Associating usage limits with individual API keys
* Tracking API requests and response status codes
* Working with Django REST Framework authentication and permissions
* Running Redis with Docker
* Managing multiple services with Docker Compose

The project provides a foundation for understanding how production API gateways protect backend services, enforce usage policies, and track API consumption.
