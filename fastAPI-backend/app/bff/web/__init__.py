"""
Web BFF module for Angular frontend.

Provides endpoints optimized for the Angular web application,
including landing page data, tenant signup, and onboarding flows.
"""

from app.bff.web.router import router
from app.bff.web.landing_controller import LandingController
from app.bff.web.onboarding_controller import OnboardingController

__all__ = [
    "router",
    "LandingController",
    "OnboardingController",
]