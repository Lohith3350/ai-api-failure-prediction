from fastapi import APIRouter

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.get("/{service_name}")
def get_prediction(service_name: str):
    # TODO: call Namith's prediction service once its interface is agreed.
    return {
        "service_name": service_name,
        "failure_probability": None,
        "risk_level": "NOT_READY",
        "message": "Prediction module not integrated yet",
    }
