import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict

from ..core.config import settings


class MLService:

    def __init__(self):
        # Modèle ML — chargé depuis le fichier joblib au démarrage
        self.model:           object = None
        self.is_model_loaded: bool   = False

        self.home_stats:   pd.DataFrame | None = None
        self.away_stats:   pd.DataFrame | None = None
        self.standings:    pd.DataFrame | None = None
        self.rolling_home: pd.DataFrame | None = None
        self.rolling_away: pd.DataFrame | None = None

    def load_model(self) -> None:
        """
        Charge le modèle depuis le fichier joblib défini dans la configuration.
        """
        model_path = Path(settings.MODEL_PATH)

        if not model_path.exists():
            print(f"Avertissement — modèle introuvable : {model_path}")
            return

        self.model           = joblib.load(model_path)
        self.is_model_loaded = True
        print(f"Modèle chargé : {model_path}")

    def load_stats_from_db(self, db) -> None:
        """
        Charge les statistiques de référence depuis team_stats_reference
        """
        from ..models.match import TeamStatsReference

        stats = db.query(TeamStatsReference).all()

        if not stats:
            print("Avertissement — team_stats_reference est vide. Lancez POST /train d'abord.")
            return

        # Construction des DataFrames à partir des lignes de la BD
        records_home         = []
        records_away         = []
        records_standings    = []
        records_rolling_home = []
        records_rolling_away = []

        for s in stats:
            records_home.append({
                "league.season":     s.season,
                "Team":              s.team,
                "goals_scored_home": s.goals_scored_home,
                "goals_conceded_home": s.goals_conceded_home,
                "win_rate_home":     s.win_rate_home,
            })
            records_away.append({
                "league.season":      s.season,
                "Team":               s.team,
                "goals_scored_away":  s.goals_scored_away,
                "goals_conceded_away": s.goals_conceded_away,
                "win_rate_away":      s.win_rate_away,
            })
            records_standings.append({
                "league.season": s.season,
                "Team":          s.team,
                "season_rank":   s.season_rank,
            })
            records_rolling_home.append({
                "league.season":  s.season,
                "Team":           s.team,
                "rolling_scored":   s.rolling_scored_home,
                "rolling_conceded": s.rolling_conceded_home,
                "rolling_win_rate": s.rolling_win_rate_home,
            })
            records_rolling_away.append({
                "league.season":  s.season,
                "Team":           s.team,
                "rolling_scored":   s.rolling_scored_away,
                "rolling_conceded": s.rolling_conceded_away,
                "rolling_win_rate": s.rolling_win_rate_away,
            })

        self.home_stats   = pd.DataFrame(records_home)
        self.away_stats   = pd.DataFrame(records_away)
        self.standings    = pd.DataFrame(records_standings)
        self.rolling_home = pd.DataFrame(records_rolling_home)
        self.rolling_away = pd.DataFrame(records_rolling_away)

        print(f"Stats chargées depuis la BD : {len(stats)} entrées.")

    def get_stat(
        self,
        team:   str,
        season: int,
        col:    str,
        source: pd.DataFrame,
    ) -> float:
        """
        Récupère une statistique depuis une table de référence
        """
        try:
            return source.set_index(["league.season", "Team"]).loc[(season, team), col]
        except KeyError:
            return 0.0

    def _build_input(
        self,
        home_team: str,
        away_team: str,
        season:    int,
    ) -> pd.DataFrame:
        """
        Construit le DataFrame d'entrée pour le modèle.
        """
        return pd.DataFrame([{
            # Stats saison — équipe à domicile jouant chez elle
            "home_goals_scored_home":   self.get_stat(home_team, season, "goals_scored_home",   self.home_stats),
            "home_goals_conceded_home": self.get_stat(home_team, season, "goals_conceded_home", self.home_stats),
            "home_win_rate_home":       self.get_stat(home_team, season, "win_rate_home",        self.home_stats),
            # Stats saison — équipe à l'extérieur jouant hors de chez elle
            "away_goals_scored_away":   self.get_stat(away_team, season, "goals_scored_away",   self.away_stats),
            "away_goals_conceded_away": self.get_stat(away_team, season, "goals_conceded_away", self.away_stats),
            "away_win_rate_away":       self.get_stat(away_team, season, "win_rate_away",        self.away_stats),
            # Classement
            "home_season_rank": self.get_stat(home_team, season, "season_rank", self.standings),
            "away_season_rank": self.get_stat(away_team, season, "season_rank", self.standings),
            # Rolling averages — forme récente
            "home_rolling_scored":   self.get_stat(home_team, season, "rolling_scored",   self.rolling_home),
            "home_rolling_conceded": self.get_stat(home_team, season, "rolling_conceded", self.rolling_home),
            "home_rolling_win_rate": self.get_stat(home_team, season, "rolling_win_rate", self.rolling_home),
            "away_rolling_scored":   self.get_stat(away_team, season, "rolling_scored",   self.rolling_away),
            "away_rolling_conceded": self.get_stat(away_team, season, "rolling_conceded", self.rolling_away),
            "away_rolling_win_rate": self.get_stat(away_team, season, "rolling_win_rate", self.rolling_away),
            # Contexte
            "league_season": season,
            "HomeTeam":      home_team,
            "AwayTeam":      away_team,
        }])

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        season:    int,
    ) -> Dict:
        """
        Prédit le résultat d'un match à partir des noms des équipes et de la saison.
        """
        # Mapping LabelEncoder : A=0, D=1, H=2
        labels = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}

        df_input    = self._build_input(home_team, away_team, season)
        probs_array = self.model.predict_proba(df_input)[0]
        pred_idx    = int(np.argmax(probs_array))

        return {
            "match":      f"{home_team} vs {away_team}",
            "prediction": labels[pred_idx],
            "confidence": round(float(probs_array[pred_idx]), 4),
            "probabilities": {
                "HOME": round(float(probs_array[2]), 4),
                "DRAW": round(float(probs_array[1]), 4),
                "AWAY": round(float(probs_array[0]), 4),
            },
        }

ml_service = MLService()