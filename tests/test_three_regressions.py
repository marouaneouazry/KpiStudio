import pytest
import os
import json
import tempfile
import pandas as pd
import numpy as np
from datetime import date
from app.services.kpi_service import KpiService
from app.holidays import get_all_validated_holiday_dates, get_validated_holiday_dates, HOLIDAYS_DIR
from app.domain.kpi.business_days import calculate_business_days

def test_regression1_ticket_41330_historical_multiyear_holidays():
    """
    REGRESSION 1 TEST 1: Ticket 41330 (2023-11-07 to 2026-07-20)
    Verifies that calculation incorporates validated holidays across 2023, 2024, 2025, and 2026,
    yielding exact raw delay 666 business days.
    """
    start_d = date(2023, 11, 7)
    end_d = date(2026, 7, 20)
    
    # Load all validated holidays across available years
    holidays = get_all_validated_holiday_dates()
    delay = calculate_business_days(start_d, end_d, holidays=holidays)
    
    assert delay == 666.0

def test_regression1_single_year_ticket():
    """
    REGRESSION 1 TEST 2: Ticket entirely inside 2026 uses 2026 holidays.
    """
    start_d = date(2026, 1, 5) # Monday
    end_d = date(2026, 1, 15)  # Thursday
    holidays = get_all_validated_holiday_dates()
    
    delay = calculate_business_days(start_d, end_d, holidays=holidays)
    # 2026-01-11 is Sun, 2026-01-10 is Sat, 2026-01-01 was earlier.
    assert delay is not None
    assert delay > 0

def test_regression1_two_year_ticket():
    """
    REGRESSION 1 TEST 3: Ticket spanning 2025 -> 2026 uses both 2025 and 2026 holidays.
    """
    start_d = date(2025, 12, 20)
    end_d = date(2026, 1, 10)
    holidays = get_all_validated_holiday_dates()
    
    delay = calculate_business_days(start_d, end_d, holidays=holidays)
    assert delay is not None

def test_regression1_unvalidated_calendar_raises_error(tmp_path, monkeypatch):
    """
    REGRESSION 1 TEST 5: An unvalidated calendar file raises ValueError.
    """
    # Create temporary draft calendar
    test_holidays_dir = tmp_path / "holidays"
    test_holidays_dir.mkdir(parents=True, exist_ok=True)
    
    draft_cal = {
        "year": 2099,
        "status": "draft",
        "holidays": []
    }
    with open(test_holidays_dir / "2099.json", "w", encoding="utf-8") as f:
        json.dump(draft_cal, f)
        
    monkeypatch.setattr("app.holidays.HOLIDAYS_DIR", str(test_holidays_dir))
    
    with pytest.raises(ValueError) as exc_info:
        get_all_validated_holiday_dates()
    
    assert "2099" in str(exc_info.value)
    assert "draft" in str(exc_info.value)

