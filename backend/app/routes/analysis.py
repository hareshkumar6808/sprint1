from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("")
def analyze() -> None:
    raise HTTPException(status_code=501, detail="Analysis orchestration is reserved for the next phase")

