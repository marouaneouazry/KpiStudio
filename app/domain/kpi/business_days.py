import numpy as np
from datetime import date, datetime
from typing import Optional, Union, Sequence

DateLike = Union[str, date, datetime, np.datetime64]

def _to_dt64(d: DateLike) -> Optional[np.datetime64]:
    if d is None:
        return None
    if isinstance(d, np.datetime64):
        if np.isnat(d):
            return None
        return d.astype('datetime64[D]')
    if isinstance(d, (datetime, date)):
        return np.datetime64(d.strftime('%Y-%m-%d'), 'D')
    if isinstance(d, str):
        try:
            val = np.datetime64(d, 'D')
            if np.isnat(val):
                return None
            return val
        except Exception:
            return None
    return None

def calculate_business_days(
    start_date: Optional[DateLike],
    end_date: Optional[DateLike],
    holidays: Optional[Sequence[DateLike]] = None
) -> Optional[float]:
    """
    Calculates net business days between start_date and end_date excluding weekends and holidays.
    Uses numpy.busday_count and the existing '- 1' business rule.

    Rules:
    - Returns None if start_date or end_date is None or invalid.
    - If end_date < start_date, returns 0.0.
    - Formula: np.busday_count(start, end + 1 day, holidays=holidays) - 1
    """
    if start_date is None or end_date is None:
        return None

    s_date = _to_dt64(start_date)
    e_date = _to_dt64(end_date)

    if s_date is None or e_date is None:
        return None

    if e_date < s_date:
        return 0.0

    holidays_arr = None
    if holidays is not None and len(holidays) > 0:
        clean_hols = []
        for h in holidays:
            dt_h = _to_dt64(h)
            if dt_h is not None and not np.isnat(dt_h):
                clean_hols.append(dt_h)
        if clean_hols:
            holidays_arr = np.array(clean_hols, dtype='datetime64[D]')

    try:
        if holidays_arr is not None and len(holidays_arr) > 0:
            netdays = np.busday_count(s_date, e_date + np.timedelta64(1, 'D'), holidays=holidays_arr)
        else:
            netdays = np.busday_count(s_date, e_date + np.timedelta64(1, 'D'))
        return float(netdays - 1)
    except Exception:
        return None
