from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, FastAPI
from ..services.preparation import preparation_service
from sqlalchemy.orm import Session
from ..database import get_db
from typing import Optional
import pandas as pd
import io

router = APIRouter(tags=["Ingestion"])

@router.post("/ingest")
def ingest(
    db: Session = Depends(get_db),
    file: Optional[UploadFile] = File(None)
):
    """
        Ingestion d'une nouvelle source de données dans la base de données ML pour des entrainements futurs.
        Si le fichier n'est pas fourni, re-ingestion des données de base.

        :param db: Session : Injection de la base de données
        :param file: Optional[UploadFile] : Le fichier .csv importé

        Returns:
            dict: Un message de confirmation ou l'état de l'ingestion.
    """
    try:
        # Entrainement de base avec les deux sources de données
        if file is None:
            return preparation_service.run_base(db)
        # Entrainement avec le .csv complémentaire
        else:
            # Récupération du fichier
            contents = file.file.read()
            df = pd.read_csv(io.BytesIO(contents))

            return preparation_service.run(db, df)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=traceback.format_exc()
        )

def register_routes(app: FastAPI):
    app.include_router(router)