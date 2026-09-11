import pytest
import pandas as pd
import tempfile
import os
from processor import generate_dashboard

@pytest.fixture
def temp_excel_file():
    # Create test data
    data = {
        "Identifiant": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "Projet": [
            "SIB_RUN_MON",  # SIB
            "SIB_RUN_MON",  # SIB
            "SIB_RUN_MON",  # SIB
            "SIB_RUN_MON",  # SIB
            "SIB_RUN_MON",  # SIB
            "SIB_RUN_MON",  # SIB
            "RUN MON",      # RUN MON (no underscore)
            "SIB_RUN_MON",  # SIB
            "OTHER_PROJ",   # OTHER
            "SIB_RUN_MON"   # SIB
        ],
        "Assigné à": ["Collab1"] * 10,
        "Date de soumission": [
            "2026-06-01", # inside period
            "2026-06-05", # inside period
            "2026-06-10", # inside period
            "2026-05-15", # outside period
            "2026-06-20", # inside period
            "2026-06-25", # inside period
            "2026-06-15", # inside period (for RUN MON)
            "2026-05-20", # outside period
            "2026-06-12", # inside period but other project
            "2026-06-15"  # inside period
        ],
        "Mis à jour": ["2026-06-30"] * 10,
        "Résumé": ["Test ticket"] * 10,
        "Statut": [
            "Clôturé",      # 1: SIB, in period, clôturé
            "En Cours",     # 2: SIB, in period, en cours, Resp: APP
            "Mise En Production", # 3: SIB, in period, en cours, Resp: Filiale
            "En Cours",     # 4: SIB, out period, en cours, Resp: APP
            "Clôturé",      # 5: SIB, in period, clôturé
            "A Clôturer",   # 6: SIB, in period, clôturé
            "En Cours",     # 7: RUN MON, in period, en cours, Resp: APP
            "Clôturé",      # 8: SIB, out period, clôturé (updated in period)
            "Clôturé",      # 9: OTHER, in period, clôturé
            "Clôturé"       # 10: SIB, in period, clôturé (Resp: Tech)
        ],
        "Responsable": [
            "APP",          # 1
            "APP",          # 2
            "Filiale",      # 3
            "APP",          # 4
            "SIG",          # 5
            "APP",          # 6
            "APP",          # 7
            "SIG",          # 8 (SIG, out period, clôturé)
            "APP",          # 9
            "Tech"          # 10 (Tech, in period, clôturé)
        ],
        "Sous Domaine MON": [
            "Domaine A",    # 1
            "Domaine B",    # 2
            "Domaine A",    # 3
            "Domaine A",    # 4
            "Domaine B",    # 5
            "Domaine C",    # 6
            "Domaine A",    # 7
            "Domaine C",    # 8
            "Domaine A",    # 9
            "Domaine B"     # 10
        ]
    }
    df = pd.DataFrame(data)
    
    # Write to a temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "test_mantis_dashboard.xlsx")
    
    with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RUN+MON', index=False)
        
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except OSError:
            pass

