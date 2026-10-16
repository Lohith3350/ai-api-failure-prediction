from fastapi import APIRouter

router = APIRouter(prefix="/incidents", tags=["incidents"])

@router.get("/")
def list_incidents():
    # TODO: combine predictions, root-cause analysis, and decision recommendations.
    return {"incidents": []}
