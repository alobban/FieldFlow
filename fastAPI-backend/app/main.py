"""
Multi-Tenant Backend Application

Main FastAPI application entry point with BFF support for Angular frontend.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.api.v1.router import router as api_v1_router
from app.bff.web.router import router as web_bff_router
from app.core.exceptions import AppException


# ═══════════════════════════════════════════════════════════════════════════════
# LIFESPAN MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize connections, log configuration
    - Shutdown: Clean up resources, close connections
    """
    # ─────────────────────────────────────────────────────────────────────────
    # STARTUP
    # ─────────────────────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"🚀 Starting {settings.app_name}")
    print(f"   Environment: {settings.app_env}")
    print(f"   Debug Mode: {settings.debug}")
    print(f"   Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    print(f"   API Prefix: {settings.api_v1_prefix}")
    print(f"   BFF Prefix: {settings.bff_web_prefix}")
    print("=" * 60)
    
    # Test database connection on startup
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        # Don't raise - let the app start anyway for health checks
    
    yield
    
    # ─────────────────────────────────────────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"👋 Shutting down {settings.app_name}")
    print("=" * 60)
    
    # Dispose database engine
    await engine.dispose()
    print("✅ Database connections closed")


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle custom application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "detail": exc.detail,
                "status_code": exc.status_code,
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors with detailed field information."""
        errors = []
        for error in exc.errors():
            # Build field path (e.g., "body.username" or "query.limit")
            field_path = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "detail": "Validation error",
                "errors": errors,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        # Log the exception (in production, use proper logging)
        print(f"Unhandled exception: {type(exc).__name__}: {exc}")
        
        if settings.debug:
            # In debug mode, return detailed error information
            import traceback
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "detail": str(exc),
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                },
            )
        else:
            # In production, return generic error
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "detail": "An unexpected error occurred. Please try again later.",
                },
            )


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    
    # ─────────────────────────────────────────────────────────────────────────
    # Health Check Endpoints
    # ─────────────────────────────────────────────────────────────────────────
    
    @app.get(
        "/health",
        tags=["Health"],
        summary="Health Check",
        description="Basic health check - returns OK if the application is running.",
        response_model=dict,
    )
    async def health_check() -> dict:
        """
        Basic health check endpoint.
        
        Used by load balancers and container orchestration to verify
        the application is running.
        """
        return {
            "status": "healthy",
            "app": settings.app_name,
            "environment": settings.app_env,
            "version": "1.0.0",
        }
    
    @app.get(
        "/ready",
        tags=["Health"],
        summary="Readiness Check",
        description="Checks if the application is ready to serve requests (including database).",
        response_model=dict,
    )
    async def readiness_check() -> dict:
        """
        Readiness check endpoint.
        
        Verifies the application can connect to all required services
        (database, cache, etc.) and is ready to handle requests.
        """
        checks = {
            "database": "unknown",
        }
        
        # Check database connection
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "connected"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
        
        # Determine overall status
        all_healthy = all(
            status == "connected" or status == "ok"
            for status in checks.values()
        )
        
        return {
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
        }
    
    @app.get(
        "/",
        tags=["Root"],
        summary="API Root",
        description="Welcome endpoint with API information.",
    )
    async def root() -> dict:
        """
        Root endpoint with API information.
        """
        return {
            "message": f"Welcome to {settings.app_name}",
            "documentation": "/docs" if settings.debug else "Documentation disabled in production",
            "health": "/health",
            "ready": "/ready",
            "api_v1": settings.api_v1_prefix,
            "bff_web": settings.bff_web_prefix,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # API Routers
    # ─────────────────────────────────────────────────────────────────────────
    
    # REST API v1
    app.include_router(
        api_v1_router,
        prefix=settings.api_v1_prefix,
    )
    
    # Web BFF (Backend for Frontend - optimized for Angular)
    app.include_router(
        web_bff_router,
        prefix=settings.bff_web_prefix,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION FACTORY
# ═══════════════════════════════════════════════════════════════════════════════


def create_application() -> FastAPI:
    """
    Application factory function.
    
    Creates and configures the FastAPI application instance with:
    - Metadata and documentation
    - CORS middleware
    - Exception handlers
    - Route registration
    
    Returns:
        Configured FastAPI application instance
    """
    
    # Create FastAPI instance
    app = FastAPI(
        title=settings.app_name,
        description="""
## 🏢 Multi-Tenant Backend API

A comprehensive multi-tenant backend system with BFF (Backend for Frontend) 
support optimized for Angular applications.

### Features

#### 🔐 Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- Tenant-scoped user management

#### 🏢 Tenant Management
- Self-service tenant registration
- Tenant isolation and data separation
- Customizable tenant settings

#### 👥 User Management
- User registration within tenant context
- Username auto-generation
- Email verification workflow

#### 🌐 Web BFF (Backend for Frontend)
- Optimized endpoints for Angular frontend
- Landing page data aggregation
- Streamlined onboarding flow

### API Structure

- **`/api/v1`** - REST API endpoints
- **`/bff/web`** - Web BFF endpoints for Angular
- **`/health`** - Health check
- **`/ready`** - Readiness check (includes DB)
- **`/docs`** - This documentation (Swagger UI)
- **`/redoc`** - Alternative documentation (ReDoc)
        """,
        version="1.0.0",
        terms_of_service="https://example.com/terms",
        contact={
            "name": "API Support",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        # Disable docs in production
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        # Lifespan manager
        lifespan=lifespan,
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # CORS Middleware
    # ─────────────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Total-Count",
            "X-Page",
            "X-Page-Size",
            "X-Total-Pages",
        ],
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Register Exception Handlers
    # ─────────────────────────────────────────────────────────────────────────
    register_exception_handlers(app)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Register Routers
    # ─────────────────────────────────────────────────────────────────────────
    register_routers(app)
    
    return app


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Create the application instance
app = create_application()


# ═══════════════════════════════════════════════════════════════════════════════
# DEVELOPMENT SERVER
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 60)
    print("Starting development server...")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        reload_dirs=["app"] if settings.debug else None,
        log_level="debug" if settings.debug else "info",
        access_log=True,
    )