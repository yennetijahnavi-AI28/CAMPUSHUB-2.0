import logging
import re
import uuid
import os
from datetime import datetime, timezone
from database import (
    orders_collection,
    library_bookings_collection,
    certificate_requests_collection,
    library_seats_collection
)

logger = logging.getLogger("uvicorn")

# ── Gemini setup (new google.generativeai SDK) ──────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini AI configured (google.generativeai SDK)")
    except Exception as e:
        logger.warning(f"⚠️  Gemini init failed: {e}")
else:
    logger.warning("⚠️  GEMINI_API_KEY not set – AI will use rule-based fallback")


import asyncio
import time

async def generate_ai_response(prompt: str) -> str:
    """Core function to execute Gemini with retries and Fallbacks."""
    import google.generativeai as genai
    
    # Primary Model (Using identical string mapping per user request)
    primary_model_name = "gemini-1.5-flash-latest"
    fallback_model_name = "gemini-1.5-pro-latest"
    
    primary_model = genai.GenerativeModel(primary_model_name)
    fallback_model = genai.GenerativeModel(fallback_model_name)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Generating AI response (Model: {primary_model_name}, Attempt: {attempt+1}/{max_retries})")
            
            # 1. Use synchronous generate_content via asyncio.to_thread to prevent event loop blocking
            # 2. Add timeout-like behavior or standard execution
            response = await asyncio.to_thread(primary_model.generate_content, prompt)
            
            if response and response.text:
                return response.text.strip()
            raise Exception("Empty response received from primary model")
            
        except Exception as e:
            error_str = str(e).lower()
            logger.warning(f"Gemini primary error (Attempt {attempt+1}/{max_retries}): {e}")
            
            # Switch immediately on 404
            if "404" in error_str or "not found" in error_str:
                logger.warning("Primary model not found (404). Triggering immediate fallback.")
                break
                
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # Delay between retries
                continue

    # Fallback Execution
    try:
        logger.info(f"Switching to fallback model: {fallback_model_name}")
        fallback_resp = await asyncio.to_thread(fallback_model.generate_content, prompt)
        if fallback_resp and fallback_resp.text:
            return fallback_resp.text.strip()
        raise Exception("Empty response received from fallback model")
    except Exception as e:
        logger.error(f"Fallback model failed: {e}")
        # ALWAYS return clean text only on complete exhaustion
        return "CampusBot is temporarily busy. Try again in a moment."


async def get_study_ai_response(message: str, history: list) -> str:
    """Format past messages into transcript, append message, and execute with AI."""
    if not message or not message.strip(): 
        return "Empty query provided."
    
    # 1. Advanced NLP / Intent pre-scan
    casual_greetings = ["hi", "hello", "hey", "sup", "what's up", "good morning", "good evening", "how are you"]
    lower_q = message.lower().strip()
    if lower_q in casual_greetings:
        return "Hello! I am CampusBot, your AI Study Assistant. I am ready to explain complex topics, summarize academic texts, or give programming help! What are we studying today?"
        
    # 2. Re-arrange history from oldest to newest
    transcript_lines = []
    for doc in history:
        sender = doc.get("sender_name", "User")
        msg = doc.get("message", "")
        if msg:
            transcript_lines.append(f"{sender}: {msg}")
            
    transcript_text = "\n".join(transcript_lines)
    
    system_prompt = """You are CampusBot, an elite, highly intelligent academic tutor participating in a student study group chat.
You have access to the recent chat history to use for context.
Keep your answers highly accurate, deeply educational, but concise enough for a chat interface.
Respond directly to the latest query."""

    full_prompt = f"{system_prompt}\n\nConversation:\n{transcript_text}\nStudent latest query: {message}\n\nAnswer clearly:"
    
    # Single clean call to the centralized AI function
    reply = await generate_ai_response(full_prompt)
    return reply