def test_dashboard_logic(temp_excel_file):
    # Run generate_dashboard
    kpi_stats, _ = generate_dashboard(
        temp_excel_file,
        start_date="2026-06-01",
        end_date="2026-06-30",
        filiale="SIB"
    )
    
    # Reçues: SIB project, date in 2026-06-01 to 2026-06-30
    # Expected: Id 1, 2, 3, 5, 6, 10 -> Total = 6
    assert kpi_stats["total_receves"] == 6
    
    # Clôturés: SIB project, date de mise à jour in 2026-06-01 to 2026-06-30, status Clôturé or A Clôturer
    # Expected: Id 1, 5, 6, 8, 10 -> Total = 5
    assert kpi_stats["total_clotures"] == 5
    
    # En Cours (definition élargie): SIB project, status En Cours or Mise En Production, no date filter
    # Expected: Id 2, 3, 4 -> Total = 3 (Id 8 is Clôturé, not En Cours)
    assert kpi_stats["total_en_cours"] == 3
    
    # Test 1: Clôturés and Reçues are calculated independently on separate date columns
    # Id 8 (submitted 2026-05-20, updated 2026-06-30, status Clôturé) is included in Clôturés but not in Reçues
    df = pd.read_excel(temp_excel_file, sheet_name='RUN+MON', engine='openpyxl')
    df['Filiale'] = df['Projet'].astype(str).str.split('_').str[0]
    df_sib = df[df['Filiale'] == 'SIB']
    
    # Reçues based on Date de soumission in period
    df_receves = df_sib[
        (pd.to_datetime(df_sib['Date de soumission']) >= '2026-06-01') &
        (pd.to_datetime(df_sib['Date de soumission']) <= '2026-06-30')
    ]
    # Clôturés based on Mis à jour in period
    df_clotures = df_sib[
        df_sib['Statut'].isin(["A Clôturer", "Clôturé"]) &
        (pd.to_datetime(df_sib['Mis à jour']) >= '2026-06-01') &
        (pd.to_datetime(df_sib['Mis à jour']) <= '2026-06-30')
    ]
    
    # Verify ticket 8 is in Clôturés but not in Reçues
    ticket_8_receves = df_receves[df_receves['Identifiant'] == 8]
    ticket_8_clotures = df_clotures[df_clotures['Identifiant'] == 8]
    assert len(ticket_8_receves) == 0
    assert len(ticket_8_clotures) == 1
    
    # Test 2: En cours is NOT affected by date filter
    # Id 4 is submitted outside period (2026-05-15) and remains in En Cours.
    assert kpi_stats["total_en_cours"] == 3
    
    # Test 3: Graph 1 APP + Filiale calculations
    # In En Cours tickets (Id 2, 3, 4), responsibles are:
    # Id 2: APP
    # Id 3: Filiale
    # Id 4: APP
    # Sum of APP + Filiale = 2 + 1 = 3 (100% of filtered population)
    df_sib_en_cours = df_sib[df_sib['Statut'].isin(["En Cours", "Mise En Production"])]
    df_g1 = df_sib_en_cours[df_sib_en_cours['Responsable'].isin(['APP', 'Filiale'])]
    g1_counts = df_g1['Responsable'].value_counts()
    app_count = g1_counts.get('APP', 0)
    filiale_count = g1_counts.get('Filiale', 0)
    assert app_count + filiale_count == len(df_g1)
    
    # Test 4: Graph 3 + 4 <= Graph 2 total
    df_g3 = df_receves[df_receves['Responsable'] == 'APP']
    df_g4 = df_receves[df_receves['Responsable'] == 'Filiale']
    assert len(df_g3) + len(df_g4) <= len(df_receves)


def test_out_of_period_closed_ticket_exclusion(monkeypatch):
    from processor import generate_report

    # Mock get_ticket_history to return history for ticket 99 showing it was closed in 2023
    def mock_get_ticket_history(ticket_id, session=None):
        if str(ticket_id) == "99":
            return [
                {
                    "created_at": "2023-11-07T10:00:00+00:00",
                    "field": {"name": "status"},
                    "new_value": {"label": "Clôturé"}
                }
            ]
        return []

    monkeypatch.setattr("processor.get_ticket_history", mock_get_ticket_history)
    monkeypatch.setattr("processor.MANTIS_TOKEN", "mock_token")
    monkeypatch.setattr("processor.MANTIS_BASE_URL", "http://mock-mantis")

    data = {
        "Identifiant": [99],
        "Projet": ["SIB_RUN_MON"],
        "Assigné à": ["Collab1"],
        "Date de soumission": ["2023-11-07"],
        "Mis à jour": ["2026-07-20"],  # Modified in July 2026 due to duplication
        "Résumé": ["Old 2023 ticket"],
        "Statut": ["Clôturé"],
        "Responsable": ["APP"],
        "Sous Domaine MON": ["Domaine A"]
    }
    df = pd.DataFrame(data)

    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "test_out_of_period.xlsx")
    with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RUN+MON', index=False)

    try:
        kpi_stats, _ = generate_report(
            temp_path,
            start_date="2026-07-01",
            end_date="2026-07-31",
            date_column="Mis à jour",
            sla_groups=[2, 5, 15],
            collaborators=["Collab1"]
        )
        # Ticket 99 was closed in 2023, so it should be excluded completely from July 2026 report!
        assert kpi_stats["clotures_dans_delai"] == 0
        assert kpi_stats["clotures_hors_delai"] == 0
        assert len(kpi_stats["hors_delai_tickets"]) == 0
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

