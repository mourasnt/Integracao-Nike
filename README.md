# Integração Logística - Notfis/JSON

Projeto de exemplo para receber minutas e notas fiscais via JSON (Notfis) usando FastAPI.

Run:

pip install -r requirements.txt
uvicorn app.main:app --reload

DB:

Use `.env` to set DATABASE_URL (ex: postgresql+asyncpg://...)

To apply DB migrations manually run:

    alembic upgrade head

Run with Docker Compose (Postgres + API):

1. Build and start:

   docker-compose up --build -d

2. The container will run migrations and create an initial user defined by `INITIAL_USER` / `INITIAL_PASSWORD`.

Create an initial user for manual runs:

python scripts/create_user.py integracao_logistica StrongP@ssw0rd

This script will insert a user into `users_api` with a bcrypt-hashed password if it does not already exist.
