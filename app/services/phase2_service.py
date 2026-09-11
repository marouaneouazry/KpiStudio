from typing import Optional, Dict, Any, List

import pandas as pd

from app.infrastructure.mantis.client import MantisClient
from app.domain.tickets.timeline import (
    _to_naive_ts,
    compute_effective_close_and_pauses,
    total_pause_business_days,
)
from app.domain.kpi.business_days import calculate_business_days


class Phase2Service:
    """
    Service responsable de la correction Phase 2.

    IMPORTANT :
    Ce service est appelé uniquement pour les tickets déjà identifiés
    comme hors délai par le calcul initial Excel.

    Il ne modifie pas la formule de calcul métier du délai.
    Il applique uniquement les corrections issues de la timeline Mantis.
    """

    def __init__(
        self,
        mantis_client: Optional[MantisClient] = None,
    ):
        self.client = (
            mantis_client
            if mantis_client is not None
            else MantisClient()
        )

    def process_correction(
    self,
    ticket_id: Any,
    current_assignee: Optional[str],
    submission_date: Any,
    holidays: Any,
    today_ref: Any,
    collaborators: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:

        # ==================================================================
        # 1. HISTORIQUE MANTIS
        # ==================================================================

        history = self.client.fetch_ticket_history(
            ticket_id
        )

        if not history:
            return None

        # ==================================================================
        # 2. NORMALISATION DES DATES
        # ==================================================================

        sub_dt = _to_naive_ts(
            submission_date
        )

        ref_dt = _to_naive_ts(
            today_ref
        )

        if pd.isna(sub_dt) or pd.isna(ref_dt):
            return None

        # ==================================================================
        # 3. RECONSTRUCTION DE LA TIMELINE
        # ==================================================================

        timeline = compute_effective_close_and_pauses(
            history=history,
            current_assignee=current_assignee,
            submission_date=sub_dt,
            reference_date=ref_dt,
            collaborators=collaborators,
        )

        # ==================================================================
        # 4. CALCUL DES PAUSES
        # ==================================================================

        pause_days = total_pause_business_days(
            timeline["pause_intervals"],
            holidays=holidays,
        )

        # ==================================================================
        # 5. DATE DE FIN DU CALCUL PHASE 2
        # ==================================================================

        if timeline["is_closed"]:
            effective_date = timeline[
                "effective_close_date"
            ]
        else:
            effective_date = ref_dt

        if effective_date is None:
            effective_date = ref_dt

        effective_date = _to_naive_ts(
            effective_date
        )

        if pd.isna(effective_date):
            return None

        # ==================================================================
        # 6. CALCUL BRUT PHASE 2
        # ==================================================================

        raw_delai = calculate_business_days(
            sub_dt.date(),
            effective_date.date(),
            holidays=holidays,
        )

        if raw_delai is None:
            raw_delai = 0.0

        # ==================================================================
        # 7. RETRAIT DES PAUSES MÉTIER
        # ==================================================================

        corrected_delai = max(
            0.0,
            raw_delai - pause_days,
        )

        # ==================================================================
        # 8. RESULTAT
        # ==================================================================

        return {
            "corrected_delai": corrected_delai,
            "effective_close_date": timeline[
                "effective_close_date"
            ],
            "is_closed": timeline[
                "is_closed"
            ],
            "display_update_date": timeline.get(
                "display_update_date"
            ),
        }


_default_service = Phase2Service()


def apply_phase2_correction(
    ticket_id: Any,
    current_assignee: Optional[str],
    submission_date: Any,
    holidays: Any,
    today_ref: Any,
    collaborators: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Wrapper global de compatibilité.
    """
    return _default_service.process_correction(
    ticket_id=ticket_id,
    current_assignee=current_assignee,
    submission_date=submission_date,
    holidays=holidays,
    today_ref=today_ref,
    collaborators=collaborators,
)