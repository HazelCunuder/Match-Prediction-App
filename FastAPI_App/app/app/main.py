from contextlib import asynccontextmanager
from .services.ml_service import ml_service
from fastapi import FastAPI
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from .routes.predict import register_routes
from .routes.train import register_routes as register_train_routes
from .routes.ingestion import register_routes as register_ingestion_routes
from .core.config import settings
from .database import engine, Base, SessionLocal

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)

    if Path(settings.MODEL_PATH).exists():
        try:
            ml_service.load_model()
            db = SessionLocal()
            try:
                ml_service.load_stats_from_db(db)
            finally:
                db.close()
            print("Modèle chargé avec succès.")
        except Exception as e:

            print(f"Avertissement — modèle non chargé : {e}")
    else:
        print(f"Avertissement — modèle introuvable : {settings.MODEL_PATH}")
        print("Lancez POST /train pour entraîner le premier modèle.")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API ML (données de matchs, entraînement et prédiction) pour la Match Prediction App.",
    version=settings.PROJECT_VERSION,
    lifespan= lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routes(app)
register_train_routes(app)
register_ingestion_routes(app)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "ml-api"}

