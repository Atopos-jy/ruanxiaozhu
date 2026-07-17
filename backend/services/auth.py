import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, REFRESH_TOKEN_MAX_SESSION_DAYS, REFRESH_TOKEN_SLIDING_DAYS, SECRET_KEY
from database import get_connection
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash("not-a-real-password")


def user_from_row(row: Mapping[str, Any]) -> UserResponse:
    return UserResponse(id=str(row["id"]), email=row["email"])


def create_access_token(user_id: str, session_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "jti": str(uuid.uuid4()), "sid": session_id, "type": "access", "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, session_id: str, refresh_jti: str, expires_at: datetime) -> str:
    return jwt.encode({"sub": user_id, "jti": refresh_jti, "sid": session_id, "type": "refresh", "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)


def issue_token_pair(user: UserResponse, session_id: str, refresh_jti: str, refresh_expires_at: datetime) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.id, session_id), refresh_token=create_refresh_token(user.id, session_id, refresh_jti, refresh_expires_at), user=user)


def register_user(data: RegisterRequest) -> UserResponse:
    email, user_id = str(data.email).lower(), uuid.uuid4()
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO users (id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)", (user_id, email, password_hash.hash(data.password), datetime.now(timezone.utc)))
    except Exception as error:
        if getattr(error, "sqlstate", None) == "23505":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册，请直接登录") from error
        raise
    return UserResponse(id=str(user_id), email=email)


def login_user(data: LoginRequest) -> TokenResponse:
    email = str(data.email).lower()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            if row is None:
                password_hash.verify(data.password, dummy_hash)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
            if not password_hash.verify(data.password, row["password_hash"]):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
            cursor.execute("UPDATE users SET last_login_at = %s WHERE id = %s", (datetime.now(timezone.utc), row["id"]))
    user, now = user_from_row(row), datetime.now(timezone.utc)
    session_id, refresh_jti = uuid.uuid4(), uuid.uuid4()
    session_expires_at = now + timedelta(days=REFRESH_TOKEN_MAX_SESSION_DAYS)
    refresh_expires_at = min(now + timedelta(days=REFRESH_TOKEN_SLIDING_DAYS), session_expires_at)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO auth_sessions (id, user_id, refresh_jti, created_at, expires_at, refresh_expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)""", (session_id, user.id, refresh_jti, now, session_expires_at, refresh_expires_at))
    return issue_token_pair(user, str(session_id), str(refresh_jti), refresh_expires_at)


def refresh_tokens(refresh_token: str) -> TokenResponse:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token 无效或已过期")
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id, session_id, refresh_jti = payload.get("sub"), payload.get("sid"), payload.get("jti")
        if payload.get("type") != "refresh" or not user_id or not session_id or not refresh_jti:
            raise unauthorized
    except InvalidTokenError as error:
        raise unauthorized from error
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT * FROM auth_sessions WHERE id = %s AND user_id = %s AND refresh_jti = %s
                AND revoked_at IS NULL AND expires_at > %s""", (session_id, user_id, refresh_jti, now))
            session = cursor.fetchone()
            cursor.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
            user_row = cursor.fetchone()
            if session is None or user_row is None:
                raise unauthorized
            new_refresh_expires_at = min(now + timedelta(days=REFRESH_TOKEN_SLIDING_DAYS), session["expires_at"])
            new_refresh_jti = uuid.uuid4()
            cursor.execute("UPDATE auth_sessions SET refresh_jti = %s, refresh_expires_at = %s WHERE id = %s", (new_refresh_jti, new_refresh_expires_at, session_id))
    return issue_token_pair(user_from_row(user_row), session_id, str(new_refresh_jti), new_refresh_expires_at)


def get_user_from_access_token(access_token: str) -> UserResponse:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态无效或已过期", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id, token_id, session_id = payload.get("sub"), payload.get("jti"), payload.get("sid")
        if payload.get("type") != "access" or not user_id or not token_id or not session_id:
            raise unauthorized
    except InvalidTokenError as error:
        raise unauthorized from error
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT jti FROM revoked_tokens WHERE jti = %s", (token_id,))
            revoked = cursor.fetchone()
            cursor.execute("SELECT id FROM auth_sessions WHERE id = %s AND user_id = %s AND revoked_at IS NULL AND expires_at > %s", (session_id, user_id, datetime.now(timezone.utc)))
            session = cursor.fetchone()
            cursor.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
    if revoked is not None or session is None or row is None:
        raise unauthorized
    return user_from_row(row)


def logout_user(access_token: str | None, refresh_token: str | None) -> None:
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""INSERT INTO revoked_tokens (jti, expires_at, revoked_at) VALUES (%s, %s, %s)
                        ON CONFLICT (jti) DO NOTHING""", (payload["jti"], datetime.fromtimestamp(payload["exp"], tz=timezone.utc), datetime.now(timezone.utc)))
        except (InvalidTokenError, KeyError):
            pass
    if refresh_token:
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") == "refresh":
                with get_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("UPDATE auth_sessions SET revoked_at = %s WHERE id = %s AND user_id = %s", (datetime.now(timezone.utc), payload.get("sid"), payload.get("sub")))
        except InvalidTokenError:
            pass
