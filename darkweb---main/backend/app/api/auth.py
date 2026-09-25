from fastapi import APIRouter, Request, Response


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


USER = {
    "id": "u1",
    "name": "Analyst",
    "role": "analyst",
}


@router.get("/session")
def get_session(request: Request):
    token = request.cookies.get("session_token")
    if token:
        return {"user": USER}
    return {"user": None}


@router.post("/login")
def login(payload: dict, response: Response):
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        return {"user": None}

    name = username.split("@")[0].replace(".", " ").title() if "@" in str(username) else str(username)
    user_info = {
        "id": str(username),
        "name": name or "Analyst",
        "role": "analyst",
    }

    response.set_cookie(
        key="session_token",
        value="valid",
        httponly=True,
        samesite="lax",
        path="/",
    )

    return {"user": user_info}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token", path="/")
    return {"ok": True}