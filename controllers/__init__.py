# Controllers module
from controllers.admin_controller import router as admin_router
from controllers.customer_calls_controller import router as customer_calls_router
from controllers.customer_visit_controller import router as customer_visit_router
from controllers.admin_jobs_controller import router as admin_jobs_router
from controllers.jobs_controller import router as jobs_router
from controllers.auth_controller import router as auth_router

__all__ = [
    "admin_router", 
    "customer_calls_router", 
    "customer_visit_router",
    "admin_jobs_router",
    "jobs_router",
    "auth_router",
]
