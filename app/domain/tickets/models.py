from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class TicketRecord:
    ticket_id: Any
    domain: str
    status: str
    submission_date: Any
    updated_date: Any
    assignee: Optional[str] = None
    sla_target: Optional[int] = None
    delay: Optional[float] = None
    is_over_sla: bool = False
