TEAM_NAME_MAPPING = {
    # LFP Scraper Name -> ML Model Name
    "Angers SCO": "Angers",
    "AJ Auxerre": "Auxerre",
    "Stade Brestois 29": "Stade Brestois",
    "Le Havre AC": "Le Havre",
    "Havre AC": "Le Havre",
    "Havre Athletic Club" : "Le Havre",
    "RC Lens": "Lens",
    "LOSC Lille": "Lille",
    "FC Lorient": "Lorient",
    "Olympique Lyonnais": "Lyon",
    "Olympique de Marseille": "Marseille",
    "FC Metz": "Metz",
    "AS Monaco": "Monaco",
    "FC Nantes": "Nantes",
    "OGC Nice": "Nice",
    "Paris FC": "Paris FC",
    "Paris Saint-Germain": "Paris SG",
    "Stade Rennais FC": "Rennes",
    "RC Strasbourg Alsace": "Strasbourg",
    "Toulouse FC": "Toulouse"
}

def normalize_team(lfp_name: str) -> str:
    """
    Transforme un nom d'équipe complet (LFP) en nom reconnu par le modèle ML.
    """
    # On enlève d'éventuels espaces en trop
    clean_name = lfp_name.strip()
    return TEAM_NAME_MAPPING.get(clean_name, clean_name)
