from sqlalchemy.exc import ProgrammingError
from fastapi import HTTPException

async def commit_or_raise(session):
    try:
        await session.commit()
    except Exception as e:
        # Catch SQLAlchemy ProgrammingError that wraps DB driver errors like UndefinedColumnError
        msg = str(e)
        if isinstance(e, ProgrammingError) or 'UndefinedColumnError' in msg or 'column "status"' in msg:
            raise HTTPException(500, "Database schema mismatch: missing column (e.g., 'status'). Please run migrations: `alembic upgrade head` or restart the container to apply migrations.")
        raise
