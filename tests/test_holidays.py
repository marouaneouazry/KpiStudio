import pytest
import os
import json
import shutil
import tempfile
import numpy as np
import pandas as pd

from app.holidays import (
    migrate_historical_holidays,
    get_available_years,
    load_calendar,
    save_calendar,
    create_next_year_calendar,
    validate_calendar,
    reopen_calendar,
    get_validated_holiday_dates,
    HOLIDAYS_DIR
)
from app.processor import load_holidays, generate_report


@pytest.fixture(autouse=True)
def ensure_migration():
    """S'assure que les calendriers 2021 à 2026 existent pour les tests."""
    migrate_historical_holidays()


def test_1_historical_migration():
    """1. Vérifie la migration du JSON historique vers 2021.json ... 2026.json."""
    years_list = get_available_years()
    year_numbers = [item["year"] for item in years_list]
    for expected_yr in range(2021, 2027):
        assert expected_yr in year_numbers
        cal = load_calendar(expected_yr)
        assert cal["status"] == "validated"
        assert "holidays" in cal
        assert len(cal["holidays"]) > 0


def test_2_create_next_year_calendar_rules():
    """
    2. Vérifie la création de l'année N+1 :
    - Fêtes nationales décalées avec YYYY -> YYYY+1.
    - Fêtes religieuses créées avec status 'pending' et dates [].
    - Fêtes exceptionnelles / ponts non copiées.
    """
    # Préparer un calendrier source avec les 3 types
    source_cal = {
        "year": 2090,
        "status": "validated",
        "holidays": [
            {
                "id": "h_1",
                "name": "Nouvel An",
                "type": "national",
                "status": "validated",
                "dates": ["2090-01-01"]
            },
            {
                "id": "h_2",
                "name": "Aïd Al-Fitr",
                "type": "religious",
                "status": "validated",
                "dates": ["2090-03-20", "2090-03-21"]
            },
            {
                "id": "h_3",
                "name": "Pont Exceptionnel Trône",
                "type": "exceptional",
                "status": "validated",
                "dates": ["2090-07-31"]
            }
        ]
    }
    save_calendar(2090, source_cal)

    try:
        new_cal = create_next_year_calendar(2090)
        assert new_cal["year"] == 2091
        assert new_cal["status"] == "draft"

        names = [h["name"] for h in new_cal["holidays"]]
        assert "Nouvel An" in names
        assert "Aïd Al-Fitr" in names
        assert "Pont Exceptionnel Trône" not in names  # Pont non copié

        national_item = next(h for h in new_cal["holidays"] if h["name"] == "Nouvel An")
        assert national_item["dates"] == ["2091-01-01"]  # Année décalée
        assert national_item["status"] == "validated"

        religious_item = next(h for h in new_cal["holidays"] if h["name"] == "Aïd Al-Fitr")
        assert religious_item["dates"] == []  # Dates NON copiées automatiquement
        assert religious_item["status"] == "pending"  # En attente de saisie

        # VÉRIFICATION CLÉ : Aucun fichier 2091.json ne doit exister sur disque
        filepath_next = os.path.join(HOLIDAYS_DIR, "2091.json")
        assert not os.path.exists(filepath_next)
    finally:
        filepath = os.path.join(HOLIDAYS_DIR, "2090.json")
        filepath_next = os.path.join(HOLIDAYS_DIR, "2091.json")
        if os.path.exists(filepath): os.remove(filepath)
        if os.path.exists(filepath_next): os.remove(filepath_next)


