# CivicFlow — Civic Service Operations Platform

CivicFlow is a modular FastAPI backend for managing citizen service requests, staff assignments, service workflows, and request status tracking. Built with FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, and Docker.

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
- **Cache and Broker:** Redis
- **Infrastructure:** Docker Compose, Nginx
- **Email:** SMTP
- **Code Quality:** Ruff

## Project Structure

```text
city-service-management-platform/
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   └── services/
├── migrations/
│   └── versions/
├── tests/
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Nazimulislam2875/city-service-management-platform.git
cd city-service-management-platform
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

Install the application and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

### 4. Configure environment variables

Create a local `.env` file using `.env.example` as a template. Set the required database and authentication values. Redis and SMTP settings are also documented in `.env.example`.

SMTP email notifications are optional. To enable them, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, and `SMTP_USE_TLS` in `.env`. Use credentials provided by your SMTP service; for Gmail, use an app password when required rather than your regular account password. Keep these values private. Without SMTP host and sender configuration, notifications are skipped.

Never commit `.env` or production secrets to version control.

### 5. Apply database migrations

Ensure PostgreSQL is running and the configured database exists.

```bash
alembic upgrade head
```

### 6. Start the development server

```bash
uvicorn app.main:app --reload
```

Open the interactive API documentation at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Testing

Run the automated test suite:

```bash
pytest -q
```

Run the code quality checks:

```bash
ruff check .
```

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
- Do not commit `.env` files.
- Use HTTPS and strong secrets in production.
- Review role permissions before exposing administrative operations.
- Keep dependencies updated and run automated tests before deployment.

## Project Status

The backend includes authentication, role-based permissions, service request management, staff assignment, request status history, and automated tests.

**License:** Add a license before redistributing this project under specific open-source terms.

## SeaweedFS S3 Configuration

For a fresh checkout, create the local S3 configuration before starting
Docker Compose:

```bash
cp docker/seaweedfs/s3.example.json docker/seaweedfs/s3.json
```

Replace the example access key and secret key with your own local credentials.
The local `docker/seaweedfs/s3.json` file is ignored by Git. Never commit
real credentials.