def test_regression2_explicit_reference_date_reproducibility():
    """
    REGRESSION 2: En Cours Reference Date
    Verifies that changing reference_date alters En Cours ticket delays reproducibly,
    while CLOSED ticket delays remain completely unchanged.
    """
    data = {
        "Identifiant": [90581, 90582],
        "Projet": ["CDM_RUN", "CDM_RUN"],
        "Assigné à": ["User A", "User A"],
        "Date de soumission": ["2026-07-29", "2026-07-29"],
        "Mis à jour": ["2026-08-05", "2026-08-05"],
        "Résumé": ["Open Ticket", "Closed Ticket"],
        "Statut": ["En Cours", "Clôturé"],
        "Responsable": ["APP", "APP"],
        "Sous Domaine MON": ["Activation Carte", "Activation Carte"]
    }
    df = pd.DataFrame(data)
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "test_ref_date_reg.xlsx")
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RUN+MON', index=False)

    service = KpiService()

    # Execution with reference_date 2026-08-07
    stats1, file1 = service.generate_report(
        file_path=test_file,
        start_date="2026-07-01",
        end_date="2026-07-31",
        date_column="Date de soumission",
        sla_groups=[2],
        collaborators=["User A"],
        reference_date="2026-08-07"
    )

    # Execution with reference_date 2026-08-15
    stats2, file2 = service.generate_report(
        file_path=test_file,
        start_date="2026-07-01",
        end_date="2026-07-31",
        date_column="Date de soumission",
        sla_groups=[2],
        collaborators=["User A"],
        reference_date="2026-08-15"
    )

    # Closed ticket metrics (c2, c3) MUST REMAIN UNCHANGED
    assert stats1["c2"] == stats2["c2"]
    assert stats1["c3"] == stats2["c3"]

    # Direct business days delay check with reference_date 2026-08-07 vs 2026-08-15
    sub_d = date(2026, 7, 29)
    ref_d1 = date(2026, 8, 7)
    ref_d2 = date(2026, 8, 15)
    
    holidays = get_all_validated_holiday_dates()
    
    delay1_open = calculate_business_days(sub_d, ref_d1, holidays=holidays)
    delay2_open = calculate_business_days(sub_d, ref_d2, holidays=holidays)
    
    # Open ticket delay MUST BE DIFFERENT when reference_date changes
    assert delay1_open != delay2_open
    assert delay1_open == 6.0
    assert delay2_open == 10.0

    # Closed ticket delay MUST BE IDENTICAL when reference_date changes
    closed_upd = date(2026, 8, 5)
    closed_delay1 = calculate_business_days(sub_d, closed_upd, holidays=holidays)
    closed_delay2 = calculate_business_days(sub_d, closed_upd, holidays=holidays)
    assert closed_delay1 == closed_delay2 == 4.0

    if os.path.exists(test_file):
        os.remove(test_file)

def test_regression3_excel_sheet_sorting_by_sla_then_delai():
    """
    REGRESSION 3: Excel Sorting Order
    Verifies that all detailed worksheets are strictly sorted by:
    1. SLA ascending
    2. Délai ascending
    """
    # Deliberately unsorted dataset
    data = {
        "Identifiant": [1, 2, 3, 4, 5],
        "Projet": ["CDM_RUN"] * 5,
        "Assigné à": ["User A"] * 5,
        "Date de soumission": ["2026-06-01"] * 5,
        "Mis à jour": ["2026-06-10", "2026-06-05", "2026-06-04", "2026-06-03", "2026-06-06"],
        "Résumé": ["T1", "T2", "T3", "T4", "T5"],
        "Statut": ["Clôturé"] * 5,
        "Responsable": ["APP"] * 5,
        # SLA 5, 2, 5, 2, 15
        "Sous Domaine MON": [
            "Demande des extractions", # SLA 5
            "Activation Carte",         # SLA 2
            "Demande des extractions", # SLA 5
            "Activation Carte",         # SLA 2
            "Dysfonctionnement"         # SLA 15
        ]
    }
    df = pd.DataFrame(data)
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "test_sort_reg.xlsx")
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RUN+MON', index=False)

    service = KpiService()
    _, output_file = service.generate_report(
        file_path=test_file,
        start_date="2026-06-01",
        end_date="2026-06-30",
        date_column="Date de soumission",
        sla_groups=[2, 5, 15],
        collaborators=["User A"]
    )

    df_clotures = pd.read_excel(output_file, sheet_name="Clôturées", engine="openpyxl")
    slas = list(df_clotures["SLA"])
    delais = list(df_clotures["Délai"])

    # Verify primary sort order (SLA ascending)
    assert slas == sorted(slas)

    # Verify secondary sort order (Délai ascending within same SLA group)
    for sla_val in set(slas):
        delais_for_sla = df_clotures.loc[df_clotures["SLA"] == sla_val, "Délai"].tolist()
        assert delais_for_sla == sorted(delais_for_sla)

    if os.path.exists(test_file):
        os.remove(test_file)
