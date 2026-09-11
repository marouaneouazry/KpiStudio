import pytest
import pandas as pd
from pathlib import Path
from app.services.dashboard_service import DashboardService

def test_dashboard_service_generate_dashboard_end_to_end(tmp_path):
    df_data = pd.DataFrame({
        "Identifiant": [2001, 2002],
        "Projet": ["CDM_RUN", "CDM_MON"],
        "Assigné à": ["User A", "User B"],
        "Date de soumission": ["2026-01-05", "2026-01-10"],
        "Mis à jour": ["2026-01-08", "2026-01-12"],
        "Résumé": ["Summary 1", "Summary 2"],
        "Statut": ["Clôturé", "En Cours"],
        "Responsable": ["APP", "Filiale"],
        "Sous Domaine MON": ["Demande d'assistance / conseil", "Demande ticket TPE"]
    })

    file_path = tmp_path / "mantis_dashboard_test.xlsx"
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df_data.to_excel(writer, sheet_name='RUN+MON', index=False)

    service = DashboardService()
    stats, output_file = service.generate_dashboard(
        file_path=file_path,
        start_date="2026-01-01",
        end_date="2026-01-31",
        filiale="CDM"
    )

    assert isinstance(stats, dict)
    assert "total_receves" in stats
    assert "dysfonctionnement" in stats
    assert "financieres" in stats
    assert Path(output_file).exists()
