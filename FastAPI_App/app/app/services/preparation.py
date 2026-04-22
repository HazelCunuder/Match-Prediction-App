import pandas as pd
from pathlib import Path
from typing import Dict
from pandas import DataFrame
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.match import FootballMatch
from ..core.config import settings


class PreparationService:

    # Colonnes à supprimer après la fusion
    _COLS_TO_DROP = [
        "fixture.id", "Referee", "Round", "fixture.timezone", "fixture.date",
        "fixture.timestamp", "fixture.periods.first", "fixture.periods.second",
        "fixture.venue.id", "fixture.venue.name", "fixture.venue.city",
        "fixture.status.long", "fixture.status.short", "fixture.status.elapsed",
        "fixture.status.extra", "league.id", "league.name", "league.country",
        "league.logo", "league.flag", "league.standings",
        "teams.home.id", "teams.home.logo", "teams.away.id", "teams.home.winner",
        "teams.away.logo", "teams.away.winner", "Div",
        "score.penalty.home", "score.penalty.away",
        "score.extratime.home", "score.extratime.away",
        "goals.home", "goals.away", "score.halftime.home", "score.halftime.away",
        "LBCA", "LBCD", "LBCH", "CLCA", "CLCD", "CLCH", "LBA", "CLH", "CLD",
        "LBH", "LBD", "CLA", "BMGMCH", "BVA", "BFDH", "BFDD", "BFDA", "BFDCA",
        "BMGMD", "BMGMA", "BVH", "BVD", "BMGMH", "BVCA", "BVCH", "BMGMCA",
        "BMGMCD", "BFDCH", "BFDCD", "BVCD", "1XBA", "1XBH", "1XBD", "1XBCH",
        "BFCA", "BFCD", "BFCH", "BFD", "BFA", "BFH", "1XBCA", "1XBCD",
        "IWD", "IWA", "IWCH", "IWCD", "IWCA", "IWH",
        "BFE<2.5", "BFE>2.5", "BFEAHA", "BFEAHH", "BFED", "BFEH", "BFECAHA",
        "BFEA", "BFECA", "BFECAHH", "BFECH", "BFEC>2.5", "BFEC<2.5", "BFECD",
        "VCA", "VCD", "VCH", "VCCH", "VCCA", "VCCD", "WHA", "WHD", "WHH",
        "WHCD", "WHCH", "WHCA", "B365H", "B365D", "B365A", "BWH", "BWD", "BWA",
        "PSH", "PSD", "PSA", "MaxH", "MaxD", "MaxA", "AvgH", "AvgD", "AvgA",
        "B365>2.5", "B365<2.5", "P>2.5", "P<2.5", "Max>2.5", "Max<2.5",
        "Avg>2.5", "Avg<2.5", "AHh", "B365AHH", "B365AHA", "PAHH", "PAHA",
        "MaxAHH", "MaxAHA", "AvgAHH", "AvgAHA", "B365CH", "B365CD", "B365CA",
        "BWCH", "BWCD", "BWCA", "PSCH", "PSCD", "PSCA", "MaxCH", "MaxCD",
        "MaxCA", "AvgCH", "AvgCD", "AvgCA", "B365C>2.5", "B365C<2.5",
        "PC>2.5", "PC<2.5", "MaxC>2.5", "MaxC<2.5", "AvgC>2.5", "AvgC<2.5",
        "AHCh", "B365CAHH", "B365CAHA", "PCAHH", "PCAHA", "MaxCAHH",
        "MaxCAHA", "AvgCAHH", "AvgCAHA",
    ]

    # Colonnes à convertir en entier

    _COLS_INT = [
        "league.season", "HalftimeHomeGoals", "HalftimeAwayGoals",
        "HomeShot", "AwayShot", "HomeShotTarget", "AwayShotTarget",
        "HomeTeamFouls", "AwayTeamFouls", "HomeTeamCorners", "AwayTeamCorners",
        "HomeYellowCards", "AwayYellowCards", "HomeRedCards", "AwayRedCards",
    ]

    # Renommage colonnes API Football

    _RENAME_API = {
        "fixture.referee": "Referee",
        "league.round":    "Round",
        "teams.home.name": "HomeTeam",
        "teams.away.name": "AwayTeam",
        "score.fulltime.home": "HomeScore",
        "score.fulltime.away": "AwayScore",
    }

    # Renommage colonnes football-data.co.uk

    _RENAME_EXT = {
        "FTHG": "HomeScore", "FTAG": "AwayScore", "FTR": "Result",
        "HS": "HomeShot", "AS": "AwayShot",
        "HST": "HomeShotTarget", "AST": "AwayShotTarget",
        "HTHG": "HalftimeHomeGoals", "HTAG": "HalftimeAwayGoals",
        "HTR": "HalftimeResult",
        "HF": "HomeTeamFouls", "AF": "AwayTeamFouls",
        "HC": "HomeTeamCorners", "AC": "AwayTeamCorners",
        "HY": "HomeYellowCards", "AY": "AwayYellowCards",
        "HR": "HomeRedCards", "AR": "AwayRedCards",
    }

    # Harmonisation des noms d'équipes

    _TEAM_NAMES_EXT = {
        "Clermont": "Clermont Foot",
        "Troyes":   "Estac Troyes",
        "Brest":    "Stade Brestois",
    }

    _TEAM_NAMES_API = {
        "Saint Etienne":       "St Etienne",
        "Paris Saint Germain": "Paris SG",
        "Stade Brestois 29":   "Stade Brestois",
    }

    # Étape 1 — Chargement des sources


    def _load_sources(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Charge et concatène les fichiers CSV des deux sources.

        Source 1 : API Football
        Source 2 : football-data.co.uk
        """
        base = Path(settings.DATA_DIR)

        dataset1 = pd.concat([
            pd.read_csv(base / "part1" / "ligue1_2022_completed.csv"),
            pd.read_csv(base / "part1" / "ligue1_2023_completed.csv"),
            pd.read_csv(base / "part1" / "ligue1_2024_completed.csv"),
        ])

        dataset2 = pd.concat([
            pd.read_csv(base / "part2" / "2022_2023.csv"),
            pd.read_csv(base / "part2" / "2023_2024.csv"),
            pd.read_csv(base / "part2" / "2024_2025.csv"),
            pd.read_csv(base / "part2" / "2025_2026.csv"),
        ])

        return dataset1, dataset2

    # Étape 2 — Harmonisation et fusion

    def _harmonise_ext(
        self,
        dataset: pd.DataFrame
    ) -> pd.DataFrame:

        dataset["Date"] = pd.to_datetime(dataset["Date"], format='mixed').dt.date
        dataset.replace(self._TEAM_NAMES_EXT, inplace=True)
        dataset.rename(columns=self._RENAME_EXT, inplace=True)

        return dataset

    def _harmonise_and_merge(
        self,
        dataset1: pd.DataFrame,
        dataset2: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Harmonise les noms de colonnes et d'équipes entre les deux sources,
        puis fusionne via outer join sur (Date, HomeTeam, AwayTeam, scores).
        """
        dataset1["Date"] = pd.to_datetime(dataset1["fixture.date"]).dt.date
        dataset2["Date"] = pd.to_datetime(dataset2["Date"], dayfirst=True).dt.date

        dataset1.replace(self._TEAM_NAMES_API, inplace=True)
        dataset2.replace(self._TEAM_NAMES_EXT, inplace=True)

        dataset1.rename(columns=self._RENAME_API, inplace=True)
        dataset2.rename(columns=self._RENAME_EXT, inplace=True)

        return pd.merge(
            dataset1, dataset2,
            on=["Date", "HomeTeam", "AwayTeam", "HomeScore", "AwayScore"],
            how="outer",
        )

    # Étape 3 — Nettoyage

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Supprime les colonnes inutiles et les lignes sans résultat.
        Convertit les colonnes numériques au bon type.
        """
        existing_cols = [c for c in self._COLS_TO_DROP if c in df.columns]
        df = df.drop(columns=existing_cols)

        if "league.season" in df.columns:
            df["league.season"] = df["league.season"].fillna("2025")
        else:
            print("Warning: 'league.season' column missing, defaulting to 2025")
            df["league.season"] = 2025
        
        df = df.dropna(subset=["Result"]).copy()

        for col in self._COLS_INT:
            if col in df.columns:
                df[col] = df[col].astype(int)

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)

        return df

    # Étape 4 — Feature Engineering : stats par lieu (saison entière)

    @staticmethod
    def _home_points(result: str) -> int:
        return 3 if result == "H" else (1 if result == "D" else 0)

    @staticmethod
    def _away_points(result: str) -> int:
        return 3 if result == "A" else (1 if result == "D" else 0)

    def _add_season_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les statistiques séparées selon le lieu de jeu (domicile / extérieur)
        et insère les features dans le DataFrame via mapping (league.season, team).
        """
        # Stats domicile
        home_stats = df.groupby(["league.season", "HomeTeam"]).agg(
            gs_h=("HomeScore", "sum"),
            gc_h=("AwayScore", "sum"),
            gm_h=("HomeScore", "count"),
            wins_h=("Result", lambda x: (x == "H").sum()),
        ).reset_index().rename(columns={"HomeTeam": "Team"})

        home_stats["goals_scored_home"]   = (home_stats["gs_h"] / home_stats["gm_h"]).round(3)
        home_stats["goals_conceded_home"] = (home_stats["gc_h"] / home_stats["gm_h"]).round(3)
        home_stats["win_rate_home"]       = (home_stats["wins_h"] / home_stats["gm_h"]).round(3)

        # Stats extérieur
        away_stats = df.groupby(["league.season", "AwayTeam"]).agg(
            gs_a=("AwayScore", "sum"),
            gc_a=("HomeScore", "sum"),
            gm_a=("AwayScore", "count"),
            wins_a=("Result", lambda x: (x == "A").sum()),
        ).reset_index().rename(columns={"AwayTeam": "Team"})

        away_stats["goals_scored_away"]   = (away_stats["gs_a"] / away_stats["gm_a"]).round(3)
        away_stats["goals_conceded_away"] = (away_stats["gc_a"] / away_stats["gm_a"]).round(3)
        away_stats["win_rate_away"]       = (away_stats["wins_a"] / away_stats["gm_a"]).round(3)

        # Classement final
        hr = df.groupby(["league.season", "HomeTeam"]).apply(lambda g: pd.Series({
            "pts": g["Result"].apply(self._home_points).sum(),
            "gf":  g["HomeScore"].sum(),
            "ga":  g["AwayScore"].sum(),
        })).reset_index().rename(columns={"HomeTeam": "Team"})

        ar = df.groupby(["league.season", "AwayTeam"]).apply(lambda g: pd.Series({
            "pts": g["Result"].apply(self._away_points).sum(),
            "gf":  g["AwayScore"].sum(),
            "ga":  g["HomeScore"].sum(),
        })).reset_index().rename(columns={"AwayTeam": "Team"})

        standings = pd.concat([hr, ar]).groupby(["league.season", "Team"]).sum().reset_index()
        standings["gd"] = standings["gf"] - standings["ga"]
        standings = standings.sort_values(
            ["league.season", "pts", "gd", "gf"],
            ascending=[True, False, False, False],
        )
        standings["season_rank"] = standings.groupby("league.season").cumcount() + 1

        # Insertion via mapping
        hs = home_stats.set_index(["league.season", "Team"])
        as_ = away_stats.set_index(["league.season", "Team"])
        rs  = standings.set_index(["league.season", "Team"])

        for col, src, key in [
            ("home_goals_scored_home",   hs,  "goals_scored_home"),
            ("home_goals_conceded_home", hs,  "goals_conceded_home"),
            ("home_win_rate_home",       hs,  "win_rate_home"),
            ("away_goals_scored_away",   as_, "goals_scored_away"),
            ("away_goals_conceded_away", as_, "goals_conceded_away"),
            ("away_win_rate_away",       as_, "win_rate_away"),
            ("home_season_rank",         rs,  "season_rank"),
            ("away_season_rank",         rs,  "season_rank"),
        ]:
            team_col = "HomeTeam" if col.startswith("home") else "AwayTeam"
            df[col] = df.set_index(["league.season", team_col]).index.map(src[key])

        return df

    # Étape 5 — Feature Engineering : rolling averages (5 derniers matchs)

    @staticmethod
    def _add_rolling_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Calcule les moyennes mobiles sur les `window` derniers matchs de chaque équipe.

        Le .shift(1) garantit qu'aucune information du match courant n'est incluse
        dans son propre calcul — principe fondamental anti-data leakage.
        """
        df = df.copy()

        # Empiler perspective domicile + extérieur par équipe
        home_df = df[["Date", "HomeTeam", "HomeScore", "AwayScore"]].rename(
            columns={"HomeTeam": "Team", "HomeScore": "scored", "AwayScore": "conceded"}
        )
        away_df = df[["Date", "AwayTeam", "AwayScore", "HomeScore"]].rename(
            columns={"AwayTeam": "Team", "AwayScore": "scored", "HomeScore": "conceded"}
        )
        all_matches = pd.concat([home_df, away_df]).sort_values("Date").reset_index(drop=True)

        # Rolling avec shift(1) — le match courant n'est pas inclus
        all_matches["roll_scored"] = all_matches.groupby("Team")["scored"].transform(
            lambda x: x.shift(1).rolling(window, min_periods=1).mean()
        )
        all_matches["roll_conceded"] = all_matches.groupby("Team")["conceded"].transform(
            lambda x: x.shift(1).rolling(window, min_periods=1).mean()
        )

        # Taux de victoire rolling
        home_wins = df[["Date", "HomeTeam", "Result"]].rename(columns={"HomeTeam": "Team"})
        home_wins["won"] = (home_wins["Result"] == "H").astype(int)
        away_wins = df[["Date", "AwayTeam", "Result"]].rename(columns={"AwayTeam": "Team"})
        away_wins["won"] = (away_wins["Result"] == "A").astype(int)

        all_wins = pd.concat([
            home_wins[["Date", "Team", "won"]],
            away_wins[["Date", "Team", "won"]],
        ]).sort_values("Date")

        all_wins["roll_win_rate"] = all_wins.groupby("Team")["won"].transform(
            lambda x: x.shift(1).rolling(window, min_periods=1).mean()
        )

        # Lookup tables
        stats_lookup = all_matches.groupby(["Date", "Team"])[["roll_scored", "roll_conceded"]].first()
        win_lookup   = all_wins.groupby(["Date", "Team"])["roll_win_rate"].first()

        # Insertion dans le DataFrame principal
        df["home_rolling_scored"]   = df.set_index(["Date", "HomeTeam"]).index.map(stats_lookup["roll_scored"]).fillna(0).round(3).values
        df["home_rolling_conceded"] = df.set_index(["Date", "HomeTeam"]).index.map(stats_lookup["roll_conceded"]).fillna(0).round(3).values
        df["home_rolling_win_rate"] = df.set_index(["Date", "HomeTeam"]).index.map(win_lookup).fillna(0).round(3).values
        df["away_rolling_scored"]   = df.set_index(["Date", "AwayTeam"]).index.map(stats_lookup["roll_scored"]).fillna(0).round(3).values
        df["away_rolling_conceded"] = df.set_index(["Date", "AwayTeam"]).index.map(stats_lookup["roll_conceded"]).fillna(0).round(3).values
        df["away_rolling_win_rate"] = df.set_index(["Date", "AwayTeam"]).index.map(win_lookup).fillna(0).round(3).values

        return df
    
    # Étape 6 — Persistance dans FootballMatch (Raw Data Store)

    def _seed_teams(self, df: pd.DataFrame, db: Session) -> None:
        from ..models.match import Team

        all_teams = set(df["HomeTeam"].unique()) | set(df["AwayTeam"].unique())

        for name in sorted(all_teams):
            exists = db.query(Team).filter(Team.name == name).first()
            if not exists:
                db.add(Team(name=name))

        db.commit()

    def _persist(self, df: pd.DataFrame, db: Session) -> int:
        """
        Insère les matchs dans football_matches et les features dans match_stats.
        Ignore les doublons via (date, home_team_id, away_team_id).
        Retourne le nombre de nouvelles lignes insérées.
        """
        from ..models.match import Team, MatchStats

        # Seed automatique des équipes
        self._seed_teams(df, db)
        
        teams_cache = {t.name: t.id for t in db.query(Team).all()}

        inserted = 0

        for _, row in df.iterrows():
            home_team_id = teams_cache.get(row["HomeTeam"])
            away_team_id = teams_cache.get(row["AwayTeam"])

            # Ignorer si l'équipe n'existe pas
            if not home_team_id or not away_team_id:
                continue

            # Vérifier les doublons
            exists = db.query(FootballMatch).filter(
                FootballMatch.date         == str(row["Date"]),
                FootballMatch.home_team_id == home_team_id,
                FootballMatch.away_team_id == away_team_id,
            ).first()

            if exists:
                continue

            def safe(col: str):
                return float(row[col]) if col in row.index and pd.notna(row[col]) else None

            # Insertion dans football_matches (données brutes)
            match = FootballMatch(
                date          = str(row["Date"]),
                league_season = int(row["league.season"]),
                home_team_id  = home_team_id,
                away_team_id  = away_team_id,
                home_score    = int(row["HomeScore"]) if pd.notna(row.get("HomeScore")) else None,
                away_score    = int(row["AwayScore"]) if pd.notna(row.get("AwayScore")) else None,
                result        = row.get("Result"),
                halftime_home_goals = safe("HalftimeHomeGoals"),
                halftime_away_goals = safe("HalftimeAwayGoals"),
                halftime_result     = row.get("HalftimeResult"),
                home_shot           = safe("HomeShot"),
                away_shot           = safe("AwayShot"),
                home_shot_target    = safe("HomeShotTarget"),
                away_shot_target    = safe("AwayShotTarget"),
                home_team_fouls     = safe("HomeTeamFouls"),
                away_team_fouls     = safe("AwayTeamFouls"),
                home_team_corners   = safe("HomeTeamCorners"),
                away_team_corners   = safe("AwayTeamCorners"),
                home_yellow_cards   = safe("HomeYellowCards"),
                away_yellow_cards   = safe("AwayYellowCards"),
                home_red_cards      = safe("HomeRedCards"),
                away_red_cards      = safe("AwayRedCards"),
            )
            db.add(match)
            db.flush()

            # Insertion dans match_stats (features calculées)
            stats = MatchStats(
                match_id                 = match.id,
                home_goals_scored_home   = safe("home_goals_scored_home"),
                home_goals_conceded_home = safe("home_goals_conceded_home"),
                home_win_rate_home       = safe("home_win_rate_home"),
                away_goals_scored_away   = safe("away_goals_scored_away"),
                away_goals_conceded_away = safe("away_goals_conceded_away"),
                away_win_rate_away       = safe("away_win_rate_away"),
                home_season_rank         = safe("home_season_rank"),
                away_season_rank         = safe("away_season_rank"),
                home_rolling_scored      = safe("home_rolling_scored"),
                home_rolling_conceded    = safe("home_rolling_conceded"),
                home_rolling_win_rate    = safe("home_rolling_win_rate"),
                away_rolling_scored      = safe("away_rolling_scored"),
                away_rolling_conceded    = safe("away_rolling_conceded"),
                away_rolling_win_rate    = safe("away_rolling_win_rate"),
            )
            db.add(stats)
            inserted += 1

        db.commit()
        return inserted

    # Point d'entrée public

    def run(self, db: Session, df: DataFrame) -> Dict:
        # Agrégation avec le nouveau dataset fourni
        additional_dataset = self._harmonise_ext(df)

        clean_df = self._clean(additional_dataset)
        stats_df = self._add_season_stats(clean_df)
        final_df = self._add_rolling_features(stats_df)

        inserted = self._persist(final_df, db)

        total = db.query(func.count(FootballMatch.id)).scalar()

        return {
            "status": "success",
            "inserted": inserted,
            "total": total,
            "message": f"{inserted} nouveaux matchs importés. Total en base : {total}.",
        }

    def run_base(self, db: Session) -> Dict:
        """
        Exécute le pipeline complet de préparation des données.

        Étapes :
            1. Chargement des sources CSV
            2. Harmonisation et fusion
            3. Nettoyage
            4. Feature engineering — stats par lieu
            5. Feature engineering — rolling averages
            6. Persistance dans FootballMatch

        Returns:
            dict avec le nombre de matchs insérés et le total en base.
        """

        # Chargement des deux dataset issues de sources différentes
        dataset1, dataset2 = self._load_sources()
        merged_df          = self._harmonise_and_merge(dataset1, dataset2)

        clean_df           = self._clean(merged_df)
        stats_df           = self._add_season_stats(clean_df)
        final_df           = self._add_rolling_features(stats_df)

        inserted = self._persist(final_df, db)

        total = db.query(func.count(FootballMatch.id)).scalar()

        return {
            "status":   "success",
            "inserted": inserted,
            "total":    total,
            "message":  f"{inserted} nouveaux matchs importés. Total en base : {total}.",
        }

preparation_service = PreparationService()