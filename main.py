# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# --- App Initialization ---
app = FastAPI()

# --- CORS Configuration ---
# This allows your React frontend (running on localhost:3000)
# to communicate with your backend (running on localhost:8000).
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
# This defines the shape of the data your API expects.
class AvailabilityInput(BaseModel):
    timezone: str
    start_local: datetime
    end_local: datetime

# This defines the shape of the response.
class OverlapResponse(BaseModel):
    is_overlap: bool
    overlap_start_utc: datetime | None = None
    overlap_end_utc: datetime | None = None


# --- API Endpoint ---
@app.post("/calculate-overlap", response_model=OverlapResponse)
def find_overlap(availabilities: list[AvailabilityInput]):
    """
    Accepts a list of user availabilities and finds the common overlapping time slot in UTC.
    """
    if not availabilities or len(availabilities) < 2:
        raise HTTPException(status_code=400, detail="At least two availability slots are required.")

    converted_slots = []
    for slot in availabilities:
        try:
            # Get the timezone object
            tz = ZoneInfo(slot.timezone)
            # Localize the naive datetime from the request, then convert to UTC
            start_utc = slot.start_local.astimezone(tz).astimezone(ZoneInfo("UTC"))
            end_utc = slot.end_local.astimezone(tz).astimezone(ZoneInfo("UTC"))
            converted_slots.append((start_utc, end_utc))
        except ZoneInfoNotFoundError:
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {slot.timezone}")

    # --- The Core Overlap Logic ---
    # 1. Initialize the overlap window with the first person's availability.
    # The .replace() is to remove timezone info for comparison, as they are all now in UTC.
    first_slot_start, first_slot_end = converted_slots[0]
    overlap_start = first_slot_start
    overlap_end = first_slot_end

    # 2. Iterate through the rest of the slots and narrow down the window.
    for current_start, current_end in converted_slots[1:]:
        # The latest start time becomes the new start of the overlap.
        overlap_start = max(overlap_start, current_start)
        # The earliest end time becomes the new end of the overlap.
        overlap_end = min(overlap_end, current_end)

    # 3. Check if a valid overlap exists.
    if overlap_start < overlap_end:
        return OverlapResponse(
            is_overlap=True,
            overlap_start_utc=overlap_start,
            overlap_end_utc=overlap_end
        )
    else:
        return OverlapResponse(is_overlap=False)

# A simple root endpoint to check if the server is running.
@app.get("/")
def read_root():
    return {"message": "Time Zone Scheduler API is running!"}