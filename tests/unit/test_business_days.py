import pytest
import numpy as np
from datetime import date, datetime
from app.domain.kpi.business_days import calculate_business_days

def test_same_day_calculation():
    # Wednesday to Wednesday (no weekend)
    d = date(2026, 1, 7) # Wednesday
    # np.busday_count(2026-01-07, 2026-01-08) = 1 day, minus 1 = 0.0
    res = calculate_business_days(d, d)
    assert res == 0.0

def test_one_business_day_delta():
    start = date(2026, 1, 7) # Wednesday
    end = date(2026, 1, 8)   # Thursday
    # 2 business days in [Wednesday, Thursday], minus 1 = 1.0
    res = calculate_business_days(start, end)
    assert res == 1.0

def test_weekend_skipping():
    start = date(2026, 1, 9) # Friday
    end = date(2026, 1, 12)  # Monday
    # Business days: Friday, Monday (2 days). 2 - 1 = 1.0
    res = calculate_business_days(start, end)
    assert res == 1.0

def test_single_holiday_exclusion():
    start = date(2026, 1, 7) # Wednesday
    end = date(2026, 1, 9)   # Friday
    holidays = [np.datetime64('2026-01-08', 'D')] # Thursday holiday
    # Wed, Fri = 2 business days. 2 - 1 = 1.0
    res = calculate_business_days(start, end, holidays=holidays)
    assert res == 1.0

def test_multiple_holidays_exclusion():
    start = date(2026, 1, 5) # Monday
    end = date(2026, 1, 9)   # Friday
    holidays = [np.datetime64('2026-01-06', 'D'), np.datetime64('2026-01-07', 'D')] # Tue, Wed holiday
    # Mon, Thu, Fri = 3 business days. 3 - 1 = 2.0
    res = calculate_business_days(start, end, holidays=holidays)
    assert res == 2.0

def test_end_before_start():
    start = date(2026, 1, 10)
    end = date(2026, 1, 5)
    res = calculate_business_days(start, end)
    assert res == 0.0

def test_none_or_invalid_inputs():
    assert calculate_business_days(None, date(2026, 1, 10)) is None
    assert calculate_business_days(date(2026, 1, 10), None) is None
    assert calculate_business_days("invalid-date", date(2026, 1, 10)) is None
