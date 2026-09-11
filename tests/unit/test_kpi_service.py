import pytest
import pandas as pd
from pathlib import Path
from app.services.kpi_service import KpiService

def test_kpi_service_generate_report_end_to_end(tmp_path):
    df_data = pd.DataFrame({
        "Identifiant": [1001, 1002],
        "Projet": ["PROJ_1", "PROJ_1"],
        "Assigné à": ["User A", "User B"],
        "Date de soumission": ["2026-01-05", "2026-01-06"],
        "Mis à jour": ["2026-01-07", "2026-01-10"],
        "Résumé": ["Summary 1", "Summary 2"],
        "Statut": ["Clôturé", "En cours"],
        "Responsable": ["AP", "Filiale"],
        "Sous Domaine MON": ["Demande d'assistance / conseil", "Demande d'assistance / conseil"]
    })

    file_path = tmp_path / "mantis_test.xlsx"
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df_data.to_excel(writer, sheet_name='RUN+MON', index=False)

    service = KpiService()
    stats, output_file = service.generate_report(
        file_path=file_path,
        start_date="2026-01-01",
        end_date="2026-01-31",
        date_column="Date de soumission",
        sla_groups=[3, 5, 10],
        collaborators=["User A", "User B"],
        reference_date="2026-01-15"
    )

    assert isinstance(stats, dict)
    assert "clotures_dans_delai" in stats
    assert "kpi_sla_ap" in stats
    assert Path(output_file).exists()

def test_kpi_service_generate_report_zero_matching_tickets(tmp_path):
    # Empty dataframe / zero tickets
    df_data = pd.DataFrame(columns=[
        "Identifiant", "Projet", "Assigné à", "Date de soumission",
        "Mis à jour", "Résumé", "Statut", "Responsable", "Sous Domaine MON"
    ])

    file_path = tmp_path / "mantis_empty_test.xlsx"
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df_data.to_excel(writer, sheet_name='RUN+MON', index=False)

    service = KpiService()
    stats, output_file = service.generate_report(
        file_path=file_path,
        start_date="2026-01-01",
        end_date="2026-01-31",
        date_column="Date de soumission",
        sla_groups=[3, 5, 10],
        collaborators=["User A"],
        reference_date="2026-01-15"
    )

    assert isinstance(stats, dict)
    assert stats["clotures_dans_delai"] == 0
    assert stats["clotures_hors_delai"] == 0
    assert stats["en_cours_dans_delai"] == 0
    assert stats["en_cours_hors_delai"] == 0
    assert stats["kpi_sla_ap"] == "0.0%"
    assert stats["hors_delai_tickets"] == []
    assert Path(output_file).exists()
