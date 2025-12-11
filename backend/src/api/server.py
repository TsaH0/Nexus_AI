"""
NEXUS API Server
FastAPI-based REST API for supply chain orchestration

Run with:
    uvicorn src.api.server:app --reload --port 8000
    
Or:
    python -m src.api.server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .database import engine, Base, init_db
from .routes import (
    locations,
    projects,
    materials,
    material_requirements,
    tower_types,
    substation_types,
    budgets,
    taxes,
    forecasts,
    simulation,
    inventory,
    substations,
    transfers,
    quote,
    stats,
    procurement,
    alerts,
    demand_forecast
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown"""
    # Startup: Create database tables
    init_db()
    yield
    # Shutdown logic (if needed)
    print("🔴 NEXUS API shutting down...")


# Create FastAPI application
app = FastAPI(
    title="NEXUS API",
    description="""
    🔌 **NEXUS - Intelligent Supply Chain Orchestration Engine for POWERGRID**
    
    This API provides endpoints for:
    - **Materials Management**: CRUD operations for materials and equipment
    - **Project Management**: Manage power grid infrastructure projects
    - **Demand Forecasting**: AI-powered forecasting using Prophet
    - **Procurement Optimization**: Vendor selection and order batching
    - **Inventory Management**: Warehouse and transfer operations
    - **Simulation**: Run supply chain simulations and get action plans
    
    Built for Smart India Hackathon 2024.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS Configuration - Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React default
        "http://localhost:5173",      # Vite default
        "http://localhost:8080",      # Alternative
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"                           # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers with prefixes
app.include_router(
    locations.router, 
    prefix="/api/v1/locations", 
    tags=["Locations"]
)

app.include_router(
    projects.router, 
    prefix="/api/v1/projects", 
    tags=["Projects"]
)

app.include_router(
    materials.router, 
    prefix="/api/v1/materials", 
    tags=["Materials"]
)

app.include_router(
    material_requirements.router, 
    prefix="/api/v1/material-requirements", 
    tags=["Material Requirements"]
)

app.include_router(
    tower_types.router, 
    prefix="/api/v1/tower-types", 
    tags=["Tower Types"]
)

app.include_router(
    substation_types.router, 
    prefix="/api/v1/substation-types", 
    tags=["Substation Types"]
)

app.include_router(
    budgets.router, 
    prefix="/api/v1/budgets", 
    tags=["Budgets"]
)

app.include_router(
    taxes.router, 
    prefix="/api/v1/taxes", 
    tags=["Taxes"]
)

app.include_router(
    forecasts.router, 
    prefix="/api/v1/forecasts", 
    tags=["Forecasts"]
)

app.include_router(
    simulation.router, 
    prefix="/api/v1/simulation", 
    tags=["Simulation"]
)

app.include_router(
    inventory.router, 
    prefix="/api/v1", 
    tags=["Inventory Management"]
)

app.include_router(
    substations.router, 
    prefix="/api/v1", 
    tags=["Substations"]
)

app.include_router(
    transfers.router, 
    prefix="/api/v1", 
    tags=["Material Transfers"]
)

app.include_router(
    quote.router, 
    prefix="/api/v1/quote", 
    tags=["Project Quote"]
)

app.include_router(
    stats.router, 
    prefix="/api/v1/stats", 
    tags=["System Stats"]
)

app.include_router(
    procurement.router, 
    prefix="/api/v1/procurement", 
    tags=["Procurement Monitoring"]
)

app.include_router(
    alerts.router, 
    prefix="/api/v1/alerts", 
    tags=["Alerts & Notifications"]
)

app.include_router(
    demand_forecast.router, 
    prefix="/api/v1", 
    tags=["Demand Forecasting"]
)


# Root endpoints
@app.get("/", tags=["Root"])
async def root():
    """API root - returns service info"""
    return {
        "service": "NEXUS API",
        "description": "Intelligent Supply Chain Orchestration for POWERGRID",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NEXUS Backend",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }


@app.get("/api/v1", tags=["Root"])
async def api_info():
    """API v1 information"""
    return {
        "version": "1.0.0",
        "endpoints": {
            "locations": "/api/v1/locations",
            "projects": "/api/v1/projects",
            "materials": "/api/v1/materials",
            "material_requirements": "/api/v1/material-requirements",
            "tower_types": "/api/v1/tower-types",
            "substation_types": "/api/v1/substation-types",
            "budgets": "/api/v1/budgets",
            "taxes": "/api/v1/taxes",
            "forecasts": "/api/v1/forecasts",
            "simulation": "/api/v1/simulation",
            "inventory": "/api/v1/inventory"
        }
    }


# Run server directly
if __name__ == "__main__":
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
