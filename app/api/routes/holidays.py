from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.api.dependencies import get_current_user, User
try:
    from app.holidays import (
        get_available_years, load_calendar, save_calendar,
        create_next_year_calendar, validate_calendar, reopen_calendar
    )
except ModuleNotFoundError:
    from holidays import (
        get_available_years, load_calendar, save_calendar,
        create_next_year_calendar, validate_calendar, reopen_calendar
    )

router = APIRouter(prefix="/api/holidays", tags=["Holidays"])

class CreateNextYearPayload(BaseModel):
    from_year: Optional[int] = None

class HolidayItemPayload(BaseModel):
    id: Optional[str] = None
    name: str
    type: str  # national, religious, exceptional
    status: Optional[str] = "validated"
    dates: List[str] = []

class CalendarPayload(BaseModel):
    year: int
    status: Optional[str] = "draft"
    holidays: List[HolidayItemPayload]

@router.get("/years")
def get_years(current_user: User = Depends(get_current_user)):
    return {"years": get_available_years()}

@router.get("/{year}")
def get_calendar_by_year(year: int, current_user: User = Depends(get_current_user)):
    try:
        cal = load_calendar(year)
        return cal
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/create-next")
def create_next_year(payload: CreateNextYearPayload = None, current_user: User = Depends(get_current_user)):
    try:
        if payload and payload.from_year:
            from_yr = payload.from_year
        else:
            avail = get_available_years()
            if not avail:
                raise ValueError("Aucun calendrier source n'est disponible pour dériver l'année suivante.")
            from_yr = max(item["year"] for item in avail)
        new_cal = create_next_year_calendar(from_yr)
        return new_cal
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{year}")
def update_calendar(year: int, payload: CalendarPayload, current_user: User = Depends(get_current_user)):
    try:
        saved = save_calendar(year, payload.dict())
        return saved
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{year}/validate")
def validate_calendar_endpoint(year: int, current_user: User = Depends(get_current_user)):
    try:
        validated_cal = validate_calendar(year)
        return validated_cal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{year}/reopen")
def reopen_calendar_endpoint(year: int, current_user: User = Depends(get_current_user)):
    try:
        reopened_cal = reopen_calendar(year)
        return reopened_cal
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
