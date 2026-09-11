from typing import Optional, Dict, Any

def get_sla_for_domain(domain: Optional[str], sla_mapping: Dict[str, Any]) -> Optional[int]:
    """
    Maps a Sub-Domain ("Sous Domaine MON") string to its target SLA in business days.
    Returns None if the domain is missing or unmapped.
    """
    if not domain or not sla_mapping:
        return None
    val = sla_mapping.get(str(domain).strip())
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    return None

def is_over_sla(delay: Optional[float], sla_target: Optional[int]) -> bool:
    """
    Determines whether a calculated delay exceeds the target SLA threshold.
    Returns True if delay > sla_target, otherwise False.
    """
    if delay is None or sla_target is None:
        return False
    return float(delay) > float(sla_target)
