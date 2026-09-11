import pandas as pd
from typing import List, Union
from pathlib import Path

_TEXT_COLUMNS_TO_SANITIZE = [
    "Identifiant",
    "Projet",
    "Rapporteur",
    "Assigné à",
    "Priorité",
    "Impact",
    "Reproductibilité",
    "Version du produit",
    "Catégorie",
    "Date de soumission",
    "OS",
    "Version de l'OS",
    "Plate-forme",
    "Visibilité",
    "Mis à jour",
    "Résumé",
    "Statut",
    "Résolution",
    "Résolu dans la version",
    "Description",
    "Responsable",
    "Numéro de la DIM",
    "Ticket externe",
    "Sous Domaine MON",
]
REQUIRED_COLUMNS = [
    "Identifiant", "Projet", "Assigné à", "Date de soumission",
    "Mis à jour", "Résumé", "Statut", "Responsable", "Sous Domaine MON"
]

def sanitize_excel_value(value: str) -> str:
    """
    Prevents Excel formula injection attack vectors.
    If string starts with =, +, -, or @, prefixes it with an apostrophe.
    """
    if isinstance(value, str) and value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value

def read_mantis_export(file_path: Union[str, Path], sheet_name: str = 'RUN+MON') -> pd.DataFrame:
    """
    Reads Mantis Excel workbook export (.xlsx / .xlsm), validates required columns,
    normalizes text fields, and applies formula injection protection.
    """
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    except ValueError as e:
        raise ValueError(f"La feuille '{sheet_name}' n'a pas été trouvée dans le fichier Excel.") from e
    except Exception as e:
        raise ValueError(f"Impossible de lire le fichier Excel '{file_path}': {e}") from e

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes: {missing_cols}")

    df = df[REQUIRED_COLUMNS].copy()

    # Normalisation du texte
    if 'Sous Domaine MON' in df.columns:
        df['Sous Domaine MON'] = df['Sous Domaine MON'].astype(str).str.strip()

    for col in _TEXT_COLUMNS_TO_SANITIZE:
        if col in df.columns:
            df[col] = df[col].apply(sanitize_excel_value)

    return df
