from fastapi import APIRouter
from src.api.v1.routers.misc import router as misc_router
from src.api.v1.routers.project import router as project_router
from src.api.v1.routers.link import router as link_router

router = APIRouter(prefix="/api/v1")

router.include_router(misc_router)
router.include_router(project_router)
router.include_router(link_router)
