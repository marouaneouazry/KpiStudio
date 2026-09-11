import pytest
import pandas as pd
import openpyxl
from app.infrastructure.excel.writer import write_kpi_report

def test_write_kpi_report_creates_all_sheets(tmp_path):
    output_path = tmp_path / "ApresCalcul.xlsx"

    cols = [
        "Identifiant", "Projet", "Assigné à", "Date de soumission",
        "Mis à jour", "Date de clôture", "Résumé", "Statut",
        "Responsable", "Sous Domaine MON", "Délai", "SLA"
    ]
    df_sample = pd.DataFrame([{
        "Identifiant": 1001, "Projet": "PROJ", "Assigné à": "User A",
        "Date de soumission": "2026-01-01", "Mis à jour": "2026-01-05*",
        "Date de clôture": "2026-01-05", "Résumé": "Test summary",
        "Statut": "Clôturé", "Responsable": "AP",
        "Sous Domaine MON": "INCIDENT", "Délai": 3.0, "SLA": 5
    }], columns=cols)

    sheets_data = [
        ("Clôturées", df_sample, [False], [5]),
        ("Clôturées hors délai", pd.DataFrame(), [], []),
        ("En cours", pd.DataFrame(), [], []),
        ("En cours hors délai", pd.DataFrame(), [], []),
    ]

    synth_data = [
        ["Indicateur", "Valeur"],
        ["Demandes traitées du 2026-01-01 au 2026-01-31 dans les délais", 1],
        ["Demandes traitées du 2026-01-01 au 2026-01-31", 1],
        ["Demandes en cours hors SLA au 31-01-2026", 0],
        ["Taux de respect SLA", 1.0],
    ]

    saved_file = write_kpi_report(sheets_data, synth_data, output_path)
    assert saved_file == str(output_path)
    assert output_path.exists()

    wb = openpyxl.load_workbook(output_path)
    sheet_names = wb.sheetnames
    assert "Clôturées" in sheet_names
    assert "Clôturées hors délai" in sheet_names
    assert "En cours" in sheet_names
    assert "En cours hors délai" in sheet_names
    assert "SLA" in sheet_names

    ws_sla = wb["SLA"]
    assert ws_sla.cell(row=ws_sla.max_row, column=1).value == "Taux de respect SLA"
    assert ws_sla.cell(row=ws_sla.max_row, column=2).number_format == "0.00%"
