# SplitEasy

SplitEasy is a backend REST API for managing shared group expenses, tracking balances, and recording settlements.

## Features

- User registration and login with JWT authentication
- Group creation and group membership
- Expense creation with equal and exact splits
- Group balance calculation
- Debt simplification
- Settlement recording
- Expense history and filtering
- Redis-based login rate limiting
- Redis caching for group balances
- PostgreSQL database with SQLAlchemy and Alembic migrations
- Automated tests with pytest
- Docker-based development setup

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Pydantic
- JWT authentication
- Redis
- Pytest
- Docker Compose

## Run Locally with Docker

1. Clone the repository.
2. Open the project directory.
3. Start the services:

   ```bash
   docker compose up --build
   ```

4. Open the API documentation at `http://localhost:8000/docs`.
5. Check service health at `http://localhost:8000/health`.

## Run Tests

Activate your virtual environment, install dependencies, and run:

```bash
python -m pytest tests -v
```

## Database Migrations

Apply migrations with:

```bash
alembic upgrade head
```

## API Documentation

FastAPI provides interactive API documentation at `/docs` and an OpenAPI schema at `/openapi.json`.

## Project Purpose

This project demonstrates REST API development, relational database design, authentication, transaction handling, caching, automated testing, and containerization.
