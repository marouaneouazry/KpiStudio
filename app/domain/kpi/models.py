from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class DelayResult:
    raw_delay: Optional[float]
    is_over_sla: bool
    status: str = "ok"

@dataclass
class KpiStats:
    total_receves: int = 0
    total_clotures: int = 0
    total_en_cours: int = 0
    clotures_dans_delai: int = 0
    clotures_hors_delai: int = 0
    encours_dans_delai: int = 0
    encours_hors_delai: int = 0
    taux_sla_ap: str = "0.00%"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_receves": self.total_receves,
            "total_clotures": self.total_clotures,
            "total_en_cours": self.total_en_cours,
            "clotures_dans_delai": self.clotures_dans_delai,
            "clotures_hors_delai": self.clotures_hors_delai,
            "encours_dans_delai": self.encours_dans_delai,
            "encours_hors_delai": self.encours_hors_delai,
            "taux_sla_ap": self.taux_sla_ap,
        }
