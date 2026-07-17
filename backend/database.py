from datetime import datetime, timezone

from psycopg import Connection, connect
from psycopg.rows import dict_row

from config import DATABASE_URL


def get_connection() -> Connection:
    return connect(DATABASE_URL, row_factory=dict_row)


def init_database() -> None:
    """Create the relational schema and enable pgvector on PostgreSQL."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL, last_login_at TIMESTAMPTZ)""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti UUID PRIMARY KEY, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ NOT NULL)""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS auth_sessions (
                id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id), refresh_jti UUID NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
                refresh_expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ)""")
            now = datetime.now(timezone.utc)
            cursor.execute("DELETE FROM revoked_tokens WHERE expires_at <= %s", (now,))
            cursor.execute("DELETE FROM auth_sessions WHERE expires_at <= %s", (now,))
