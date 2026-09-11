import pytest
from unittest.mock import MagicMock
from datetime import date
from app.services.phase2_service import Phase2Service, apply_phase2_correction

def test_phase2_service_process_correction_success():
    mock_history = [
        {"created_at": "2026-01-05T09:00:00", "field": {"name": "status"}, "new_value": {"label": "En cours"}},
        {"created_at": "2026-01-06T09:00:00", "field": {"name": "status"}, "new_value": {"label": "Complément d'information"}},
        {"created_at": "2026-01-07T09:00:00", "field": {"name": "status"}, "new_value": {"label": "En cours"}},
        {"created_at": "2026-01-08T09:00:00", "field": {"name": "status"}, "new_value": {"label": "A Clôturer"}},
    ]

    mock_client = MagicMock()
    mock_client.fetch_ticket_history.return_value = mock_history

    service = Phase2Service(mantis_client=mock_client)
    res = service.process_correction(
        ticket_id=12345,
        current_assignee="Jean Dupont",
        submission_date="2026-01-05T09:00:00",
        holidays=[],
        today_ref="2026-01-09T09:00:00"
    )

    assert res is not None
    assert res["is_closed"] is True
    assert "corrected_delai" in res
    assert res["effective_close_date"] is not None

def test_phase2_service_api_failure():
    mock_client = MagicMock()
    mock_client.fetch_ticket_history.return_value = None

    service = Phase2Service(mantis_client=mock_client)
    res = service.process_correction(
        ticket_id=999,
        current_assignee="Jean Dupont",
        submission_date="2026-01-05T09:00:00",
        holidays=[],
        today_ref="2026-01-09T09:00:00"
    )
    assert res is None
