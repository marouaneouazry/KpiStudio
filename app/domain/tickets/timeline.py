import pandas as pd
import numpy as np
from typing import Optional, List, Tuple, Dict, Any


CLOSED_LABELS = {"A Clôturer", "Clôturé"}
TEAM_QUEUE_BUCKETS = {"AP", "APP"}


def _to_naive_ts(value: Any) -> pd.Timestamp:
    """
    Convertit une valeur de date/heure en Timestamp tz-naive.
    """
    if value is None:
        return pd.NaT

    if isinstance(value, float) and pd.isna(value):
        return pd.NaT

    ts = pd.to_datetime(value)

    if ts is pd.NaT:
        return pd.NaT

    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)

    return ts


def _merge_intervals(
    intervals: List[Tuple[Any, Any]]
) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Fusionne les intervalles qui se chevauchent ou se touchent.
    """
    if not intervals:
        return []

    parsed = []

    for start, end in intervals:
        start_ts = _to_naive_ts(start)
        end_ts = _to_naive_ts(end)

        if pd.isna(start_ts) or pd.isna(end_ts):
            continue

        if end_ts <= start_ts:
            continue

        parsed.append((start_ts, end_ts))

    if not parsed:
        return []

    parsed.sort(key=lambda item: item[0])

    merged = [parsed[0]]

    for start, end in parsed[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:
            merged[-1] = (
                last_start,
                max(last_end, end),
            )
        else:
            merged.append((start, end))

    return merged


def _clip_intervals(
    intervals: List[Tuple[Any, Any]],
    window_start: Any,
    window_end: Any,
) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Borne les intervalles à [window_start, window_end].
    """
    if window_start is None or window_end is None:
        return intervals

    ws = _to_naive_ts(window_start)
    we = _to_naive_ts(window_end)

    if pd.isna(ws) or pd.isna(we):
        return []

    clipped = []

    for start, end in intervals:
        start_ts = _to_naive_ts(start)
        end_ts = _to_naive_ts(end)

        if pd.isna(start_ts) or pd.isna(end_ts):
            continue

        clipped_start = max(start_ts, ws)
        clipped_end = min(end_ts, we)

        if clipped_end > clipped_start:
            clipped.append(
                (clipped_start, clipped_end)
            )

    return clipped


def _field_name(event: Dict[str, Any]) -> str:
    """
    Retourne le nom du champ modifié dans un événement Mantis.
    """
    field = event.get("field", {})

    if isinstance(field, dict):
        return str(field.get("name", ""))

    return str(field)


def _extract_value(value: Any) -> Any:
    """
    Extrait label/name lorsque Mantis retourne un objet.
    """
    if isinstance(value, dict):
        if value.get("label") is not None:
            return value.get("label")

        if value.get("name") is not None:
            return value.get("name")

    return value


