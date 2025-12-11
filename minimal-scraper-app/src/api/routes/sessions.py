from fastapi import APIRouter

router = APIRouter()


@router.get("/sessions/health")
def sessions_health():
    """Session health check endpoint."""
    return {"status": "ok", "detail": "session health stub"}
