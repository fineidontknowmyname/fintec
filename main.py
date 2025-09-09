# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from pytz import timezone, UTC, UnknownTimeZoneError

# --- App Initialization ---
app = FastAPI()

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Data Validation ---
class AvailabilityInput(BaseModel):
    timezone: str
    start_local: datetime
    end_local: datetime

class OverlapResponse(BaseModel):
    is_overlap: bool
    overlap_start_utc: datetime | None = None
    overlap_end_utc: datetime | None = None


# --- API Endpoint ---
@app.post("/calculate-overlap", response_model=OverlapResponse)
def find_overlap(availabilities: list[AvailabilityInput]):
    if not availabilities or len(availabilities) < 2:
        raise HTTPException(status_code=400, detail="At least two availability slots are required.")

    converted_slots = []
    for slot in availabilities:
        try:
            # Get the timezone object using pytz
            tz = timezone(slot.timezone)
            
            # Localize the naive datetime, then convert to UTC
            # pytz requires a different method for this
            start_utc = tz.localize(slot.start_local).astimezone(UTC)
            end_utc = tz.localize(slot.end_local).astimezone(UTC)
            
            converted_slots.append((start_utc, end_utc))
        except UnknownTimeZoneError:
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {slot.timezone}")

    # --- The Core Overlap Logic (this part remains the same) ---
    first_slot_start, first_slot_end = converted_slots[0]
    overlap_start = first_slot_start
    overlap_end = first_slot_end

    for current_start, current_end in converted_slots[1:]:
        overlap_start = max(overlap_start, current_start)
        overlap_end = min(overlap_end, current_end)

    if overlap_start < overlap_end:
        return OverlapResponse(
            is_overlap=True,
            overlap_start_utc=overlap_start,
            overlap_end_utc=overlap_end
        )
    else:
        return OverlapResponse(is_overlap=False)

@app.get("/")
def read_root():
    return {"message": "Time Zone Scheduler API is running!"}
