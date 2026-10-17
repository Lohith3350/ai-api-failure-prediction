"""Main FastAPI application entry point with CORS and modular routing."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import telemetry, predictions, incidents, system
from backend.app.services.telemetry_service import seed_default_data
from backend.app.services.prediction_service import process_telemetry_window, get_latest_records


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed initial baseline data and perform warmup prediction evaluation
    seed_default_data()
    latest = get_latest_records()
    if latest:
        try:
            process_telemetry_window(list(latest.values()))
        except Exception:
            pass
    yield
    # Shutdown logic if needed


app = FastAPI(
    title="API Failure Prediction Platform",
    description="Real-time microservice failure prediction, dependency root-cause diagnosis, and automated decision recommendations.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local Vite development and external frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers (both directly and under /api for proxy and standalone clients)
for r in [telemetry.router, predictions.router, incidents.router, system.router, system.sim_router]:
    app.include_router(r)
    app.include_router(r, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "project": "AI-Powered API Failure Prediction",
        "status": "ready",
        "docs": "/docs",
        "endpoints": [
            "/telemetry/recent",
            "/predictions",
            "/incidents",
            "/system/overview",
            "/system/topology",
            "/simulation/step",
        ],
    }
