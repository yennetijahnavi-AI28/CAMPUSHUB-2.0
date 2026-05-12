from fastapi import APIRouter, Depends
from auth import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        db = get_database()

        user_id = str(current_user["_id"])

        if db is None:
            return {
                "total_orders": 0,
                "active_bookings": 0,
                "pending_certificates": 0,
                "open_complaints": 0,
                "total_study_groups": 0,
            }

        total_orders         = await db["orders"].count_documents({"user_id": user_id})
        active_bookings      = await db["library_bookings"].count_documents({"user_id": user_id, "status": "confirmed"})
        pending_certificates = await db["certificate_requests"].count_documents({"user_id": user_id})
        open_complaints      = await db["complaints"].count_documents({"user_id": user_id, "status": {"$in": ["open", "in_progress"]}})
        total_study_groups   = await db["study_groups"].count_documents({"member_ids": user_id})

        return {
            "total_orders":         total_orders,
            "active_bookings":      active_bookings,
            "pending_certificates": pending_certificates,
            "open_complaints":      open_complaints,
            "total_study_groups":   total_study_groups,
        }
    except Exception as e:
        print(f"[STATS ERROR] {e}")
        return {
            "total_orders": 0, "active_bookings": 0,
            "pending_certificates": 0, "open_complaints": 0, "total_study_groups": 0,
        }

@router.get("/chart-data")
async def get_chart_data(current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        db = get_database()

        if db is None:
            return {"weekly_orders": [0]*7}

        orders = await db["orders"].find().to_list(500)
        weekly = [0]*7
        for o in orders:
            if "created_at" in o:
                try:
                    weekly[o["created_at"].weekday()] += 1
                except Exception:
                    pass
        return {"weekly_orders": weekly}
    except Exception as e:
        print(f"[CHART ERROR] {e}")
        return {"weekly_orders": [0]*7}
