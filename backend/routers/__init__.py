"""Routers module for LEAMSS Portal"""
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.products import router as products_router
from routers.sales import router as sales_router
from routers.cases import router as cases_router
from routers.documents import router as documents_router
from routers.tickets import router as tickets_router
from routers.notifications import router as notifications_router
from routers.reports import router as reports_router
from routers.admin import router as admin_router

__all__ = [
    "auth_router",
    "users_router", 
    "products_router",
    "sales_router",
    "cases_router",
    "documents_router",
    "tickets_router",
    "notifications_router",
    "reports_router",
    "admin_router"
]
