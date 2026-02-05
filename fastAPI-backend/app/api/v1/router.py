"""
API v1 router configuration.

Aggregates all v1 API endpoints into a single router.
"""

from fastapi import APIRouter

from app.api.v1.tenants import router as tenants_router
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.auth import router as auth_router

# Main API v1 router
router = APIRouter(
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)

# Include sub-routers
router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

router.include_router(
    tenants_router,
    prefix="/tenants",
    tags=["Tenants"],
)

router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"],
)

router.include_router(
    roles_router,
    prefix="/roles",
    tags=["Roles"],
)