from fastapi import APIRouter, Depends, HTTPException
from models import LibraryBookingCreate, LibraryBookingResponse, LibrarySeatResponse
from auth import get_current_user
from database import library_bookings_collection, library_seats_collection
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/library", tags=["Library Booking"])

def booking_helper(booking) -> dict:
    return {
        "id": str(booking.get("_id", "")),
        "user_id": booking.get("user_id", ""),
        "seat_id": booking.get("seat_id", ""),
        "date": booking.get("date", ""),
        "start_time": booking.get("start_time", ""),
        "end_time": booking.get("end_time", ""),
        "floor": booking.get("floor", 1),
        "zone": booking.get("zone", "General"),
        "status": booking.get("status", "confirmed"),
        "created_at": booking.get("created_at", datetime.now(timezone.utc)),
    }

@router.get("/seats")
async def get_today_seats():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await get_seats_status(today)

@router.get("/seats/{date}")
async def get_seats_status(date: str, floor: int = 1):
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            return []

        seats = []
        if floor == 1:
            rows = ['A', 'B', 'C', 'D', 'E', 'F']
            cols = 10
            prefix = "F1"
        else:
            # Floor 2 is Group Zone: A1-D5 (20 tables)
            rows = ['A', 'B', 'C', 'D']
            cols = 5
            prefix = "F2"

        for row in rows:
            for col in range(1, cols + 1):
                seat_id = f"{prefix}-{row}{col}"
                booking = await db["library_bookings"].find_one({
                    "seat_id": seat_id,
                    "date": date,
                    "status": "confirmed"
                })
                seats.append({
                    "seat_id": seat_id,
                    "booked": booking is not None,
                    "bookedBy": booking.get("user_id") if booking is not None else None
                })
        return seats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/book-seat", response_model=LibraryBookingResponse)
async def book_seat(booking_data: LibraryBookingCreate, current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Check if seat is already booked
        existing = await db["library_bookings"].find_one({
            "seat_id": booking_data.seat_id,
            "date": booking_data.date,
            "status": "confirmed"
        })
        if existing is not None:
            raise HTTPException(status_code=400, detail="Seat is already booked for this date")

        booking_id = str(uuid.uuid4())
        booking_doc = {
            "_id": booking_id,
            "user_id": str(current_user["_id"]),
            "seat_id": booking_data.seat_id,
            "date": booking_data.date,
            "start_time": booking_data.start_time,
            "end_time": booking_data.end_time,
            "floor": booking_data.floor,
            "zone": booking_data.zone,
            "status": "confirmed",
            "created_at": datetime.now(timezone.utc),
        }
        await db["library_bookings"].insert_one(booking_doc)
        return booking_helper(booking_doc)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "E11000 duplicate key error" in error_msg:
            if "user_id_1_date_1_status_1" in error_msg:
                raise HTTPException(status_code=400, detail="You already have a seat booked for this date")
            if "seat_id_1_date_1" in error_msg:
                raise HTTPException(status_code=400, detail="This seat is already booked for this date by someone else")
        raise HTTPException(status_code=500, detail=f"Booking failed: {error_msg}")

@router.get("/my-bookings")
async def get_my_bookings(current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            return []
            
        bookings = []
        cursor = db["library_bookings"].find({"user_id": str(current_user["_id"])})
        cursor.sort("created_at", -1)
        async for b in cursor:
            bookings.append(booking_helper(b))
        return bookings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cancel/{booking_id}")
async def cancel_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database connection unavailable")
            
        result = await db["library_bookings"].update_one(
            {"_id": booking_id, "user_id": str(current_user["_id"])},
            {"$set": {"status": "cancelled"}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found")
        return {"message": "Booking cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/unbook-seat/{seat_id}")
async def unbook_seat(seat_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Delete from seats status and update/remove from bookings (unbook-seat typically removes confirmed entries)
        result = await db["library_bookings"].delete_one({
            "seat_id": seat_id,
            "user_id": str(current_user["_id"]),
            "status": "confirmed"
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="No active booking found for this seat")
            
        return {"message": "Booking cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
