import pytest
import pandas as pd
import tempfile
import os
from app.services.kpi_service import KpiService
from app.domain.kpi.calculator import compute_kpi_metrics

def test_regression_collaborator_filtering():
    """
    REGRESSION TEST 1: Collaborator Filtering
    Verifies that tickets assigned to unselected collaborators are strictly excluded
    from all output sheets and KPI aggregations.
    """
    data = {
        "Identifiant": [101, 102, 103],
        "Projet": ["CDM_RUN", "CDM_MON", "CDM_RUN"],
        "Assigné à": ["User A", "User B", "Unselected User"],
        "Date de soumission": ["2026-06-01", "2026-06-02", "2026-06-03"],
        "Mis à jour": ["2026-06-10", "2026-06-12", "2026-06-15"],
        "Résumé": ["Ticket 1", "Ticket 2", "Ticket 3"],
        "Statut": ["Clôturé", "En Cours", "Clôturé"],
        "Responsable": ["APP", "Filiale", "APP"],
        "Sous Domaine MON": ["Activation Carte", "Création TPE", "Activation Carte"]
    }
    df = pd.DataFrame(data)
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "test_collab_reg.xlsx")
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RUN+MON', index=False)

    service = KpiService()
    stats, _ = service.generate_report(
        file_path=test_file,
        start_date="2026-06-01",
        end_date="2026-06-30",
        date_column="Date de soumission",
        sla_groups=[2, 5, 15],
        collaborators=["User A", "User B"]
    )

    # Ticket 103 assigned to "Unselected User" must NOT be counted anywhere
    assert stats["c3"] + stats["en_cours_dans_delai"] + stats["c4"] == 2
    for ticket in stats["hors_delai_tickets"]:
        assert ticket["assigne"] in ["User A", "User B"]

    if os.path.exists(test_file):
        os.remove(test_file)

def test_regression_status_filtering():
    """
    REGRESSION TEST 2: Exact Status Filtering
    Verifies that ONLY tickets with status 'A Clôturer', 'Clôturé', or 'En Cours' are processed.
    Non-standard statuses ('Nouveau', 'Abandonné', 'Rejeté', 'Mise En Production') must be excluded.
    """
    data = {
        "Identifiant": [201, 202, 203, 204, 205, 206, 207],
        "Projet": ["CDM_RUN"] * 7,
        "Assigné à": ["User A"] * 7,
        "Date de soumission": ["2026-06-01"] * 7,
        "Mis à jour": ["2026-06-10"] * 7,
        "Résumé": [f"Ticket {i}" for i in range(1, 8)],
        "Statut": ["A Clôturer", "Clôturé", "En Cours", "Nouveau", "Abandonné", "Rejeté", "Mise En Production"],
        "Responsable": ["APP"] * 7,
        "Sous Domaine MON": ["Activation Carte"] * 7
    }
    df = pd.DataFrame(data)
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "test_status_reg.xlsx")
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RUN+MON', index=False)

    service = KpiService()
    stats, _ = service.generate_report(
        file_path=test_file,
        start_date="2026-06-01",
        end_date="2026-06-30",
        date_column="Date de soumission",
        sla_groups=[2, 5, 15],
        collaborators=["User A"]
    )

    # Exactly 3 valid status tickets (A Clôturer, Clôturé, En Cours)
    total_processed = stats["c3"] + stats["en_cours_dans_delai"] + stats["c4"]
    assert total_processed == 3

    if os.path.exists(test_file):
        os.remove(test_file)

def test_regression_golden_master_kpi_formula():
    """
    REGRESSION TEST 3: Golden Master KPI Formula
    Verifies that Taux SLA AP = c2 / (c3 + c4)
    Controlled dataset:
      clotures_dans_delai (c2) = 8
      clotures_hors_delai = 2 => total clotures (c3) = 10
      encours_dans_delai = 5
      encours_hors_delai (c4) = 1
    Expected KPI = 8 / (10 + 1) = 72.727...% => "72.7%"
    (NOT (8 + 5) / (10 + 1 + 5) = 81.25%)
    """
    stats = compute_kpi_metrics(
        total_receves=16,
        total_clotures=10,
        total_en_cours=6,
        clotures_dans_delai=8,
        clotures_hors_delai=2,
        encours_dans_delai=5,
        encours_hors_delai=1
    )

    assert stats.taux_sla_ap == "72.7%"
