import pytest
import pandas as pd
from datetime import datetime
from app.domain.tickets.timeline import (
    _to_naive_ts,
    _merge_intervals,
    _clip_intervals,
    compute_effective_close_and_pauses,
    total_pause_business_days
)

def test_to_naive_ts_timezone_aware():
    tz_aware_str = "2026-01-05T10:00:00+02:00"
    ts = _to_naive_ts(tz_aware_str)
    assert ts.tzinfo is None
    assert ts == pd.Timestamp("2026-01-05 08:00:00")

def test_merge_intervals_overlapping():
    intervals = [
        ("2026-01-05 08:00", "2026-01-05 12:00"),
        ("2026-01-05 10:00", "2026-01-05 14:00"),
        ("2026-01-06 09:00", "2026-01-06 17:00"),
    ]
    merged = _merge_intervals(intervals)
    assert len(merged) == 2
    assert merged[0] == (pd.Timestamp("2026-01-05 08:00"), pd.Timestamp("2026-01-05 14:00"))
    assert merged[1] == (pd.Timestamp("2026-01-06 09:00"), pd.Timestamp("2026-01-06 17:00"))

def test_clip_intervals():
    intervals = [
        ("2026-01-01", "2026-01-10"),
    ]
    clipped = _clip_intervals(intervals, "2026-01-03", "2026-01-07")
    assert len(clipped) == 1
    assert clipped[0] == (pd.Timestamp("2026-01-03"), pd.Timestamp("2026-01-07"))

def test_timeline_a_cloturer_to_cloture_cas_3():
    history = [
        {"created_at": "2026-01-05T09:00:00", "field": {"name": "status"}, "new_value": {"label": "En cours"}},
        {"created_at": "2026-01-07T10:00:00", "field": {"name": "status"}, "new_value": {"label": "A Clôturer"}},
        {"created_at": "2026-01-09T16:00:00", "field": {"name": "status"}, "new_value": {"label": "Clôturé"}},
    ]
    res = compute_effective_close_and_pauses(
        history=history,
        current_assignee="Jean Dupont",
        submission_date="2026-01-05T09:00:00"
    )
    assert res["is_closed"] is True
    assert res["effective_close_date"] == pd.Timestamp("2026-01-07 10:00:00")
    # Pause interval should contain the admin delay window (2026-01-07 10:00 to 2026-01-09 16:00) clipped to effective close
    assert len(res["pause_intervals"]) == 0 or res["pause_intervals"] == [(pd.Timestamp("2026-01-07 10:00:00"), pd.Timestamp("2026-01-07 10:00:00"))]

def test_timeline_reopening_resets_tentative_completion():
    history = [
        {"created_at": "2026-01-05T09:00:00", "field": {"name": "status"}, "new_value": {"label": "A Clôturer"}},
        {"created_at": "2026-01-06T09:00:00", "field": {"name": "status"}, "new_value": {"label": "En cours"}}, # Reopened
        {"created_at": "2026-01-08T09:00:00", "field": {"name": "status"}, "new_value": {"label": "A Clôturer"}},
        {"created_at": "2026-01-09T09:00:00", "field": {"name": "status"}, "new_value": {"label": "Clôturé"}},
    ]
    res = compute_effective_close_and_pauses(
        history=history,
        current_assignee="Jean Dupont",
        submission_date="2026-01-05T09:00:00"
    )
    assert res["is_closed"] is True
    # The effective close date should be the latest tentative completion (2026-01-08 09:00)
    assert res["effective_close_date"] == pd.Timestamp("2026-01-08 09:00:00")

def test_timeline_complement_information_pause_cas_1():
    history = [
        {"created_at": "2026-01-05T09:00:00", "field": {"name": "status"}, "new_value": {"label": "Complément d'information"}},
        {"created_at": "2026-01-07T09:00:00", "field": {"name": "status"}, "new_value": {"label": "En cours"}},
    ]
    res = compute_effective_close_and_pauses(
        history=history,
        current_assignee="Jean Dupont",
        submission_date="2026-01-05T09:00:00",
        reference_date="2026-01-08T09:00:00"
    )
    assert len(res["pause_intervals"]) == 1
    assert res["pause_intervals"][0] == (pd.Timestamp("2026-01-05 09:00:00"), pd.Timestamp("2026-01-07 09:00:00"))
