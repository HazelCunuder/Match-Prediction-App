import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date
from typing import Dict
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func

from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, log_loss

from ..models.match import FootballMatch, MatchStats, TeamStatsReference, TrainLog, Team
from ..core.config import settings


class PipelineService:

    _CAT_FEATURES = ["HomeTeam", "AwayTeam"]

    _NUM_FEATURES = [
        "home_goals_scored_home",   "home_goals_conceded_home",   "home_win_rate_home",
        "away_goals_scored_away",   "away_goals_conceded_away",   "away_win_rate_away",
        "home_season_rank",         "away_season_rank",
        "home_rolling_scored",      "home_rolling_conceded",      "home_rolling_win_rate",
        "away_rolling_scored",      "away_rolling_conceded",      "away_rolling_win_rate",
        "league_season",
    ]

    # ─────────────────────────────────────────────────────────────────────
    # Étape 1 — Chargement depuis la base de données
    # ─────────────────────────────────────────────────────────────────────

    def _load_from_db(self, db: Session) -> pd.DataFrame:
        """
        Charge les données d'entraînement depuis match_stats (Feature Store)
        en jointure avec football_matches et teams.
        """
        HomeTeam = aliased(Team, name="home_team_alias")
        AwayTeam = aliased(Team, name="away_team_alias")

        rows = (
            db.query(
                FootballMatch.league_season,
                FootballMatch.result,
                HomeTeam.name.label("HomeTeam"),
                AwayTeam.name.label("AwayTeam"),
                MatchStats.home_goals_scored_home,
                MatchStats.home_goals_conceded_home,
                MatchStats.home_win_rate_home,
                MatchStats.away_goals_scored_away,
                MatchStats.away_goals_conceded_away,
                MatchStats.away_win_rate_away,
                MatchStats.home_season_rank,
                MatchStats.away_season_rank,
                MatchStats.home_rolling_scored,
                MatchStats.home_rolling_conceded,
                MatchStats.home_rolling_win_rate,
                MatchStats.away_rolling_scored,
                MatchStats.away_rolling_conceded,
                MatchStats.away_rolling_win_rate,
            )
            .join(MatchStats, MatchStats.match_id == FootballMatch.id)
            .join(HomeTeam, HomeTeam.id == FootballMatch.home_team_id)
            .join(AwayTeam, AwayTeam.id == FootballMatch.away_team_id)
            .filter(FootballMatch.result.isnot(None))
            .all()
        )

        return pd.DataFrame(rows, columns=[
            "league_season", "Result", "HomeTeam", "AwayTeam",
            "home_goals_scored_home",   "home_goals_conceded_home",   "home_win_rate_home",
            "away_goals_scored_away",   "away_goals_conceded_away",   "away_win_rate_away",
            "home_season_rank",         "away_season_rank",
            "home_rolling_scored",      "home_rolling_conceded",      "home_rolling_win_rate",
            "away_rolling_scored",      "away_rolling_conceded",      "away_rolling_win_rate",
        ])

    # ─────────────────────────────────────────────────────────────────────
    # Étape 2 — Construction du pipeline sklearn
    # ─────────────────────────────────────────────────────────────────────

    def _build_pipeline(self) -> CalibratedClassifierCV:
        """
        Construit le pipeline sklearn identique au notebook ML_pipeline_final.
        """
        preprocessor = ColumnTransformer(transformers=[
            ("num", StandardScaler(),                       self._NUM_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), self._CAT_FEATURES),
        ])

        rf_base = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            class_weight={0: 1, 1: 4, 2: 1},
            random_state=42,
        )

        pipeline_base = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier",   rf_base),
        ])

        return CalibratedClassifierCV(
            estimator=pipeline_base,
            method="sigmoid",
            cv=5,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Étape 3 — Sauvegarde du modèle
    # ─────────────────────────────────────────────────────────────────────

    def _save_model(self, model: CalibratedClassifierCV, version: str) -> None:
        """
        Sauvegarde le modèle en deux fichiers :
            - match_model_<version>.joblib  -> archive versionnée
            - match_model_v1.joblib         -> modèle courant
        """
        model_dir = Path(settings.MODEL_PATH).parent
        model_dir.mkdir(exist_ok=True)

        joblib.dump(model, model_dir / f"match_model_{version}.joblib")
        joblib.dump(model, Path(settings.MODEL_PATH))

    # ─────────────────────────────────────────────────────────────────────
    # Étape 4 — Population de la Feature Store (TeamStatsReference)
    # ─────────────────────────────────────────────────────────────────────

    def _populate_feature_store(self, df: pd.DataFrame, db: Session) -> None:
        """
        Calcule les features agrégées par équipe/saison et les persiste
        dans team_stats_reference.
        """
        seasons = df["league_season"].unique()

        for season in seasons:
            db.query(TeamStatsReference).filter(
                TeamStatsReference.season == int(season)
            ).delete()

        home_stats = df.groupby(["league_season", "HomeTeam"]).agg(
            goals_scored_home     = ("home_goals_scored_home",   "last"),
            goals_conceded_home   = ("home_goals_conceded_home", "last"),
            win_rate_home         = ("home_win_rate_home",       "last"),
            season_rank           = ("home_season_rank",         "last"),
            rolling_scored_home   = ("home_rolling_scored",      "last"),
            rolling_conceded_home = ("home_rolling_conceded",    "last"),
            rolling_win_rate_home = ("home_rolling_win_rate",    "last"),
        ).reset_index().rename(columns={
            "HomeTeam":      "team",
            "league_season": "season",
        })

        away_stats = df.groupby(["league_season", "AwayTeam"]).agg(
            goals_scored_away     = ("away_goals_scored_away",   "last"),
            goals_conceded_away   = ("away_goals_conceded_away", "last"),
            win_rate_away         = ("away_win_rate_away",       "last"),
            rolling_scored_away   = ("away_rolling_scored",      "last"),
            rolling_conceded_away = ("away_rolling_conceded",    "last"),
            rolling_win_rate_away = ("away_rolling_win_rate",    "last"),
        ).reset_index().rename(columns={
            "AwayTeam":      "team",
            "league_season": "season",
        })

        merged = pd.merge(home_stats, away_stats, on=["season", "team"], how="outer")

        for _, row in merged.iterrows():
            db.add(TeamStatsReference(
                team   = row["team"],
                season = int(row["season"]),
                goals_scored_home     = row.get("goals_scored_home"),
                goals_conceded_home   = row.get("goals_conceded_home"),
                win_rate_home         = row.get("win_rate_home"),
                season_rank           = row.get("season_rank"),
                rolling_scored_home   = row.get("rolling_scored_home"),
                rolling_conceded_home = row.get("rolling_conceded_home"),
                rolling_win_rate_home = row.get("rolling_win_rate_home"),
                goals_scored_away     = row.get("goals_scored_away"),
                goals_conceded_away   = row.get("goals_conceded_away"),
                win_rate_away         = row.get("win_rate_away"),
                rolling_scored_away   = row.get("rolling_scored_away"),
                rolling_conceded_away = row.get("rolling_conceded_away"),
                rolling_win_rate_away = row.get("rolling_win_rate_away"),
            ))

        db.commit()

    # ─────────────────────────────────────────────────────────────────────
    # Étape 5 — Logging MLflow
    # ─────────────────────────────────────────────────────────────────────

    def _log_mlflow(
        self,
        model:   CalibratedClassifierCV,
        X:       pd.DataFrame,
        y:       np.ndarray,
        cv_acc:  np.ndarray,
        cv_ll:   np.ndarray,
        version: str,
    ) -> None:
        """
        Logue le run dans MLflow — identique au notebook ML_pipeline_final.
        """
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment("ML model for match prediction")

        with mlflow.start_run(run_name=f"Calibrated_RF_{version}"):

            mlflow.log_param("model_type",         "CalibratedRandomForest")
            mlflow.log_param("n_estimators",        200)
            mlflow.log_param("max_depth",           10)
            mlflow.log_param("class_weight",        str({0: 1, 1: 4, 2: 1}))
            mlflow.log_param("calibration_method", "sigmoid")
            mlflow.log_param("cv_folds",            5)
            mlflow.log_param("n_samples",           len(X))

            mlflow.log_metric("cv_accuracy_mean", round(float(cv_acc.mean()), 4))
            mlflow.log_metric("cv_log_loss_mean", round(float(-cv_ll.mean()), 4))

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            model.fit(X_train, y_train)
            y_pred  = model.predict(X_test)
            y_proba = model.predict_proba(X_test)

            mlflow.log_metric("test_accuracy", round(accuracy_score(y_test, y_pred), 4))

            mlflow.sklearn.log_model(model, name="match_prediction_model")

    # ─────────────────────────────────────────────────────────────────────
    # Étape 6 — Enregistrement dans TrainLog
    # ─────────────────────────────────────────────────────────────────────

    def _save_train_log(
        self,
        db:      Session,
        version: str,
        n:       int,
        acc:     float,
        ll:      float,
    ) -> None:
        """Enregistre les métriques d'entraînement dans train_log."""
        db.add(TrainLog(
            model_version = version,
            n_samples     = n,
            cv_accuracy   = acc,
            cv_log_loss   = ll,
            status        = "success",
        ))
        db.commit()

    # ─────────────────────────────────────────────────────────────────────
    # Point d'entrée public — entraînement
    # ─────────────────────────────────────────────────────────────────────

    def train(self, db: Session) -> Dict:
        """
        Exécute le pipeline complet d'entraînement.
        """
        # 1. Chargement
        df = self._load_from_db(db)

        if df.empty:
            raise ValueError(
                "Aucun match disponible en base. "
                "Lancez d'abord POST /data/prepare."
            )

        le = LabelEncoder()
        X  = df[self._NUM_FEATURES + self._CAT_FEATURES]
        y  = le.fit_transform(df["Result"])

        # 2. Construction
        calibrated = self._build_pipeline()

        # 3. Évaluation
        cv_acc = cross_val_score(calibrated, X, y, cv=5, scoring="accuracy")
        cv_ll  = cross_val_score(calibrated, X, y, cv=5, scoring="neg_log_loss")

        # 4. Entraînement final
        calibrated.fit(X, y)

        # 5. Sauvegarde
        version = date.today().strftime("%Y%m%d")
        self._save_model(calibrated, version)

        from ..services.ml_service import ml_service
        ml_service.model           = calibrated
        ml_service.is_model_loaded = True

        # 6. Logging MLflow — ne bloque jamais le train si erreur
        try:
            self._log_mlflow(
                model   = self._build_pipeline(),
                X       = X,
                y       = y,
                cv_acc  = cv_acc,
                cv_ll   = cv_ll,
                version = version,
            )
        except Exception as e:
            print(f"Avertissement MLflow : {e}")

        # 7. Feature Store
        self._populate_feature_store(df, db)
        ml_service.load_stats_from_db(db)

        # 8. TrainLog
        cv_accuracy = round(float(cv_acc.mean()), 4)
        cv_log_loss = round(float(-cv_ll.mean()), 4)
        self._save_train_log(db, version, len(df), cv_accuracy, cv_log_loss)

        return {
            "status":        "success",
            "model_version": version,
            "cv_accuracy":   cv_accuracy,
            "cv_log_loss":   cv_log_loss,
            "n_samples":     len(df),
        }

    # ─────────────────────────────────────────────────────────────────────
    # Point d'entrée public — historique
    # ─────────────────────────────────────────────────────────────────────

    def get_history(self, db: Session, limit: int = 20) -> list:
        """Retourne l'historique des entraînements depuis train_log."""
        logs = db.query(TrainLog).order_by(
            TrainLog.created_at.desc()
        ).limit(limit).all()

        return [{
            "id":            l.id,
            "created_at":    l.created_at,
            "model_version": l.model_version,
            "n_samples":     l.n_samples,
            "cv_accuracy":   l.cv_accuracy,
            "cv_log_loss":   l.cv_log_loss,
            "status":        l.status,
        } for l in logs]


# Singleton
pipeline_service = PipelineService()