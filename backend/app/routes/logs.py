from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
def logs() -> None:
    raise HTTPException(status_code=501, detail="Analysis log access is reserved for the next phase")

