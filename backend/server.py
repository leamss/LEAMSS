"""
LEAMSS Portal - Main Application Entry Point
Refactored modular architecture
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os
import logging

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core modules
from core.database import db, shutdown_db
from core.auth import get_user_from_token

# Import notification services
from services.notification_service import ws_manager

# Import all routers
from routers import (
    auth_router,
    users_router,
    products_router,
    sales_router,
    cases_router,
    documents_router,
    tickets_router,
    notifications_router,
    reports_router,
    admin_router
)
from routers.scheduler import router as scheduler_router

# Create FastAPI application
app = FastAPI(
    title="LEAMSS Immigration Portal API",
    description="API for managing immigration cases, documents, and workflows",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(sales_router, prefix="/api")
app.include_router(cases_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(scheduler_router, prefix="/api")


# ==================== WebSocket Endpoint ====================

@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time notifications"""
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001)
        return
    
    user_id = user["id"]
    await ws_manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, user_id)
        try:
            await websocket.close(code=4000)
        except Exception:
            pass


# ==================== Health Check ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}


# ==================== Root Endpoint ====================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LEAMSS Immigration Portal API",
        "version": "2.0.0",
        "docs": "/docs"
    }


# ==================== Startup/Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("LEAMSS Portal API starting up...")
    logger.info("Modular architecture loaded successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("LEAMSS Portal API shutting down...")
    await shutdown_db()
