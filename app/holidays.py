import os
import json
import logging
from datetime import datetime
import numpy as np

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings

PROJECT_ROOT = settings.PROJECT_ROOT
CONFIG_DIR = settings.CONFIG_DIR
HOLIDAYS_DIR = settings.HOLIDAYS_DIR

logger = logging.getLogger(__name__)

RELIGIOUS_KEYWORDS = [
    "aid", "aïd", "fitr", "adha", "moharram", "hégir", "hegir", "mawlid", "nabawi", "ennabaoui"
]
EXCEPTIONAL_KEYWORDS = [
    "pont", "exceptionnel", "exceptionnelle"
]


def classify_holiday_type(name: str) -> str:
    name_lower = name.lower()
    for kw in EXCEPTIONAL_KEYWORDS:
        if kw in name_lower:
            return "exceptional"
    for kw in RELIGIOUS_KEYWORDS:
        if kw in name_lower:
            return "religious"
    return "national"


def normalize_religious_name(name: str) -> str:
    name_lower = name.lower()
    if "fitr" in name_lower:
        return "Aïd Al-Fitr"
    if "adha" in name_lower:
        return "Aïd Al-Adha"
    if "moharram" in name_lower or "hégir" in name_lower or "hegir" in name_lower:
        return "1er Moharram (Nouvel An Hégirien)"
    if "mawlid" in name_lower or "nabawi" in name_lower or "ennabaoui" in name_lower:
        return "Aïd Al-Mawlid"
    return name


