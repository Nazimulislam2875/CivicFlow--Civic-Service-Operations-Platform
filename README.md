# CivicFlow — Civic Service Operations Platform

CivicFlow is a modular FastAPI backend for managing citizen service requests, staff assignments, service workflows, and request status tracking. It is built with FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, SeaweedFS, and Docker.

## Features

- User registration and authentication
- JWT access and refresh token authentication
- Role-based access control for citizens, staff, supervisors, and administrators
- Department and service category management
- Service request creation, retrieval, updating, and filtering
- Request priority and status management
- Staff assignment for service requests
- Service request status history
- PostgreSQL database integration
- Database schema migrations with Alembic
- Redis caching for service request lists with cache invalidation
- Celery background tasks for service request email notifications
- Configurable SMTP delivery with retry handling
- SeaweedFS S3-compatible object storage configuration for attachments
- Automated API, permission, caching, and notification tests with Pytest

## Technology Stack

- **Language:** Python 3.12+
- **API Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Validation and Configuration:** Pydantic, Pydantic Settings
- **Authentication:** JWT, password hashing
- **Testing:** Pytest, HTTPX
- **Background Jobs:** Celery
- **Cache and Message Broker:** Redis
- **Object Storage:** SeaweedFS S3-compatible API
- **Infrastructure:** Docker Compose, Nginx
- **Email:** SMTP
- **Code Quality:** Ruff

## Project Structure

```text
CivicFlow--Civic-Service-Operations-Platform/
├── .github/
│   └── workflows/
├── app/
├── docker/
│   └── seaweedfs/
├── migrations/
│   └── versions/
├── nginx/
├── tests/
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Prerequisites

For the Docker-based setup, install:

- Git
- Docker Desktop with WSL 2 integration on Windows, or Docker Engine and Docker Compose on Linux
- A terminal that can access Docker

Verify the installation:

```bash
docker --version
docker compose version
```

## Local Setup

The following instructions run the API directly in a Python environment. PostgreSQL and Redis must be available separately, and any required environment variables must be configured.

### 1. Clone the repository

```bash
git clone https://github.com/Nazimulislam2875/CivicFlow--Civic-Service-Operations-Platform.git
cd CivicFlow--Civic-Service-Operations-Platform
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the application and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

### 4. Configure environment variables

Create a local `.env` file using `.env.example` as a template:

```bash
cp .env.example .env
```

Set the required database connection and authentication values for the environment in which the API will run. Configure `REDIS_URL` to point to the appropriate Redis instance.

Generate a strong secret key if needed:

```bash
openssl rand -hex 32
```

Use the generated value for `SECRET_KEY` in `.env`.

Never commit `.env` or production secrets to version control.

### 5. Prepare the database

Ensure PostgreSQL is running and the configured database exists. Apply the database migrations:

```bash
alembic upgrade head
```

### 6. Start the development server

```bash
uvicorn app.main:app --reload
```

Open the interactive API documentation:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Docker Setup and Full Stack Verification

Docker Compose provides a local environment for running the API and its supporting services together.

The Compose configuration defines PostgreSQL, Redis, SeaweedFS, a database migration service, the FastAPI API, a Celery Worker, and Nginx.

### 1. Configure the environment

From the project root, create the `.env` file:

```bash
cp .env.example .env
```

Set a strong `SECRET_KEY` in `.env`. Docker Compose requires this variable for the migration, API, and worker services.

The Compose configuration supplies internal PostgreSQL and Redis connection URLs to the containers. These use the Compose service names `db` and `redis`; they are different from the `localhost` examples used for direct local development.

### 2. Configure SeaweedFS

Create the local S3 configuration file:

```bash
cp docker/seaweedfs/s3.example.json docker/seaweedfs/s3.json
```

Configure the S3 access key and secret key in `docker/seaweedfs/s3.json`. Ensure they match the `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` values supplied to the API. If these variables are omitted, the Compose configuration uses its development defaults.

The local `docker/seaweedfs/s3.json` file should remain untracked. Never commit real credentials.

### 3. Build and start the services

From the project root, run:

```bash
docker compose up --build -d
```

Check the container status:

```bash
docker compose ps
```

The API depends on successful database migration and a started Redis and SeaweedFS service. Wait for startup to complete before testing the API.

### 4. Check service logs

Inspect the logs when a service does not start correctly:

```bash
docker compose logs --tail=100 db
docker compose logs --tail=100 redis
docker compose logs --tail=100 seaweedfs
docker compose logs --tail=100 migrate
docker compose logs --tail=100 api
docker compose logs --tail=100 worker
docker compose logs --tail=100 nginx
```

To follow the API logs live:

```bash
docker compose logs -f api
```

Press `Ctrl + C` to stop following logs. This does not stop the containers.

### 5. Verify the API through Nginx

Nginx exposes the API on port `8080` in the local environment.

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

Check database connectivity through the API:

```bash
curl -i http://localhost:8080/api/v1/health/db
```

A successful check should return HTTP `200 OK` with a response indicating that the database is connected.

### 6. Verify the supporting services

Use the following command to inspect the current container state:

```bash
docker compose ps
```

Confirm that:

- PostgreSQL is healthy.
- Redis is healthy.
- The migration service completed successfully.
- The API responds through Nginx.
- The Celery Worker starts without errors.
- SeaweedFS starts and its S3 configuration is valid.

For a complete functional check, test authentication, service request operations, role permissions, attachment operations, and background notification tasks through the appropriate API workflows. SMTP notifications require valid SMTP configuration.

A running container alone does not prove that every feature is working.

### 7. Stop the services

Stop the containers while preserving named volumes:

```bash
docker compose down
```

Start them again later:

```bash
docker compose up -d
```

Avoid `docker compose down -v` unless you intentionally want to delete the named volumes containing local PostgreSQL, Redis, and SeaweedFS data.

## Testing

Run the automated test suite in an environment where the required Python dependencies, environment variables, and test services are configured:

```bash
pytest -q
```

Run the code quality checks:

```bash
ruff check .
```

Tests that depend on PostgreSQL, Redis, or other services require those dependencies to be available. Consult the test configuration and CI workflow for the expected test environment.

## Database Migrations

Apply all migrations:

```bash
alembic upgrade head
```

Check the current migration:

```bash
alembic current
```

View available migration heads:

```bash
alembic heads
```

## Security Notes

- Keep secret keys and database credentials in environment variables.
- Never commit `.env` files or real credentials.
- Use strong secrets and HTTPS in production.
- Review role permissions before exposing administrative operations.
- Keep dependencies updated and run automated tests before deployment.
- The database credentials in the current Docker Compose configuration are for local development; replace and secure them appropriately before using a production environment.

## Project Status

The backend includes authentication, role-based permissions, service request management, staff assignment, request status history, Redis caching, Celery background tasks, and automated tests.

The complete stack should be validated from a fresh checkout before considering all documented workflows verified.

## License

No license has been specified yet. Add an appropriate license before redistributing the project under specific open-source terms.