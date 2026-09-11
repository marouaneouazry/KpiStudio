from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class MantisHistoryEvent:
    created_at: str
    field_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MantisHistoryEvent":
        field_info = data.get("field", {})
        fname = field_info.get("name") if isinstance(field_info, dict) else str(field_info)
        return cls(
            created_at=data.get("created_at", ""),
            field_name=fname,
            old_value=data.get("old_value"),
            new_value=data.get("new_value")
        )
