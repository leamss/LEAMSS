"""
LEAMSS Portal Backend Server - MySQL Version
Immigration Service Management System
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database and models
from core.database import engine, init_db, test_connection, Base
from core.models import *  # Import all models to register them

# Import routers
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.products import router as products_router
from routers.sales import router as sales_router
from routers.cases import router as cases_router
from routers.documents import router as documents_router
from routers.tickets import router as tickets_router
from routers.notifications import router as notifications_router
from routers.reports import router as reports_router
from routers.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting LEAMSS Portal Backend (MySQL)...")
    
    # Test database connection
    connected = await test_connection()
    if connected:
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed - please check your MySQL configuration")
    
    # Create tables if they don't exist
    try:
        await init_db()
        print("✓ Database tables initialized")
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down LEAMSS Portal Backend...")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="LEAMSS Portal API",
    description="Immigration Service Management System - MySQL Backend",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS[0] != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "documents"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "sales"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "tickets"), exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(sales_router, prefix="/api")
app.include_router(cases_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LEAMSS Portal API",
        "version": "2.0.0",
        "database": "MySQL",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    db_status = await test_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "service": "LEAMSS Portal MySQL Backend"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
