"""
Backend for Frontend (BFF) layer.

Provides optimized API endpoints tailored for specific frontend clients.
Currently supports:
- Web BFF: Optimized for Angular frontend
"""

from app.bff.web.router import router as web_bff_router

__all__ = ["web_bff_router"]