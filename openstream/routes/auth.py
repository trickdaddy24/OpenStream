"""Authentication routes — login/logout with session cookies."""

import bcrypt
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from openstream.database import get_db
from openstream.models import User

router = APIRouter(tags=["auth"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Read user_id from session and return User or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).get(user_id)


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Validate credentials and set session."""
    user = db.query(User).filter_by(username=username).first()
    if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        request.session["user_id"] = user.id
        return RedirectResponse("/", status_code=303)

    # Re-render login with error
    from openstream.app import templates
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid username or password",
    })


@router.post("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
