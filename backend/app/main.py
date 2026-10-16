from fastapi import FastAPI
from backend.app.routes import telemetry, predictions, incidents

app = FastAPI(
    title="API Failure Prediction API",
    description="Starter API for telemetry, prediction, root-cause analysis, and recommendations.",
    version="0.1.0",
)

app.include_router(telemetry.router)
app.include_router(predictions.router)
app.include_router(incidents.router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {
        "project": "AI-Powered API Failure Prediction",
        "status": "starter",
        "docs": "/docs",
    }