def migrate_historical_holidays():
    """
    Migre le fichier historique multi-années Joursferiés2026.json
    en fichiers annuels indépendants (2021.json, 2022.json, ..., 2026.json).
    """
    os.makedirs(HOLIDAYS_DIR, exist_ok=True)
    legacy_file = os.path.join(HOLIDAYS_DIR, "Joursferiés2026.json")

    if not os.path.exists(legacy_file):
        logger.warning(f"Fichier historique introuvable: {legacy_file}")
        return

    with open(legacy_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Regrouper par année
    years_data = {}
    for entry in data:
        raw_date = entry.get("date")
        raw_nom = entry.get("nom", "").strip()
        if not raw_date or not raw_nom:
            continue
        
        try:
            dt = datetime.strptime(raw_date, "%Y-%m-%d")
            year = dt.year
        except ValueError:
            logger.error(f"Format de date invalide dans l'historique: {raw_date}")
            continue

        if year not in years_data:
            years_data[year] = []
        years_data[year].append({"date": raw_date, "nom": raw_nom})

    for year, entries in sorted(years_data.items()):
        yearly_filepath = os.path.join(HOLIDAYS_DIR, f"{year}.json")
        # Si le fichier existe déjà, ne pas le réécraser silencieusement
        if os.path.exists(yearly_filepath):
            continue

        # Traitement des doublons et structuration par fêtes
        grouped_holidays = {}
        seen_dates = set()
        suspicious_duplicates = []

        for item in entries:
            d = item["date"]
            nom = item["nom"]
            if d in seen_dates:
                suspicious_duplicates.append(d)
            seen_dates.add(d)

            htype = classify_holiday_type(nom)
            if htype == "religious":
                norm_name = normalize_religious_name(nom)
            else:
                norm_name = nom

            group_key = f"{htype}:{norm_name}"
            if group_key not in grouped_holidays:
                grouped_holidays[group_key] = {
                    "id": f"h_{year}_{len(grouped_holidays) + 1}",
                    "name": norm_name,
                    "type": htype,
                    "status": "validated",
                    "dates": []
                }
            if d not in grouped_holidays[group_key]["dates"]:
                grouped_holidays[group_key]["dates"].append(d)

        if suspicious_duplicates:
            logger.warning(f"Doublons de dates détectés dans l'historique pour {year}: {suspicious_duplicates}")

        # Trier les dates dans chaque fête
        holidays_list = list(grouped_holidays.values())
        for h in holidays_list:
            h["dates"].sort()

        calendar_obj = {
            "year": year,
            "status": "validated",
            "holidays": holidays_list
        }

        with open(yearly_filepath, 'w', encoding='utf-8') as f:
            json.dump(calendar_obj, f, ensure_ascii=False, indent=2)

        logger.info(f"Calendrier {year}.json créé avec succès à partir de l'historique.")


def get_available_years():
    """
    Retourne la liste de toutes les années de calendrier disponibles avec leur statut.
    """
    migrate_historical_holidays()
    years = []
    if not os.path.exists(HOLIDAYS_DIR):
        return []

    for filename in os.listdir(HOLIDAYS_DIR):
        if filename.endswith(".json") and filename[:-5].isdigit():
            year = int(filename[:-5])
            filepath = os.path.join(HOLIDAYS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cal = json.load(f)
                    years.append({
                        "year": year,
                        "status": cal.get("status", "draft")
                    })
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de {filename}: {e}")

    years.sort(key=lambda x: x["year"])
    return years


def load_calendar(year: int):
    """
    Charge le calendrier d'une année spécifique.
    """
    migrate_historical_holidays()
    filepath = os.path.join(HOLIDAYS_DIR, f"{year}.json")
    if not os.path.exists(filepath):
        raise ValueError(f"Le calendrier pour l'année {year} n'existe pas.")

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_calendar(year: int, calendar_data: dict):
    """
    Enregistre les modifications d'un calendrier (en mode draft ou validated).
    """
    os.makedirs(HOLIDAYS_DIR, exist_ok=True)
    filepath = os.path.join(HOLIDAYS_DIR, f"{year}.json")

    # Toujours s'assurer que year correspond
    calendar_data["year"] = int(year)
    if "status" not in calendar_data:
        calendar_data["status"] = "draft"
    if "holidays" not in calendar_data:
        calendar_data["holidays"] = []

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(calendar_data, f, ensure_ascii=False, indent=2)

    return calendar_data


def create_next_year_calendar(from_year: int):
    """
    Génère le calendrier brouillon de l'année suivante (from_year + 1) :
    - Copie les fêtes nationales récurrentes en décalant l'année.
    - Copie les définitions des fêtes religieuses sans dates (dates: [], status: 'pending').
    - N'importe PAS les jours exceptionnels / ponts.
    """
    source_cal = load_calendar(from_year)
    target_year = from_year + 1
    target_filepath = os.path.join(HOLIDAYS_DIR, f"{target_year}.json")

    if os.path.exists(target_filepath):
        raise ValueError(f"Le calendrier pour l'année {target_year} existe déjà.")

    new_holidays = []
    idx = 1

    for item in source_cal.get("holidays", []):
        htype = item.get("type", "national")
        name = item.get("name", "")

        # EXCEPTIONNELS : Ne pas copier
        if htype == "exceptional":
            continue

        # NATIONALES : Décaler les dates
        if htype == "national":
            shifted_dates = []
            for d_str in item.get("dates", []):
                try:
                    dt = datetime.strptime(d_str, "%Y-%m-%d")
                    shifted_date = f"{target_year:04d}-{dt.month:02d}-{dt.day:02d}"
                    shifted_dates.append(shifted_date)
                except ValueError:
                    pass

            new_holidays.append({
                "id": f"h_{target_year}_{idx}",
                "name": name,
                "type": "national",
                "status": "validated",
                "dates": shifted_dates
            })
            idx += 1

        # RELIGIEUSES : Créer comme à valider (pending) avec dates vides
        elif htype == "religious":
            new_holidays.append({
                "id": f"h_{target_year}_{idx}",
                "name": name,
                "type": "religious",
                "status": "pending",
                "dates": []
            })
            idx += 1

    new_calendar = {
        "year": target_year,
        "status": "draft",
        "holidays": new_holidays
    }

    return new_calendar


def validate_calendar(year: int):
    """
    Valide un calendrier d'une année :
    Vérifie qu'aucune fête n'est en attente (status 'pending' ou dates vides pour religieuses/nationales),
    qu'il n'y a pas de doublons de dates, et passe le statut global à 'validated'.
    """
    cal = load_calendar(year)
    all_dates = []
    pending_items = []

    for h in cal.get("holidays", []):
        htype = h.get("type")
        dates = h.get("dates", [])
        name = h.get("name", "")

        if not dates:
            pending_items.append(name)

        for d_str in dates:
            try:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                if dt.year != year:
                    raise ValueError(f"La date {d_str} n'appartient pas à l'année {year}.")
                all_dates.append(d_str)
            except ValueError as e:
                raise ValueError(f"Date invalide '{d_str}' pour la fête '{name}': {e}")

    if pending_items:
        raise ValueError(
            f"Impossible de valider le calendrier {year} : des dates doivent être renseignées pour : {', '.join(pending_items)}."
        )

    # Détection de doublons
    duplicates = [d for d in set(all_dates) if all_dates.count(d) > 1]
    if duplicates:
        raise ValueError(f"Doublons de dates détectés dans le calendrier {year} : {', '.join(duplicates)}")

    # Tout est valide -> passage des éléments et du calendrier en 'validated'
    for h in cal.get("holidays", []):
        h["status"] = "validated"

    cal["status"] = "validated"
    save_calendar(year, cal)
    return cal


def reopen_calendar(year: int):
    """
    Repasse un calendrier du statut 'validated' vers 'draft'.
    """
    cal = load_calendar(year)
    cal["status"] = "draft"
    save_calendar(year, cal)
    return cal


def get_all_validated_holiday_dates() -> list:
    """
    Discovers and loads all validated annual holiday calendar files available in HOLIDAYS_DIR.
    Returns a sorted list of np.datetime64['D'] dates across all validated years.
    Raises ValueError if any existing annual calendar file has status != 'validated'.
    """
    migrate_historical_holidays()
    all_dates = []
    if not os.path.exists(HOLIDAYS_DIR):
        return []

    for filename in sorted(os.listdir(HOLIDAYS_DIR)):
        if filename.endswith(".json") and filename[:-5].isdigit():
            year = int(filename[:-5])
            filepath = os.path.join(HOLIDAYS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                cal = json.load(f)

            if cal.get("status") != "validated":
                raise ValueError(
                    f"Le calendrier des jours fériés pour l'année {year} est au statut '{cal.get('status', 'draft')}'. "
                    f"Il doit être validé dans le menu 'Jours fériés' avant de pouvoir générer les KPIs."
                )

            for h in cal.get("holidays", []):
                all_dates.extend(h.get("dates", []))

    return [np.datetime64(d, 'D') for d in sorted(list(set(all_dates)))]


def get_validated_holiday_dates(years: list = None) -> list:
    """
    Récupère la liste plate des dates de jours fériés sous forme de np.datetime64
    pour les années demandées, ou pour toutes les années validées si years est None.
    Lève explicitement un ValueError si une année demandée n'a pas de calendrier validé.
    """
    if years is None:
        return get_all_validated_holiday_dates()

    migrate_historical_holidays()
    all_dates = []

    for year in years:
        filepath = os.path.join(HOLIDAYS_DIR, f"{year}.json")
        if not os.path.exists(filepath):
            raise ValueError(
                f"Le calendrier des jours fériés pour l'année {year} n'existe pas. "
                f"Veuillez le créer et le valider dans le menu 'Jours fériés'."
            )

        with open(filepath, 'r', encoding='utf-8') as f:
            cal = json.load(f)

        if cal.get("status") != "validated":
            raise ValueError(
                f"Le calendrier des jours fériés pour l'année {year} est au statut '{cal.get('status', 'draft')}'. "
                f"Il doit être validé dans le menu 'Jours fériés' avant de pouvoir générer les KPIs."
            )

        for h in cal.get("holidays", []):
            all_dates.extend(h.get("dates", []))

    return [np.datetime64(d, 'D') for d in sorted(list(set(all_dates)))]
