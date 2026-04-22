from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from ..services.preparation import preparation_service
from ..database import get_db
from ..services.pipeline import pipeline_service
import pandas as pd
import io

router = APIRouter(tags=["ML Training"])

@router.post("/train")
def train_model(
    db: Session = Depends(get_db),
):
    try:

        # Entrainement
        result = pipeline_service.train(db)

        return result
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=traceback.format_exc()
        )


@router.get("/train/history")
def get_train_history(limit: int = 20, db: Session = Depends(get_db)):
    return pipeline_service.get_history(db, limit=limit)


def register_routes(app):
    app.include_router(router)