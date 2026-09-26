from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_NAME = "traceveil_session"


class LoginRequest(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: str
    name: Optional[str] = None
    role: Optional[str] = "Analyst"


class LoginResponse(BaseModel):
    user: User


class SessionResponse(BaseModel):
    user: Optional[User] = None


@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest, response: Response):
    username = creds.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a username or email.",
        )

    user = User(
        id=f"usr_{username.lower()}",
        name=username,
        role="Lead Investigator" if "analyst" in username.lower() or "admin" in username.lower() else "Analyst",
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=user.id,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return LoginResponse(user=user)


@router.get("/session", response_model=SessionResponse)
def get_session(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return SessionResponse(
            user=User(
                id="usr_analyst",
                name="Threat Intelligence Analyst",
                role="Lead Investigator",
            )
        )

    username = session_id.replace("usr_", "")
    return SessionResponse(
        user=User(
            id=session_id,
            name=username,
            role="Analyst",
        )
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
