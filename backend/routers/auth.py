from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from dependencies import bearer_scheme, get_current_user
from schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse, UserResponse, RegisterRequest
from services.auth import login_user, logout_user, refresh_tokens, register_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest) -> UserResponse:
    return register_user(data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest) -> TokenResponse:
    return login_user(data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest) -> TokenResponse:
    return refresh_tokens(data.refresh_token)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> UserResponse:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: LogoutRequest, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]) -> Response:
    logout_user(credentials.credentials if credentials else None, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
