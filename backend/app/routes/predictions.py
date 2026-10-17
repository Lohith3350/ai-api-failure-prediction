"""Failure prediction API routes."""

from fastapi import APIRouter
from typing import List, Dict, Any
from backend.app.schemas import PredictionResponse
from backend.app.services.prediction_service import get_prediction, get_all_predictions

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("")
@router.get("/")
def list_predictions() -> Dict[str, Any]:
    """Retrieve failure probabilities and risk assessments for all monitored services."""
    preds = get_all_predictions()
    return {"predictions": preds}


@router.get("/{service_name}", response_model=PredictionResponse)
def service_prediction(service_name: str) -> PredictionResponse:
    """Retrieve failure probability and recommended actions for a specific service."""
    pred = get_prediction(service_name)
    return PredictionResponse(
        service_name=pred["service_name"],
        failure_probability=pred["failure_probability"],
        risk_level=pred["risk_level"],
        reasons=pred.get("reasons", []),
        recommended_actions=pred.get("recommended_actions", []),
    )
