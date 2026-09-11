import pytest
from datetime import date
from app.domain.kpi.calculator import calculate_raw_ticket_delay, compute_kpi_metrics
from app.domain.kpi.models import KpiStats

def test_calculate_raw_ticket_delay():
    start = date(2026, 1, 7) # Wed
    end = date(2026, 1, 8)   # Thu
    res = calculate_raw_ticket_delay(start, end)
    assert res == 1.0

def test_compute_kpi_metrics_zero_tickets():
    stats = compute_kpi_metrics(0, 0, 0, 0, 0, 0, 0)
    assert isinstance(stats, KpiStats)
    assert stats.taux_sla_ap == "0.0%"
    assert stats.total_receves == 0

def test_compute_kpi_metrics_success_rate():
    # c2 (clôturés dans délai) = 4, c3 (total clôturés) = 5, c4 (en cours hors délai) = 1
    # Golden Master Taux SLA AP = c2 / (c3 + c4) = 4 / 6 = 66.66...% => "66.7%"
    stats = compute_kpi_metrics(
        total_receves=10,
        total_clotures=5,
        total_en_cours=5,
        clotures_dans_delai=4,
        clotures_hors_delai=1,
        encours_dans_delai=4,
        encours_hors_delai=1
    )
    assert stats.taux_sla_ap == "66.7%"
    assert stats.total_receves == 10
    assert stats.to_dict()["taux_sla_ap"] == "66.7%"
