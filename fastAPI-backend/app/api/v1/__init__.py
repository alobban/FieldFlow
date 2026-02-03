"""
API Version 1 module.

Contains all v1 API endpoints for tenants, users, and roles.
"""

from app.api.v1.router import router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.auth import router as auth_router

__all__ = [
    "router",
    "tenants_router",
    "users_router",
    "roles_router",
    "auth_router",
]