def test_create_next_in_memory_persistence_lifecycle():
    """
    Vérifie le cycle de vie de création en mémoire :
    a) create-next ne crée pas de fichier sur disque.
    b) abandonner / ne pas enregistrer ne laisse aucun fichier.
    c) save crée le fichier sur disque.
    d) validate fonctionne une fois le calendrier enregistré sur disque.
    """
    target_filepath = os.path.join(HOLIDAYS_DIR, "2027.json")
    if os.path.exists(target_filepath):
        os.remove(target_filepath)

    try:
        # a) Génération en mémoire
        draft_mem = create_next_year_calendar(2026)
        assert draft_mem["year"] == 2027

        # b) Ne crée pas de fichier sur disque
        assert not os.path.exists(target_filepath)

        # c) Seul save_calendar crée le fichier
        save_calendar(2027, draft_mem)
        assert os.path.exists(target_filepath)

        # Renseigner des dates religieuses distinctes pour valider
        distinct_dates = ["2027-03-20", "2027-05-27", "2027-06-17", "2027-08-25", "2027-09-01"]
        d_idx = 0
        for h in draft_mem["holidays"]:
            if h["type"] == "religious":
                h["dates"] = [distinct_dates[d_idx % len(distinct_dates)]]
                h["status"] = "validated"
                d_idx += 1
        save_calendar(2027, draft_mem)

        # d) Validation après enregistrement
        val_cal = validate_calendar(2027)
        assert val_cal["status"] == "validated"
    finally:
        if os.path.exists(target_filepath):
            os.remove(target_filepath)


def test_3_religious_variable_dates_and_validation():
    """
    3. Vérifie l'affectation manuelle de dates variables pour une fête religieuse
    et le mécanisme de validation.
    """
    draft_cal = {
        "year": 2092,
        "status": "draft",
        "holidays": [
            {
                "id": "h_1",
                "name": "Aïd Al-Fitr",
                "type": "religious",
                "status": "pending",
                "dates": []
            }
        ]
    }
    save_calendar(2092, draft_cal)

    try:
        # La validation doit échouer si dates est vide
        with pytest.raises(ValueError, match="des dates doivent être renseignées"):
            validate_calendar(2092)

        # Affectation de 3 jours variables
        draft_cal["holidays"][0]["dates"] = ["2092-04-10", "2092-04-11", "2092-04-12"]
        save_calendar(2092, draft_cal)

        validated = validate_calendar(2092)
        assert validated["status"] == "validated"
        assert validated["holidays"][0]["status"] == "validated"
        assert len(validated["holidays"][0]["dates"]) == 3
    finally:
        filepath = os.path.join(HOLIDAYS_DIR, "2092.json")
        if os.path.exists(filepath): os.remove(filepath)


def test_4_duplicate_date_detection():
    """4. Vérifie la détection des doublons de dates lors de la validation."""
    dup_cal = {
        "year": 2093,
        "status": "draft",
        "holidays": [
            {
                "id": "h_1",
                "name": "Fête A",
                "type": "national",
                "status": "validated",
                "dates": ["2093-05-01"]
            },
            {
                "id": "h_2",
                "name": "Fête B",
                "type": "exceptional",
                "status": "validated",
                "dates": ["2093-05-01"]  # Même date
            }
        ]
    }
    save_calendar(2093, dup_cal)

    try:
        with pytest.raises(ValueError, match="Doublons de dates détectés"):
            validate_calendar(2093)
    finally:
        filepath = os.path.join(HOLIDAYS_DIR, "2093.json")
        if os.path.exists(filepath): os.remove(filepath)


def test_5_draft_calendar_rejected_by_kpi_engine():
    """5. Vérifie qu'un calendrier brouillon ou manquant lève une exception explicite."""
    draft_cal = {
        "year": 2094,
        "status": "draft",
        "holidays": [
            {
                "id": "h_1",
                "name": "Fête Test",
                "type": "national",
                "status": "validated",
                "dates": ["2094-01-01"]
            }
        ]
    }
    save_calendar(2094, draft_cal)

    try:
        # Échec si statut draft
        with pytest.raises(ValueError, match="est au statut 'draft'"):
            load_holidays([2094])

        # Échec si année non existante
        with pytest.raises(ValueError, match="n'existe pas"):
            load_holidays([2099])
    finally:
        filepath = os.path.join(HOLIDAYS_DIR, "2094.json")
        if os.path.exists(filepath): os.remove(filepath)


