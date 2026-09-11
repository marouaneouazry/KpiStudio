from typing import Optional, Sequence
from app.domain.kpi.business_days import calculate_business_days, DateLike
from app.domain.kpi.models import KpiStats

def calculate_raw_ticket_delay(
    start_date: Optional[DateLike],
    end_date: Optional[DateLike],
    holidays: Optional[Sequence[DateLike]] = None
) -> Optional[float]:
    """
    Delegates raw ticket delay calculation to the pure business-day calculation engine.
    """
    return calculate_business_days(start_date, end_date, holidays)

def compute_kpi_metrics(
    total_receves: int,
    total_clotures: int,
    total_en_cours: int,
    clotures_dans_delai: int,
    clotures_hors_delai: int,
    encours_dans_delai: int,
    encours_hors_delai: int
) -> KpiStats:
    """
    Aggregates ticket count metrics and computes SLA compliance percentage string.
    Golden Master Formula: c2 / (c3 + c4)
    Where:
      c2 = clotures_dans_delai
      c3 = total_clotures (clotures_dans_delai + clotures_hors_delai)
      c4 = encours_hors_delai
    """
    c2 = clotures_dans_delai
    c3 = clotures_dans_delai + clotures_hors_delai
    c4 = encours_hors_delai
    denom = c3 + c4
    if denom > 0:
        pct = (c2 / denom) * 100.0
        taux_str = f"{pct:.1f}%"
    else:
        taux_str = "0.0%"

    return KpiStats(
        total_receves=total_receves,
        total_clotures=total_clotures,
        total_en_cours=total_en_cours,
        clotures_dans_delai=clotures_dans_delai,
        clotures_hors_delai=clotures_hors_delai,
        encours_dans_delai=encours_dans_delai,
        encours_hors_delai=encours_hors_delai,
        taux_sla_ap=taux_str,
    )
