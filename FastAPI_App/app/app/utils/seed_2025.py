import sys
import os

# Add the project root to sys.path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.database import SessionLocal, engine
from app.models.match import Team, Match, TeamMatchStats
from sqlalchemy import text

def seed_2025():
    db = SessionLocal()
    try:
        print("--- Début du seeding Ligue 1 2025/2026 ---")
        
        # 1. Nettoyage (Ordre important pour les FK)
        print("Nettoyage des anciennes données...")
        try:
            db.execute(text("DELETE FROM team_match_stats"))
            db.execute(text("DELETE FROM match"))
            db.execute(text("DELETE FROM team"))
            db.commit()
            print("Nettoyage réussi.")
        except Exception as clean_err:
            print(f"Erreur lors du nettoyage: {clean_err}")
            db.rollback()
            # On continue quand même ? Si c'est vide ça passe.

        # 2. Liste des équipes 2025/2026
        teams_data = [
            {"name": "Paris Saint Germain", "logo_url": "https://media.api-sports.io/football/teams/85.png"},
            {"name": "Olympique de Marseille", "logo_url": "https://media.api-sports.io/football/teams/81.png"},
            {"name": "AS Monaco", "logo_url": "https://media.api-sports.io/football/teams/91.png"},
            {"name": "Lille OSC", "logo_url": "https://media.api-sports.io/football/teams/79.png"},
            {"name": "OGC Nice", "logo_url": "https://media.api-sports.io/football/teams/84.png"},
            {"name": "Olympique Lyonnais", "logo_url": "https://media.api-sports.io/football/teams/80.png"},
            {"name": "RC Lens", "logo_url": "https://media.api-sports.io/football/teams/116.png"},
            {"name": "Stade Rennais", "logo_url": "https://media.api-sports.io/football/teams/94.png"},
            {"name": "Stade Brestois 29", "logo_url": "https://media.api-sports.io/football/teams/106.png"},
            {"name": "Toulouse FC", "logo_url": "https://media.api-sports.io/football/teams/96.png"},
            {"name": "RC Strasbourg Alsace", "logo_url": "https://media.api-sports.io/football/teams/95.png"},
            {"name": "Stade de Reims", "logo_url": "https://media.api-sports.io/football/teams/93.png"},
            {"name": "Montpellier HSC", "logo_url": "https://media.api-sports.io/football/teams/82.png"},
            {"name": "AJ Auxerre", "logo_url": "https://media.api-sports.io/football/teams/108.png"},
            {"name": "Angers SCO", "logo_url": "https://media.api-sports.io/football/teams/77.png"},
            {"name": "FC Nantes", "logo_url": "https://media.api-sports.io/football/teams/83.png"},
            {"name": "FC Lorient", "logo_url": "https://media.api-sports.io/football/teams/97.png"},
            {"name": "Paris FC", "logo_url": "https://media.api-sports.io/football/teams/269.png"},
        ]

        print(f"Insertion de {len(teams_data)} équipes...")
        for t in teams_data:
            new_team = Team(name=t["name"], logo_url=t["logo_url"])
            db.add(new_team)
        
        db.commit()
        print("--- Seeding terminé avec succès ---")

    except Exception as e:
        print(f"Erreur lors du seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_2025()