class AIService:

    # ── Intent detection ──────────────────────────────────────────────────────
    @staticmethod
    async def detect_intent(query: str, context: dict = None) -> str:
        q = query.lower()

        if context and context.get("last_intent"):
            if any(w in q for w in ["cancel", "unbook", "remove", "don't want"]):
                if context["last_intent"] == "book_seat":
                    return "cancel_seat"
            if any(w in q for w in ["yes", "confirm", "go ahead"]):
                return f"confirm_{context['last_intent']}"

        if any(w in q for w in ["study group", "study partner", "match me", "studysync", "find group"]):
            if any(w in q for w in ["status", "queue", "waitlist", "am i matched"]):
                return "study_sync_status"
            return "study_sync_join"

        if any(w in q for w in ["order", "spending", "spent", "buy", "bought"]):
            if "spent" in q or "spending" in q:
                return "check_spending"
            if any(item in q for item in ["coffee", "tea", "burger", "pizza", "sandwich"]):
                return "place_order"
            return "check_orders"

        if "certificate" in q or ("status" in q and "cert" in q):
            return "check_certificate_status"

        if "book" in q and ("library" in q or "seat" in q):
            return "book_seat"

        if "cancel" in q or "unbook" in q:
            return "cancel_seat"

        return "general"

    # ── Data helpers ──────────────────────────────────────────────────────────
    @staticmethod
    async def get_user_spending(user_id: str) -> str:
        total, count = 0, 0
        async for order in orders_collection.find({"user_id": user_id}):
            total += order.get("total_amount", 0)
            count += 1
        if count == 0:
            return "You haven't placed any food orders yet."
        return f"You have placed {count} orders totalling ₹{total}."

    @staticmethod
    async def get_recent_orders(user_id: str) -> str:
        rows = []
        cursor = orders_collection.find({"user_id": user_id}).sort("created_at", -1).limit(5)
        async for o in cursor:
            items_str = ", ".join(i["name"] for i in o.get("items", []))
            rows.append(f"• {o['canteen']}: {items_str} (₹{o['total_amount']})")
        return "Your recent orders:\n" + "\n".join(rows) if rows else "You don't have any recent orders."

    @staticmethod
    async def get_certificate_status(user_id: str) -> str:
        rows = []
        cursor = certificate_requests_collection.find({"user_id": user_id}).sort("created_at", -1).limit(3)
        async for c in cursor:
            rows.append(f"• {c['certificate_type']}: {c['status']}")
        return "Your certificate requests:\n" + "\n".join(rows) if rows else "You haven't requested any certificates yet."

    @staticmethod
    async def book_seat_action(query: str, user_id: str) -> tuple:
        seat_match = re.search(r'seat\s*([a-z0-9\-]+)', query, re.I)
        seat_id = seat_match.group(1).upper() if seat_match else None
        if not seat_id:
            return "Which seat would you like to book? (e.g., 'Book seat F1-A1')", {"last_intent": "book_seat"}
        if not seat_id.startswith("F1-"):
            seat_id = f"F1-{seat_id}"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        existing = await library_seats_collection.find_one({"seat_id": seat_id, "date": today})
        if existing:
            return f"Sorry, seat {seat_id} is already booked for today.", None
        booking_data = {
            "_id": str(uuid.uuid4()), "user_id": user_id, "seat_id": seat_id,
            "date": today, "start_time": "09:00", "end_time": "12:00",
            "floor": 1, "zone": "Main Hall", "status": "confirmed",
            "created_at": datetime.now(timezone.utc)
        }
        await library_bookings_collection.insert_one(booking_data)
        await library_seats_collection.insert_one({"seat_id": seat_id, "date": today, "isBooked": True, "user_id": user_id})
        return f"Seat {seat_id} has been booked for you today (9 AM – 12 PM)!", {"last_booked_seat": seat_id}

    @staticmethod
    async def cancel_seat_action(user_id: str, context: dict) -> str:
        seat_id = context.get("last_booked_seat")
        if not seat_id:
            booking = await library_bookings_collection.find_one(
                {"user_id": user_id, "status": "confirmed"}, sort=[("created_at", -1)]
            )
            if not booking:
                return "I couldn't find any active seat bookings to cancel."
            seat_id = booking["seat_id"]
        await library_bookings_collection.update_many(
            {"user_id": user_id, "seat_id": seat_id, "status": "confirmed"},
            {"$set": {"status": "cancelled"}}
        )
        await library_seats_collection.delete_many({"seat_id": seat_id, "user_id": user_id})
        return f"Your booking for seat {seat_id} has been cancelled."

    @staticmethod
    async def place_order_action(query: str, user_id: str) -> str:
        menu = {
            "coffee":   {"price": 40,  "canteen": "Main Canteen"},
            "tea":      {"price": 15,  "canteen": "Main Canteen"},
            "burger":   {"price": 80,  "canteen": "Food Court"},
            "pizza":    {"price": 150, "canteen": "Food Court"},
            "sandwich": {"price": 50,  "canteen": "Main Canteen"},
        }
        found = next(((k, v) for k, v in menu.items() if k in query.lower()), None)
        if not found:
            return "What would you like to order? I can help with coffee, tea, burgers, etc."
        item_name, details = found
        order_data = {
            "_id": str(uuid.uuid4()), "user_id": user_id, "canteen": details["canteen"],
            "items": [{"name": item_name.capitalize(), "price": details["price"], "quantity": 1}],
            "total_amount": details["price"], "status": "confirmed",
            "created_at": datetime.now(timezone.utc)
        }
        await orders_collection.insert_one(order_data)
        return f"Ordered 1 {item_name.capitalize()} (₹{details['price']}) from {details['canteen']}. Ready soon! 🍽️"

    # ── StudySync mutators ────────────────────────────────────────────────────
    @staticmethod
    async def get_study_sync_status(user_id: str) -> str:
        from database import study_preferences_collection, study_groups_collection, users_collection
        group = await study_groups_collection.find_one({"member_ids": user_id}, sort=[("created_at", -1)])
        if group:
            members = []
            for m_id in group["member_ids"]:
                u = await users_collection.find_one({"_id": m_id})
                if u:
                    members.append(u.get("name", "Unknown"))
            return f"You're matched! Group: {', '.join(members)}. Meeting: {group['meeting_time']} 🎉"
        pref = await study_preferences_collection.find_one({"user_id": user_id})
        if pref and pref.get("status") == "searching":
            return f"You're in the queue for: {', '.join(pref['subjects'])}. We'll notify you when matched!"
        return "You're not in any study group yet. Say 'Match me for Machine Learning' to get started!"

    @staticmethod
    async def join_study_sync(query: str, user_id: str) -> str:
        from database import study_preferences_collection, study_groups_collection
        from routes.study_sync_routes import match_study_group
        SUBJECTS = ["Data Structures", "Database Management", "Operating Systems",
                    "Computer Networks", "Machine Learning", "Web Development"]
        matched = [s for s in SUBJECTS if s.lower() in query.lower()]
        if not matched:
            return f"Please name a subject! Available: {', '.join(SUBJECTS)}"
        pref_dict = {
            "user_id": user_id, "subjects": matched,
            "availability": ["Mon 10-11", "Tue 14-15", "Wed 16-17", "Thu 11-12", "Fri 10-11"],
            "skill_level": 3, "status": "searching",
            "updated_at": datetime.now(timezone.utc)
        }
        await study_preferences_collection.update_one({"user_id": user_id}, {"$set": pref_dict}, upsert=True)
        cursor = study_preferences_collection.find({"status": {"$ne": "matched"}})
        all_prefs = await cursor.to_list(length=100)
        group_data = match_study_group(all_prefs, user_id)
        if group_data.get("status") == "searching":
            return f"Added you to the waitlist for {', '.join(matched)}! You'll be matched soon 🔍"
        await study_groups_collection.insert_one(group_data.copy())
        await study_preferences_collection.update_many(
            {"user_id": {"$in": group_data["member_ids"]}}, {"$set": {"status": "matched"}}
        )
        return f"🎉 Matched! {group_data['compatibility_score']}% compatibility. Check your StudySync page!"

    # ── Main entry point ──────────────────────────────────────────────────────
    @staticmethod
    async def get_ai_response(query: str, user_data: dict = None, context: dict = None) -> tuple:
        intent = await AIService.detect_intent(query, context)
        user_id = str(user_data.get("_id")) if user_data else None
        user_name = user_data.get("name", "Student") if user_data else "Student"

        new_context = dict(context or {})
        new_context["last_intent"] = intent

        # ── Structured intents (no LLM needed) ────────────────────────────
        if intent == "check_spending" and user_id:
            return await AIService.get_user_spending(user_id), new_context
        if intent == "check_orders" and user_id:
            return await AIService.get_recent_orders(user_id), new_context
        if intent == "check_certificate_status" and user_id:
            return await AIService.get_certificate_status(user_id), new_context
        if intent == "book_seat" and user_id:
            resp, ctx_up = await AIService.book_seat_action(query, user_id)
            new_context.update(ctx_up or {})
            return resp, new_context
        if intent == "cancel_seat" and user_id:
            return await AIService.cancel_seat_action(user_id, new_context), new_context
        if intent == "place_order" and user_id:
            return await AIService.place_order_action(query, user_id), new_context
        if intent == "study_sync_status" and user_id:
            return await AIService.get_study_sync_status(user_id), new_context
        if intent == "study_sync_join" and user_id:
            return await AIService.join_study_sync(query, user_id), new_context

        # ── Gemini-powered free-form response ─────────────────────────────
        system_prompt = f"""You are CampusBot, an intelligent assistant for CampusHub 2.0 — a smart university platform.
You help students with: food ordering, library seat booking, certificate requests, exam info, study group matching (StudySync), and general campus queries.
Keep responses concise, friendly, and campus-relevant. Student name: {user_name}."""

        full_prompt = f"{system_prompt}\n\nStudent: {query}\nCampusBot:"

        # Call the new stable function
        reply = await generate_ai_response(full_prompt)
        return reply, new_context
