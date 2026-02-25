"""Dashboard API router."""

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(user: User = Depends(get_current_user)):
    """Return a lightweight dashboard summary."""
    return {"status": "ok"}
