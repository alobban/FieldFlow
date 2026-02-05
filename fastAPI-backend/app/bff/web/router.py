"""
Web BFF router configuration.

Aggregates all Web BFF endpoints into a single router
for mounting in the main application.
"""

from fastapi import APIRouter

from app.bff.web.landing_controller import router as landing_router
from app.bff.web.onboarding_controller import router as onboarding_router

# Main Web BFF router
router = APIRouter(
    tags=["Web BFF"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)

# Include sub-routers
router.include_router(
    landing_router,
    prefix="/landing",
    tags=["Landing Page"],
)

router.include_router(
    onboarding_router,
    prefix="/onboarding",
    tags=["Onboarding"],
)