def compute_effective_close_and_pauses(
    history: List[Dict[str, Any]],
    current_assignee: Optional[str],
    submission_date: Any,
    reference_date: Optional[Any] = None,
    collaborators: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Reconstruit la timeline métier du ticket.

    Règles métier :

    1. Statut "Complément d'information" => pause.
    2. Responsable hors AP/APP => pause.
    3. Handler / Assigné à :
       - si le handler est présent dans collaborators.json => PAS de pause ;
       - sinon => pause.
    4. Délai administratif entre "A Clôturer" et "Clôturé"
       => pause.

    IMPORTANT :
    La nouvelle règle concerne uniquement le champ "handler".
    Les règles liées au statut et au Responsable restent indépendantes.
    """

    sorted_history = sorted(
        history,
        key=lambda event: event.get("created_at", "")
    )

    submission_date = _to_naive_ts(
        submission_date
    )

    reference_date = (
        _to_naive_ts(reference_date)
        if reference_date is not None
        else None
    )

    # ======================================================================
    # COLLABORATEURS CONFIGURÉS
    # ======================================================================

    configured_collaborators = {
        str(name).strip()
        for name in (collaborators or [])
        if name is not None
        and str(name).strip()
    }

    # ======================================================================
    # CAS 3 :
    # A CLÔTURER -> CLÔTURÉ = PAUSE ADMINISTRATIVE
    # ======================================================================

    tentative_completion = None
    admin_delay_window = None
    is_closed = False
    final_close_event_time = None

    for event in sorted_history:
        if _field_name(event) != "status":
            continue

        new_label = _extract_value(
            event.get("new_value")
        )

        ts = _to_naive_ts(
            event.get("created_at")
        )

        if pd.isna(ts):
            continue

        if new_label == "A Clôturer":
            tentative_completion = ts

        elif new_label == "Clôturé":
            is_closed = True
            final_close_event_time = ts

            if tentative_completion is not None:
                admin_delay_window = (
                    tentative_completion,
                    ts,
                )

        elif new_label not in CLOSED_LABELS:
            # Réouverture :
            # la tentative de clôture précédente n'est plus valide.
            tentative_completion = None

    # ======================================================================
    # DERNIER STATUT
    # ======================================================================

    last_status_event = None

    for event in sorted_history:
        if _field_name(event) == "status":
            last_status_event = event

    if last_status_event is not None:
        current_status_label = _extract_value(
            last_status_event.get("new_value")
        )
    else:
        current_status_label = None

    # ======================================================================
    # DATE DE CLÔTURE EFFECTIVE
    # ======================================================================

    if (
        current_status_label == "A Clôturer"
        and not is_closed
    ):
        effective_close_date = tentative_completion

    elif is_closed:
        effective_close_date = (
            tentative_completion
            if tentative_completion is not None
            else final_close_event_time
        )

    else:
        effective_close_date = None

    # ======================================================================
    # CAS 1 & CAS 2 :
    # PAUSES MÉTIER
    # ======================================================================

    current_handler = None
    current_status_for_pause = None
    current_responsable = None

    raw_pause_intervals = []

    is_paused = False
    pause_start = None

    # Dernier événement métier utile
    last_business_event_time = None

    # ======================================================================
    # FONCTION DE DÉTERMINATION DE L'ÉTAT DE PAUSE
    # ======================================================================

    def paused_now(
        handler: Optional[str],
        status_label: Optional[str],
        responsable: Optional[str],
    ) -> bool:
        """
        Retourne True si le ticket doit être considéré en pause.

        Règle HANDLER :
            - handler dans collaborators.json => pas de pause
            - handler hors collaborators.json => pause

        Règle STATUT :
            - "Complément d'information" => pause

        Règle RESPONSABLE :
            - Responsable AP ou APP => pas de pause
            - autre Responsable => pause

        Les trois règles sont indépendantes.
        """

        # --------------------------------------------------------------
        # RÈGLE HANDLER / ASSIGNÉ À
        # --------------------------------------------------------------

        if configured_collaborators:
            handler_ok = (
            handler is None
            or str(handler).strip()
            in configured_collaborators
        )
        else:
            handler_ok = (
            handler is None
            or handler == current_assignee
            or handler in TEAM_QUEUE_BUCKETS
        )

    # Un handler hors collaborateurs => PAUSE
        if not handler_ok:
            return True
    

        # --------------------------------------------------------------
        # RÈGLE STATUT
        # --------------------------------------------------------------
        if status_label == "Complément d'information":
            return True

    # A Qualifier => PAUSE
        if status_label == "A Qualifier":
            return True

    # En Cours => PAS DE PAUSE
    # même si Responsable = Filiale
        if status_label == "En Cours":
            return False
        # --------------------------------------------------------------
        # RÈGLE RESPONSABLE
        # --------------------------------------------------------------

        responsable_ok = (
            responsable is None
            or responsable in TEAM_QUEUE_BUCKETS
    )

        return not responsable_ok

        # --------------------------------------------------------------
        # PAUSE SI AU MOINS UNE RÈGLE EST EN PAUSE
        # --------------------------------------------------------------

        return not (
            handler_ok
            and status_ok
            and responsable_ok
        )

    # ======================================================================
    # PARCOURS DE L'HISTORIQUE
    # ======================================================================

    for event in sorted_history:
        fname = _field_name(event)

        if fname not in {
            "handler",
            "status",
            "Responsable",
        }:
            continue

        ts = _to_naive_ts(
            event.get("created_at")
        )

        if pd.isna(ts):
            continue

        last_business_event_time = ts

        # --------------------------------------------------------------
        # HANDLER
        # --------------------------------------------------------------

        if fname == "handler":
            current_handler = _extract_value(
                event.get("new_value")
            )

        # --------------------------------------------------------------
        # STATUS
        # --------------------------------------------------------------

        elif fname == "status":
            current_status_for_pause = _extract_value(
                event.get("new_value")
            )

        # --------------------------------------------------------------
        # RESPONSABLE
        # --------------------------------------------------------------

        elif fname == "Responsable":
            current_responsable = _extract_value(
                event.get("new_value")
            )

        # --------------------------------------------------------------
        # NOUVEL ÉTAT DE PAUSE
        # --------------------------------------------------------------

        new_state = paused_now(
            current_handler,
            current_status_for_pause,
            current_responsable,
        )

        # Passage NORMAL -> PAUSE
        if new_state and not is_paused:
            pause_start = ts
            is_paused = True

        # Passage PAUSE -> NORMAL
        elif not new_state and is_paused:
            if pause_start is not None:
                raw_pause_intervals.append(
                    (pause_start, ts)
                )

            pause_start = None
            is_paused = False

    # ======================================================================
    # PAUSE ENCORE ACTIVE
    # ======================================================================

    if is_paused and pause_start is not None:

        end_ts = (
            effective_close_date
            if effective_close_date is not None
            else reference_date
        )

        if end_ts is not None:
            raw_pause_intervals.append(
                (pause_start, end_ts)
            )

    # ======================================================================
    # PAUSE ADMINISTRATIVE
    # ======================================================================

    if admin_delay_window is not None:
        raw_pause_intervals.append(
            admin_delay_window
        )

    # ======================================================================
    # CLIPPING + FUSION
    # ======================================================================

    window_end = (
        effective_close_date
        if effective_close_date is not None
        else reference_date
    )

    clipped = _clip_intervals(
        raw_pause_intervals,
        submission_date,
        window_end,
    )

    merged = _merge_intervals(
        clipped
    )

    # ======================================================================
    # DATE MÉTIER POUR "EN COURS"
    # ======================================================================

    if (
        is_closed
        or current_status_label == "A Clôturer"
    ):
        display_update_date = None
    else:
        display_update_date = (
            last_business_event_time
        )

    # ======================================================================
    # RESULTAT
    # ======================================================================

    return {
        "effective_close_date": effective_close_date,
        "is_closed": (
            is_closed
            or current_status_label == "A Clôturer"
        ),
        "pause_intervals": merged,
        "display_update_date": display_update_date,
    }


def total_pause_business_days(
    pause_intervals: List[Tuple[Any, Any]],
    holidays: Optional[Any] = None,
) -> int:
    """
    Calcule les jours ouvrés correspondant aux pauses.
    """

    holidays = holidays or []

    total = 0

    for start, end in pause_intervals:
        start_ts = _to_naive_ts(start)
        end_ts = _to_naive_ts(end)

        if pd.isna(start_ts) or pd.isna(end_ts):
            continue

        start_date = np.datetime64(
            start_ts.date()
        )

        end_date = np.datetime64(
            end_ts.date()
        )

        if end_date > start_date:
            total += int(
                np.busday_count(
                    start_date,
                    end_date,
                    holidays=holidays,
                )
            )

    return total