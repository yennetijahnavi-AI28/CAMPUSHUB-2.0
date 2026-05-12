import os
import shutil
import uuid
import json
import asyncio
from typing import Optional, List, Any
from itertools import combinations
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from models import (
    StudyPreferenceCreate, StudyPreference, StudyGroup, APIResponse, 
    StudyMessageCreate, StudyTaskCreate, StudyTaskUpdate, StandaloneQuizQuery, AIHelpQuery
)
from auth import get_current_user
from database import (
    study_preferences_collection, study_groups_collection, 
    study_messages_collection, study_files_collection, 
    study_tasks_collection, users_collection,
    library_bookings_collection, library_seats_collection
)
from services.studysync_ai_service import (
    generate_studysync_ai_response, analyze_studysync_file, _generate_content_sync
)

router = APIRouter(prefix="/api/study-sync", tags=["StudySync"])

def compatibility_score(a: dict, b: dict) -> int:
    subject_match = len(set(a.get('subjects', [])) & set(b.get('subjects', [])))
    time_overlap = len(set(a.get('availability', [])) & set(b.get('availability', [])))
    
    skill_a = a.get('skill_level', 3)
    skill_b = b.get('skill_level', 3)
    skill_diff = abs(skill_a - skill_b)
    
    score = subject_match * 30 + time_overlap * 20 - skill_diff * 10
    return max(score, 0)

def match_study_group(all_prefs: list, user_id: str):
    me = next((u for u in all_prefs if u['user_id'] == user_id), None)
    if not me:
        return {"status": "searching"}
    
    candidates = [u for u in all_prefs if u['user_id'] != user_id]
    best_group, best_score = None, -1
    
    if len(candidates) == 0:
        return {"status": "searching"}
    
    for r in range(1, 4):
        if len(candidates) < r:
            continue
        for combo in combinations(candidates, r):
            score = compatibility_score(me, combo[0])
            for other in combo[1:]:
                score += compatibility_score(combo[0], other)
            
            if score > best_score:
                best_score = score
                best_group = [me, *combo]
    
    if not best_group or best_score < 30: # Requires at least some compatibility (30 = 1 subject)
        return {"status": "searching"}
        
    # intersection of availabilities
    common = set(me.get('availability', []))
    for member in best_group[1:]:
        common &= set(member.get('availability', []))
    meeting_time = next(iter(common), "TBD") if common else "TBD"
    
    percentage_score = min(int((best_score / 150) * 100) + 40, 98) if best_score > 0 else 85
    
    return {
        "group_id": str(uuid.uuid4()),
        "member_ids": [m['user_id'] for m in best_group],
        "compatibility_score": percentage_score,
        "meeting_time": meeting_time,
        "status": "matched",
        "created_at": datetime.now(timezone.utc)
    }

