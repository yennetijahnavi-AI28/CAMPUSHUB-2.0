import os
import time
import logging
import asyncio

logger = logging.getLogger("uvicorn")

def _generate_content_sync(prompt: str) -> str:
    """Strictly Synchronous wrapper using google.generativeai"""
    import google.generativeai as genai
    
    # 1. Initialize API exactly as requested
    api_key = os.getenv("GEMINI_API_KEY", "")
    genai.configure(api_key=api_key)
    
    primary_model_name = "gemini-1.5-flash-latest"
    fallback_model_name = "gemini-1.5-pro-latest"
    
    # In some API environments, those exact strings return 404, so we maintain a deep fallback
    safe_primary = "gemini-flash-latest"
    
    model = genai.GenerativeModel(primary_model_name)
    max_retries = 3

    for attempt in range(max_retries):
        try:
            logger.info(f"[StudySync AI] Synchronous execution attempt {attempt + 1}")
            # Synchronous generate
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            raise Exception("Empty response.")
            
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"[StudySync AI] Primary model failed: {e}")
            
            if "404" in error_str or "not found" in error_str:
                logger.warning("[StudySync AI] 404 triggered. Trying safe alias or bouncing to fallback immediately.")
                # We do a quick safe alias try for Google's weird version mappings
                if attempt == 0:
                    model = genai.GenerativeModel(safe_primary)
                    continue
                else:
                    break
                
            if attempt < max_retries - 1:
                time.sleep(1.5)  # Blocking delay strictly
                continue
                
    # Fallback Execution
    try:
        logger.info(f"[StudySync AI] Engaging robust Fallback Model: {fallback_model_name}")
        fallback_model = genai.GenerativeModel(fallback_model_name)
        fb_resp = fallback_model.generate_content(prompt)
        if fb_resp and fb_resp.text:
            return fb_resp.text.strip()
    except Exception as e:
        logger.error(f"[StudySync AI] Total Failure on fallback: {e}")
        
    return "CampusBot is busy, try again"


async def generate_studysync_ai_response(message: str, history: list) -> str:
    """Format past messages, calculate study suggestions intelligently, and evaluate."""
    if not message or not message.strip():
        return "Empty query provided."
        
    # Phase 4: Intent Awareness & Smart Triggers
    casual_greetings = ["hi", "hello", "hey", "sup", "what's up", "good morning", "good evening", "how are you"]
    lower_q = message.lower().strip()
    
    if lower_q in casual_greetings:
        return "Hello! I am CampusBot, your Smart Study Assistant natively built within CampusHub. How can I facilitate your study group today?"
    
    # Intelligent Pre-processing for Smart Behavior
    study_nudge = ""
    if "binary tree" in lower_q or "bst" in lower_q:
         study_nudge = "\\nNote for AI context: Nudge the student briefly that they should also study BST constraints and traversal algorithms (Inorder, Preorder, Postorder)."
    elif "dsa" in lower_q or "data structures" in lower_q:
         study_nudge = "\\nNote for AI context: Remind the student briefly that algorithmic time complexity (Big-O) is equally important."

    # Format transcript cleanly
    transcript_lines = []
    for doc in history:
        sender = doc.get("sender_name", "User")
        msg = doc.get("message", "")
        if msg:
            transcript_lines.append(f"{sender}: {msg}")
            
    transcript_text = "\\n".join(transcript_lines)
    
    system_prompt = f"""You are CampusBot, an intelligent and advanced educational AI integrated entirely within a student Study Group chat room.
Your role is to deeply explain study topics, provide programming logic, and clarify any university-related educational inquiries.
- Always be structured, concise, and professional but approachable. 
- You must leverage the previous Conversation history to remain Context-Aware (if the student references 'it' or 'previous code', evaluate the history!).
{study_nudge}"""

    # Format explicitly as requested
    full_prompt = f"{system_prompt}\\n\\nConversation:\\n{transcript_text}\\nUser: {message}\\n\\nAnswer clearly:"
    
    # Thread out the synchronous blocking call to prevent Event loop pausing
    try:
        reply = await asyncio.to_thread(_generate_content_sync, full_prompt)
        return reply
    except Exception as e:
        logger.error(f"[StudySync AI] Async Wrapper Exception Tracker: {e}")
        return "CampusBot is busy, try again"

def _analyze_file_sync(file_path: str, action: str) -> str:
    """Extract text from local file and query Gemini"""
    import google.generativeai as genai
    import PyPDF2
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    
    # 1. Extract text
    text_content = ""
    try:
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted: text_content += extracted + "\\n"
        else:
            return "File type not supported for text extraction yet."
    except Exception as e:
        logger.error(f"[StudySync AI] File extraction failed: {e}")
        return "Sorry, I could not read this file."
        
    if not text_content.strip():
        return "The document appears to be empty or unreadable."
    
    # Trim to avoid token explosion
    text_content = text_content[:30000] 
    
    system_prompt = f"""You are CampusBot, an Advanced AI Study Assistant.
You have been provided with the raw extracted text of a study document uploaded by a student.
Action Requested: {action}

Please provide a highly structured, well formatted Markdown response perfectly addressing the requested Action using the Document Content below. Use bullet points and headers.

Document Content:
------------
{text_content}
------------
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"[StudySync AI] Triggering Document Analysis for action: {action} (Attempt {attempt+1})")
            response = model.generate_content(system_prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"[StudySync AI] Document Summary Failed: {e}")
            
            if "404" in error_str or "not found" in error_str:
                if attempt == 0:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    continue
                else:
                    break
                    
            if attempt < max_retries - 1:
                time.sleep(1.5)
                continue
                
    # Fallback Execution
    try:
        logger.info("[StudySync AI] Analysis Fallback to gemini-1.5-pro-latest")
        fallback_model = genai.GenerativeModel("gemini-1.5-pro-latest")
        fb_resp = fallback_model.generate_content(system_prompt)
        if fb_resp and fb_resp.text:
            return fb_resp.text.strip()
    except Exception as e:
        logger.error(f"[StudySync AI] Total Failure on Document fallback: {e}")
        
    return "File analysis failed. I might be overloaded."

async def analyze_studysync_file(file_path: str, action: str) -> str:
    """Thread-safe async wrapper for file analysis"""
    reply = await asyncio.to_thread(_analyze_file_sync, file_path, action)
    return reply
