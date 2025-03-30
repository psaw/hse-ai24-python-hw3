from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from models.user import User
from auth.users import current_active_user

router = APIRouter(prefix="/misc", tags=["Miscellaneous"])


@router.get("/protected")
def protected_route(user: User = Depends(current_active_user)):
    return f"Hello, {user.email}"


@router.get("/cache")
@cache(expire=60)
def cache_route():
    return "Hello, cache"


@router.get("/unprotected")
def unprotected_route():
    return "Hello, anonym"