@router.post("/", response_model=APIResponse)
async def find_group(pref: StudyPreferenceCreate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    pref_dict = pref.dict()
    pref_dict["user_id"] = user_id
    pref_dict["status"] = "searching"
    pref_dict["updated_at"] = datetime.now(timezone.utc)
    
    existing = await study_preferences_collection.find_one({"user_id": user_id})
    if existing:
        await study_preferences_collection.update_one({"user_id": user_id}, {"$set": pref_dict})
    else:
        await study_preferences_collection.insert_one(pref_dict)
    
    cursor = study_preferences_collection.find({"status": {"$ne": "matched"}})
    all_prefs = await cursor.to_list(length=100)
    
    group_data = match_study_group(all_prefs, user_id)
    if group_data.get("status") == "searching":
        return {"success": True, "message": "Searching for matches...", "data": {"status": "searching"}}
        
    await study_groups_collection.insert_one(group_data.copy())
    
    # Update matched members status
    await study_preferences_collection.update_many(
        {"user_id": {"$in": group_data["member_ids"]}},
        {"$set": {"status": "matched"}}
    )
    
    members_profiles = []
    for m_id in group_data["member_ids"]:
        user_doc = await users_collection.find_one({"_id": m_id})
        if user_doc:
            members_profiles.append({
                "id": str(user_doc["_id"]),
                "name": user_doc.get("name", "Unknown"),
                "avatar": user_doc.get("avatar", None),
                "department": user_doc.get("department", "")
            })
    
    group_data["members"] = members_profiles
    
    return {"success": True, "data": group_data}

@router.get("/groups", response_model=APIResponse)
async def get_my_groups(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    cursor = study_groups_collection.find({"member_ids": user_id}).sort("created_at", -1)
    groups = await cursor.to_list(length=10)
    
    enriched_groups = []
    for g in groups:
        g.pop('_id', None)
        members_profiles = []
        for m_id in g["member_ids"]:
            user_doc = await users_collection.find_one({"_id": m_id})
            if user_doc:
                members_profiles.append({
                    "id": str(user_doc["_id"]),
                    "name": user_doc.get("name", "Unknown"),
                    "avatar": user_doc.get("avatar", None),
                    "department": user_doc.get("department", "")
                })
        g["members"] = members_profiles
        enriched_groups.append(g)
        
    return {"success": True, "data": enriched_groups}

@router.get("/preference", response_model=APIResponse)
async def get_my_preference(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    existing = await study_preferences_collection.find_one({"user_id": user_id})
    if existing:
        existing.pop('_id', None)
        return {"success": True, "data": existing}
    return {"success": True, "data": None}


# --- STUDY SYNC COLLABORATION PLATFORM ---

async def verify_group_membership(group_id: str, user_id: str):
    group = await study_groups_collection.find_one({"group_id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")
    if user_id not in group.get("member_ids", []):
        raise HTTPException(status_code=403, detail="Not a member of this study group")
    return group

@router.post("/chat/send", response_model=APIResponse)
async def send_chat_message(msg: StudyMessageCreate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    name = current_user.get("name", "Unknown")
    
    await verify_group_membership(msg.group_id, user_id)
    if not msg.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    chat_doc = {
        "_id": str(uuid.uuid4()),
        "group_id": msg.group_id,
        "sender_id": user_id,
        "sender_name": name,
        "message": msg.message,
        "timestamp": datetime.now(timezone.utc)
    }
    
    await study_messages_collection.insert_one(chat_doc)
    chat_doc["id"] = chat_doc.pop("_id")
    return {"success": True, "data": chat_doc}

@router.get("/chat/{group_id}", response_model=APIResponse)
async def get_chat_messages(group_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(group_id, user_id)
    
    cursor = study_messages_collection.find({"group_id": group_id}).sort("timestamp", 1)
    messages = await cursor.to_list(length=200)
    for m in messages:
        if "_id" in m: m["id"] = str(m.pop("_id"))
    return {"success": True, "data": messages}

class AIAnalyzeQuery(BaseModel):
    group_id: str
    file_id: str
    action: str

@router.post("/analyze", response_model=APIResponse)
async def analyze_file(req: AIAnalyzeQuery, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(req.group_id, user_id)
    
    # 1. Fetch File
    doc = await study_files_collection.find_one({"_id": req.file_id})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Extract filename from URL (we saved it as /uploads/UUID_name)
    file_path = doc["file_url"].lstrip("/") # uploads/UUID_name
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing from server")
        
    # 2. Analyze Document
    reply = await analyze_studysync_file(file_path, req.action)
    
    # 3. Post the summary into the Chat!
    sys_msg = {
        "_id": str(uuid.uuid4()),
        "group_id": req.group_id,
        "sender_id": "ai-assistant",
        "sender_name": "CampusBot AI",
        "message": f"**Analyzed Document:** {doc['file_name']}\n\n{reply}",
        "timestamp": datetime.now(timezone.utc)
    }
    await study_messages_collection.insert_one(sys_msg)
    
    return {"success": True, "message": "Document successfully analyzed"}

@router.get("/quiz/{group_id}", response_model=APIResponse)
async def generate_group_quiz(group_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(group_id, user_id)
    
    # Fetch current tasks to infer what they are studying
    cursor = study_tasks_collection.find({"group_id": group_id})
    tasks = await cursor.to_list(length=20)
    
    task_strings = [t.get("task", "") for t in tasks if t.get("task")]
    context = "General Computer Science topics"
    if task_strings:
        context = ", ".join(task_strings)
        
    prompt = f"""You are CampusBot Quiz Generator.
Based on the following topics the group is studying: {context}

Generate a 3-question multiple choice quiz.
RETURN ONLY PURE JSON format. No markdown blocks, no intro, no outro, no formatting strings.
Format exactly:
[
  {{
    "question": "The question text",
    "options": ["A", "B", "C", "D"],
    "answer": 1
  }}
]
"""
    try:
        reply = await asyncio.to_thread(_generate_content_sync, prompt)
        cleaned_reply = reply.strip()
        
        # Enhanced JSON extraction removing conversational prefixes/suffixes
        import re
        array_match = re.search(r'\[\s*{.*}\s*\]', cleaned_reply, re.DOTALL)
        if array_match:
            cleaned_reply = array_match.group(0)
        else:
            # Fallback if regex fails but brackets exist
            start_idx = cleaned_reply.find("[")
            end_idx = cleaned_reply.rfind("]")
            if start_idx != -1 and end_idx != -1:
                cleaned_reply = cleaned_reply[start_idx:end_idx+1]
            
        quiz_data = json.loads(cleaned_reply)
        return APIResponse(success=True, data=quiz_data)
    except Exception as e:
        print(f"❌ Quiz Generation Error: {e}")
        return {"success": False, "message": "Failed to parse AI quiz. Try again.", "data": None}

@router.post("/quiz/generate", response_model=APIResponse)
async def generate_standalone_quiz(req: StandaloneQuizQuery, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(req.group_id, user_id)
    
    # 1. Determine Context
    context = ""
    if req.text_content:
        context = f"provided text material: {req.text_content}"
    elif req.subject:
        context = f"subject: {req.subject}"
    else:
        # Fallback to tasks
        cursor = study_tasks_collection.find({"group_id": req.group_id})
        tasks = await cursor.to_list(length=20)
        task_strings = [t.get("task", "") for t in tasks if t.get("task")]
        context = ", ".join(task_strings) if task_strings else "General Computer Science concepts"

    prompt = f"""You are CampusBot Educational Evaluator.
Generate a {req.num_questions}-question multiple choice quiz based on: {context}

RULES:
- Return ONLY valid JSON.
- Format: Array of objects with 'question', 'options' (Array of 4), and 'answer' (0-3 index).
- Professional, challenging questions.
"""
    try:
        reply = await asyncio.to_thread(_generate_content_sync, prompt)
        cleaned_reply = reply.strip()
        import re
        array_match = re.search(r'\[\s*{.*}\s*\]', cleaned_reply, re.DOTALL)
        if array_match: cleaned_reply = array_match.group(0)
        quiz_data = json.loads(cleaned_reply)
        return APIResponse(success=True, data=quiz_data)
    except Exception as e:
        return {"success": False, "message": f"Quiz Gen Error: {str(e)}"}

@router.post("/upload", response_model=APIResponse)
async def upload_group_file(
    group_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    name = current_user.get("name", "Unknown")
    await verify_group_membership(group_id, user_id)
    
    # Restrict and Validate
    allowed_exts = [".pdf", ".png", ".jpg", ".jpeg", ".docx", ".txt", ".pptx"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Invalid type {file_ext}. Allowed: PDF, Images, DOCX, TXT, PPTX")
    
    # Simple Size Validation (5MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (Max 5MB)")
        
    os.makedirs("uploads", exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename.replace(' ', '_').replace('/', '_')}"
    file_path = f"uploads/{safe_filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc = {
        "_id": file_id,
        "group_id": group_id,
        "file_name": file.filename,
        "file_url": f"/uploads/{safe_filename}",
        "uploaded_by": name,
        "uploaded_at": datetime.now(timezone.utc)
    }
    await study_files_collection.insert_one(doc)
    doc["id"] = doc.pop("_id")
    
    # Notify chat that a file was uploaded natively
    sys_msg = {
        "_id": str(uuid.uuid4()),
        "group_id": group_id,
        "sender_id": "system",
        "sender_name": "System",
        "message": f"{name} uploaded a file: {file.filename}",
        "timestamp": datetime.now(timezone.utc)
    }
    await study_messages_collection.insert_one(sys_msg)
    
    return {"success": True, "data": doc}

@router.get("/files/{group_id}", response_model=APIResponse)
async def get_group_files(group_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(group_id, user_id)
    
    cursor = study_files_collection.find({"group_id": group_id}).sort("uploaded_at", -1)
    files = await cursor.to_list(length=100)
    for f in files:
        f["id"] = str(f.pop("_id"))
        
    return {"success": True, "data": files}


@router.post("/tasks/add", response_model=APIResponse)
async def add_study_task(task_data: StudyTaskCreate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(task_data.group_id, user_id)
    
    if not task_data.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty")
        
    task_doc = {
        "_id": str(uuid.uuid4()),
        "group_id": task_data.group_id,
        "task": task_data.task,
        "completed": False,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc)
    }
    await study_tasks_collection.insert_one(task_doc)
    task_doc["id"] = task_doc.pop("_id")
    return {"success": True, "data": task_doc}

@router.get("/tasks/{group_id}", response_model=APIResponse)
async def get_study_tasks(group_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(group_id, user_id)
    
    cursor = study_tasks_collection.find({"group_id": group_id}).sort("created_at", -1)
    tasks = await cursor.to_list(length=50)
    for t in tasks:
        if "_id" in t: t["id"] = str(t.pop("_id"))
    return {"success": True, "data": tasks}

@router.patch("/tasks/{task_id}", response_model=APIResponse)
async def update_study_task(task_id: str, update_data: StudyTaskUpdate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    task = await study_tasks_collection.find_one({"_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await verify_group_membership(task["group_id"], user_id)
    
    await study_tasks_collection.update_one(
        {"_id": task_id}, 
        {"$set": {"completed": update_data.completed}}
    )
    return {"success": True, "message": "Task updated"}

    return {"success": True, "message": "Task updated"}

@router.post("/ai-help", response_model=APIResponse)
async def get_ai_help(req: AIHelpQuery, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    await verify_group_membership(req.group_id, user_id)
    
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    # Phase 2: Fetch last 10 messages from this group
    cursor = study_messages_collection.find({"group_id": req.group_id}).sort("timestamp", -1)
    
    # Reverse them to be chronological for AI prompt readability
    history_docs = await cursor.to_list(length=10)
    history_docs.reverse()
    
    # Send history + current query into pure Sync thread executor natively
    reply = await generate_studysync_ai_response(req.query, history_docs)
        
    # Store AI response as a message in the chat
    ai_msg_doc = {
        "_id": str(uuid.uuid4()),
        "group_id": req.group_id,
        "sender_id": "ai-assistant",
        "sender_name": "CampusBot AI",
        "message": reply,
        "timestamp": datetime.now(timezone.utc)
    }
    
    await study_messages_collection.insert_one(ai_msg_doc)
    ai_msg_doc["id"] = ai_msg_doc.pop("_id")
    
    return {"success": True, "data": ai_msg_doc}


@router.post("/groups/{group_id}/book-seat", response_model=APIResponse)
async def book_group_seat(group_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    group = await study_groups_collection.find_one({"group_id": group_id})
    if not group:
        return {"success": False, "message": "Group not found"}
        
    meeting_time = group.get("meeting_time", "TBD") # e.g. "Mon 10-11"
    if meeting_time == "TBD":
        return {"success": False, "message": "No specific meeting time agreed"}
        
    parts = meeting_time.split(" ")
    if len(parts) != 2:
        return {"success": False, "message": "Time format not recognized"}
        
    day_str, time_str = parts[0], parts[1]
    days = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    target_weekday = days.get(day_str)
    
    if target_weekday is None:
        return {"success": False, "message": "Invalid day"}
        
    # Calculate next occurrence of that weekday
    today = datetime.now()
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    target_date = today + timedelta(days=days_ahead)
    date_str = target_date.strftime("%Y-%m-%d")
    
    t_parts = time_str.split("-")
    start_time = f"{int(t_parts[0]):02d}:00" if len(t_parts) == 2 else "10:00"
    end_time = f"{int(t_parts[1]):02d}:00" if len(t_parts) == 2 else "11:00"
    
    # Check if already booked
    existing = await library_bookings_collection.find_one({
        "group_id": group_id, "date": date_str, "status": "confirmed"
    })
    if existing:
        return {"success": True, "data": {"seat_id": existing["seat_id"], "date": date_str, "time": f"{start_time}-{end_time}"}, "message": f"Already booked seat {existing['seat_id']}"}
    
    # Find an open group zone seat (F2)
    rows = ['A', 'B', 'C', 'D']
    selected_seat = None
    for row in rows:
        for col in range(1, 6):
            seat_id = f"F2-{row}{col}"
            conflict = await library_bookings_collection.find_one({
                "seat_id": seat_id, "date": date_str, "status": "confirmed"
            })
            if not conflict:
                selected_seat = seat_id
                break
        if selected_seat: break
        
    if not selected_seat:
        selected_seat = "F2-G1" # Fallback if all taken
        
    booking_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "group_id": group_id,
        "seat_id": selected_seat,
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "floor": 2,
        "zone": "Group Zone",
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc)
    }
    
    await library_bookings_collection.insert_one(booking_doc)
    
    # Store seat status
    await library_seats_collection.insert_one({
        "seat_id": selected_seat, "date": date_str, "isBooked": True, "user_id": user_id
    })
    
    return {
        "success": True, 
        "data": {
            "seat_id": selected_seat,
            "date": date_str,
            "time": f"{start_time}-{end_time}"
        },
        "message": f"Successfully reserved {selected_seat} in Group Zone"
    }

@router.get("/stats", response_model=APIResponse)
async def get_study_stats(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    # 1. Real Activity Aggregation (365 days)
    pipeline = [
        {"$match": {"sender_id": user_id}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "count": {"$sum": 1}
        }}
    ]
    msg_activity = await study_messages_collection.aggregate(pipeline).to_list(400)
    
    task_pipeline = [
        {"$match": {"created_by": user_id}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }}
    ]
    task_activity = await study_tasks_collection.aggregate(task_pipeline).to_list(400)
    
    # Merge and combine onto a 365 day calendar
    activity_map = {item["_id"]: item["count"] for item in msg_activity}
    for item in task_activity:
        activity_map[item["_id"]] = activity_map.get(item["_id"], 0) + item["count"] * 5
        
    activity = []
    base_date = datetime.now() - timedelta(days=364)
    for i in range(365):
        date_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        activity.append({"date": date_str, "count": activity_map.get(date_str, 0)})
    
    # 2. Real Progress from Task Completion
    # Find active groups and their completion rates
    matched_groups = await study_groups_collection.find({"member_ids": user_id}).to_list(10)
    progress = []
    for g in matched_groups:
        sub = g.get("subject", "General")
        g_id = g.get("group_id")
        
        total_tasks = await study_tasks_collection.count_documents({"group_id": g_id})
        done_tasks = await study_tasks_collection.count_documents({"group_id": g_id, "completed": True})
        
        # Mastery is at least 30%, adding 10% per completed task
        mastery = min(30 + (done_tasks * 15), 100) if total_tasks > 0 else 25
        progress.append({"subject": sub, "level": int(mastery)})
    
    if not progress:
        progress = [{"subject": "New Scholar", "level": 15}]

    return APIResponse(success=True, data={"activity": activity, "progress": progress})

@router.get("/leaderboard", response_model=APIResponse)
async def get_leaderboard(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    name = current_user.get("name", "Student")
    
    # Calculate User's Real Points
    msg_count = await study_messages_collection.count_documents({"sender_id": user_id})
    task_count = await study_tasks_collection.count_documents({"created_by": user_id, "completed": True})
    user_points = msg_count + (task_count * 10)
    
    # Top 5 Squads (Simulation for Global diversity)
    squads = [
        {"name": "Neural Pioneers", "score": 98, "members": ["Sarah K.", "Mike R.", "Alex J."]},
        {"name": "Quantum Solvers", "score": 94, "members": ["David L.", "Amy W.", "Chris P."]},
        {"name": "Logic Legends", "score": 89, "members": ["Priya S.", "Rahul M.", "Jen H."]},
        {"name": "Data Wizards", "score": 82, "members": ["Kiran R.", "Joe D.", "Leo M."]}
    ]
    
    # Scholars Leaderboard (Real Injection of Current User)
    individuals = [
        {"name": "Sarah Koenig", "points": 1450, "rank": 1},
        {"name": "David Lin", "points": 1320, "rank": 2},
        {"name": "Priya Sharma", "points": 1150, "rank": 4},
        {"name": "Chris Park", "points": 940, "rank": 5}
    ]
    
    # Insert current user based on points
    me = {"name": name, "points": user_points, "rank": 3}
    individuals.insert(2, me) # Place at rank 3 temporarily or sort properly
    # In a real app we'd query top 5 users from DB.
    
    return APIResponse(success=True, data={"squads": squads, "individuals": individuals})
