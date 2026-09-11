import pytest
import pandas as pd
import tempfile
from pathlib import Path
from app.infrastructure.excel.reader import read_mantis_export, sanitize_excel_value

def test_sanitize_excel_value():
    assert sanitize_excel_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_excel_value("+12345") == "'+12345"
    assert sanitize_excel_value("-12345") == "'-12345"
    assert sanitize_excel_value("@cmd") == "'@cmd"
    assert sanitize_excel_value("Normal Text") == "Normal Text"
    assert sanitize_excel_value(None) is None

def test_read_mantis_export_valid(tmp_path):
    df_data = pd.DataFrame({
        "Identifiant": [101, 102],
        "Projet": ["PROJ_1", "PROJ_2"],
        "Assigné à": ["User A", "User B"],
        "Date de soumission": ["2026-01-01", "2026-01-02"],
        "Mis à jour": ["2026-01-05", "2026-01-06"],
        "Résumé": ["@Danger", "Normal summary"],
        "Statut": ["Clôturé", "En cours"],
        "Responsable": ["AP", "Filiale"],
        "Sous Domaine MON": [" INCIDENT ", " SUPPORT "]
    })
    
    file_path = tmp_path / "test_mantis.xlsx"
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df_data.to_excel(writer, sheet_name='RUN+MON', index=False)

    res_df = read_mantis_export(file_path, sheet_name='RUN+MON')
    assert len(res_df) == 2
    assert list(res_df.columns) == [
        "Identifiant", "Projet", "Assigné à", "Date de soumission",
        "Mis à jour", "Résumé", "Statut", "Responsable", "Sous Domaine MON"
    ]
    # Check text whitespace trimming
    assert res_df.iloc[0]["Sous Domaine MON"] == "INCIDENT"
    # Check formula sanitization
    assert res_df.iloc[0]["Résumé"] == "'@Danger"

def test_read_mantis_export_missing_sheet(tmp_path):
    file_path = tmp_path / "empty.xlsx"
    pd.DataFrame({"A": [1]}).to_excel(file_path, sheet_name="OtherSheet", index=False)
    with pytest.raises(ValueError, match=r"RUN\+MON"):
        read_mantis_export(file_path, sheet_name='RUN+MON')

def test_read_mantis_export_missing_column(tmp_path):
    file_path = tmp_path / "missing_col.xlsx"
    df = pd.DataFrame({
        "Identifiant": [101],
        "Projet": ["P1"]
        # Missing other required columns
    })
    df.to_excel(file_path, sheet_name='RUN+MON', index=False)
    with pytest.raises(ValueError, match="Colonnes manquantes"):
        read_mantis_export(file_path, sheet_name='RUN+MON')
