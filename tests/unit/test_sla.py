import pytest
from app.domain.kpi.sla import get_sla_for_domain, is_over_sla

@pytest.fixture
def sample_sla_mapping():
    return {
        "INCIDENT_COMMERCE": 3,
        "EVOLUTION_MONETIQUE": 10,
        "SUPPORT_TECHNIQUE": 5,
    }

def test_get_sla_for_domain_mapped(sample_sla_mapping):
    assert get_sla_for_domain("INCIDENT_COMMERCE", sample_sla_mapping) == 3
    assert get_sla_for_domain("EVOLUTION_MONETIQUE", sample_sla_mapping) == 10

def test_get_sla_for_domain_unmapped_or_empty(sample_sla_mapping):
    assert get_sla_for_domain("DOMAINE_INCONNU", sample_sla_mapping) is None
    assert get_sla_for_domain("", sample_sla_mapping) is None
    assert get_sla_for_domain(None, sample_sla_mapping) is None

def test_is_over_sla_within_limit():
    assert is_over_sla(2.0, 3) is False
    assert is_over_sla(3.0, 3) is False  # Equal to SLA target is not exceeded

def test_is_over_sla_exceeded():
    assert is_over_sla(3.5, 3) is True
    assert is_over_sla(4.0, 3) is True

def test_is_over_sla_none_handling():
    assert is_over_sla(None, 3) is False
    assert is_over_sla(4.0, None) is False
    assert is_over_sla(None, None) is False