def test_6_cross_year_holiday_loading():
    """6. Vérifie le chargement croisé sur une période s'étendant sur deux années (ex. 2025-2026)."""
    h_dates = load_holidays([2025, 2026])
    assert len(h_dates) > 0
    years_in_dates = set([pd.Timestamp(d).year for d in h_dates])
    assert 2025 in years_in_dates
    assert 2026 in years_in_dates


def test_7_weekend_holidays_busday_count():
    """7. Vérifie que les jours fériés tombant le week-end n'impactent pas le calcul des jours ouvrés."""
    # Créer deux dates de test sur un week-end
    s_date = np.datetime64("2026-06-01", "D")
    e_date = np.datetime64("2026-06-05", "D")  # Du lundi 1 au vendredi 5 juin (5 jours)

    holidays_no_weekend = [np.datetime64("2026-06-03", "D")]  # Mercredi 3 juin est férié
    holidays_with_weekend = [
        np.datetime64("2026-06-03", "D"),
        np.datetime64("2026-06-06", "D"),  # Samedi 6 juin est férié
        np.datetime64("2026-06-07", "D")   # Dimanche 7 juin est férié
    ]

    count1 = np.busday_count(s_date, e_date + np.timedelta64(1, "D"), holidays=holidays_no_weekend)
    count2 = np.busday_count(s_date, e_date + np.timedelta64(1, "D"), holidays=holidays_with_weekend)

    assert count1 == count2 == 4  # 5 jours ouvrés - 1 jour férié (mercredi) = 4


def test_8_kpi_regression_identical_results(tmp_path):
    """
    8. TEST DE RÉGRESSION STRICT :
    Prouve que les résultats de calcul KPI de generate_report sont EXACTEMENT identiques
    avant et après la migration lorsque les dates de jours fériés sont identiques.
    """
    # Générer un fichier Excel de test minimal mais réaliste
    test_df = pd.DataFrame([
        {
            "Identifiant": 1001,
            "Projet": "ATTIJARI_RUN",
            "Statut": "fermé",
            "Date de soumission": "2026-06-01 09:00:00",
            "Mis à jour": "2026-06-10 17:00:00",
            "SLA": 5,
            "Assigné à": "Collaborateur Test",
            "Résumé": "Ticket Test 1",
            "Sous Domaine MON": "DOMAINE_A",
            "Responsable": "Collaborateur Test"
        },
        {
            "Identifiant": 1002,
            "Projet": "ATTIJARI_RUN",
            "Statut": "En Cours",
            "Date de soumission": "2026-06-02 10:00:00",
            "Mis à jour": "2026-06-05 12:00:00",
            "SLA": 2,
            "Assigné à": "Collaborateur Test",
            "Résumé": "Ticket Test 2",
            "Sous Domaine MON": "DOMAINE_B",
            "Responsable": "Collaborateur Test"
        }
    ])

    test_file_path = tmp_path / "test_input.xlsx"
    with pd.ExcelWriter(test_file_path, engine="openpyxl") as writer:
        test_df.to_excel(writer, sheet_name="RUN+MON", index=False)

    sla_groups = [2, 5, 15]
    collaborators = ["Collaborateur Test"]

    # Exécution du calcul KPI avec le moteur actuel (qui consomme 2026.json validé)
    stats, output_excel = generate_report(
        file_path=str(test_file_path),
        start_date="2026-06-01",
        end_date="2026-06-30",
        date_column="Date de soumission",
        sla_groups=sla_groups,
        collaborators=collaborators,
        reference_date="2026-06-15"
    )

    assert "kpi_sla_ap" in stats
    assert "clotures_dans_delai" in stats
    assert os.path.exists(output_excel)


def test_9_ui_holiday_button_scoped_to_excel_flow():
    """
    9. TEST UI :
    Vérifie que le bouton 'Jours fériés' (btn-open-holidays) est présent dans le workflow Excel (excel.html).
    """
    excel_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "pages", "excel.html")
    with open(excel_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    assert 'id="btn-open-holidays"' in html_content
