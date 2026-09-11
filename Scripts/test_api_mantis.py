"""
Script exploratoire — Phase 2 : API REST Mantis

Objectif : vérifier que le token fonctionne, et surtout voir la VRAIE structure
du champ "history" pour un ticket qui a changé de statut (pas juste un ticket
fraîchement créé) — la documentation officielle ne montre qu'un exemple de
création, pas de changement de statut, donc on ne peut pas deviner le format
exact sans un vrai appel.

Usage :
    python test_api_mantis.py
"""

import requests
import json

# --- À REMPLIR ---
BASE_URL = "https://<URL_DE_TON_MANTIS>"   # ex: https://mantis.attijaribank.ma
TOKEN = "<TON_TOKEN_API>"

# Choisis un ticket CLÔTURÉ que tu connais bien, idéalement un de ceux qu'on a
# examinés ensemble (modifié après coup par un commentaire/duplication) pour
# vérifier en même temps que l'historique retrouve la BONNE date.
TICKET_ID = "58853"  # <-- remplace par un identifiant réel


def main():
    url = f"{BASE_URL}/api/rest/issues/{TICKET_ID}"
    headers = {"Authorization": TOKEN}

    print(f"--> Appel : GET {url}")
    resp = requests.get(url, headers=headers, timeout=10)

    print(f"--> Statut HTTP : {resp.status_code}")
    if resp.status_code != 200:
        print("--> Erreur, contenu brut de la réponse :")
        print(resp.text[:2000])
        return

    data = resp.json()

    if "issues" not in data or not data["issues"]:
        print("--> Réponse inattendue, pas de clé 'issues' :")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        return

    issue = data["issues"][0]

    print("\n=== Informations générales du ticket ===")
    print("Statut actuel :", issue.get("status", {}).get("name"))
    print("Créé le :", issue.get("created_at"))
    print("Mis à jour le :", issue.get("updated_at"))

    print("\n=== Historique brut (\"history\") ===")
    history = issue.get("history", [])
    if not history:
        print("--> Aucun historique retourné. Vérifie que ton token a bien les droits "
              "de lecture sur l'historique, ou que la version de Mantis le supporte "
              "(nécessite Mantis >= 2.9.0).")
    else:
        print(json.dumps(history, indent=2, ensure_ascii=False))

    # Sauvegarde dans un fichier pour qu'on puisse l'analyser ensemble facilement
    with open("mantis_history_sample.json", "w", encoding="utf-8") as f:
        json.dump(issue, f, indent=2, ensure_ascii=False)
    print("\n--> Réponse complète sauvegardée dans mantis_history_sample.json")


if __name__ == "__main__":
    main()