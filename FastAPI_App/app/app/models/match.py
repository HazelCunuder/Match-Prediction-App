from sqlalchemy import (
    Column, Integer, String, Float,
    DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base

class Team(Base):
    __tablename__ = "teams"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    home_matches = relationship(
        "FootballMatch",
        foreign_keys="FootballMatch.home_team_id",
        back_populates="home_team",
    )
    away_matches = relationship(
        "FootballMatch",
        foreign_keys="FootballMatch.away_team_id",
        back_populates="away_team",
    )

class FootballMatch(Base):
    """
    Données brutes importées depuis le CSV après traitement
    """
    __tablename__ = "football_matches"

    id            = Column(Integer, primary_key=True, index=True)
    league_season = Column(Integer, nullable=False, index=True)
    home_team_id  = Column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    away_team_id  = Column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False)
    home_score    = Column(Integer, nullable=True)
    away_score    = Column(Integer, nullable=True)
    date          = Column(String(50), nullable=True)
    time          = Column(String(20), nullable=True)
    result        = Column(String(10), nullable=True)

    # Stats brutes du match
    halftime_home_goals  = Column(Integer, nullable=True)
    halftime_away_goals  = Column(Integer, nullable=True)
    halftime_result      = Column(String(10), nullable=True)
    home_shot            = Column(Integer, nullable=True)
    away_shot            = Column(Integer, nullable=True)
    home_shot_target     = Column(Integer, nullable=True)
    away_shot_target     = Column(Integer, nullable=True)
    home_team_fouls      = Column(Integer, nullable=True)
    away_team_fouls      = Column(Integer, nullable=True)
    home_team_corners    = Column(Integer, nullable=True)
    away_team_corners    = Column(Integer, nullable=True)
    home_yellow_cards    = Column(Integer, nullable=True)
    away_yellow_cards    = Column(Integer, nullable=True)
    home_red_cards       = Column(Integer, nullable=True)
    away_red_cards       = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    stats     = relationship("MatchStats", back_populates="match", uselist=False)

class MatchStats(Base):
    """
    Features calculées par le PreparationService
    """
    __tablename__ = "match_stats"

    id       = Column(Integer, primary_key=True, index=True)
    match_id = Column(
        Integer,
        ForeignKey("football_matches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Stats saison séparées par lieu
    home_goals_scored_home   = Column(Float, nullable=True)
    home_goals_conceded_home = Column(Float, nullable=True)
    home_win_rate_home       = Column(Float, nullable=True)
    away_goals_scored_away   = Column(Float, nullable=True)
    away_goals_conceded_away = Column(Float, nullable=True)
    away_win_rate_away       = Column(Float, nullable=True)
    # result_home   = Column(Float, nullable=True)   
    # result_away   = Column(Float, nullable=True)        

    # Classement
    home_season_rank = Column(Integer, nullable=True)
    away_season_rank = Column(Integer, nullable=True)

    # Rolling averages — forme récente (5 derniers matchs)
    home_rolling_scored   = Column(Float, nullable=True)
    home_rolling_conceded = Column(Float, nullable=True)
    home_rolling_win_rate = Column(Float, nullable=True)
    away_rolling_scored   = Column(Float, nullable=True)
    away_rolling_conceded = Column(Float, nullable=True)
    away_rolling_win_rate = Column(Float, nullable=True)

    match = relationship("FootballMatch", back_populates="stats")


class TeamStatsReference(Base):
    """
    Features agrégées par équipe par saison — consommées par le PredictionService.
    """
    __tablename__ = "team_stats_reference"

    id     = Column(Integer, primary_key=True, index=True)
    team   = Column(String(100), nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)

    # Stats domicile
    goals_scored_home   = Column(Float, nullable=True)
    goals_conceded_home = Column(Float, nullable=True)
    win_rate_home       = Column(Float, nullable=True)

    # Stats extérieur
    goals_scored_away   = Column(Float, nullable=True)
    goals_conceded_away = Column(Float, nullable=True)
    win_rate_away       = Column(Float, nullable=True)

    # Classement
    season_rank = Column(Float, nullable=True)

    # Rolling averages
    rolling_scored_home   = Column(Float, nullable=True)
    rolling_conceded_home = Column(Float, nullable=True)
    rolling_win_rate_home = Column(Float, nullable=True)
    rolling_scored_away   = Column(Float, nullable=True)
    rolling_conceded_away = Column(Float, nullable=True)
    rolling_win_rate_away = Column(Float, nullable=True)

    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class TrainLog(Base):
    """
    Historique de chaque entraînement — Model Registry.
    Enregistré par le PipelineService après chaque cycle d'entraînement.
    """
    __tablename__ = "train_log"

    id            = Column(Integer, primary_key=True, index=True)
    created_at    = Column(DateTime(timezone=True), default=datetime.utcnow)
    model_version = Column(String(50), nullable=False)
    n_samples     = Column(Integer, nullable=False)
    cv_accuracy   = Column(Float, nullable=False)
    cv_log_loss   = Column(Float, nullable=False)
    status        = Column(String(20), nullable=False, default="success")
    error_message = Column(String(500), nullable=True)