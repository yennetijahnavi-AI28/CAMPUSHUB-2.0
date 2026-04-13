📌 Overview
🎓 CampusHub 2.0

CampusHub 2.0 is a full-stack smart campus platform that combines essential student services with AI-powered collaboration tools.

It transforms traditional campus applications into an intelligent ecosystem, enabling students to:

Access campus services (food, library, certificates)
Find study partners using AI
Collaborate in real-time with chat, file sharing, and AI assistance
📌 Overview

CampusHub 2.0 bridges the gap between academic collaboration and campus services by integrating them into one platform powered by AI.

🌟 Core Features
🧠 StudySync (AI Study Group Matching)
Automatically forms study groups (2–4 students)
Matching based on:
Subjects
Availability
Skill level
Outputs:
Compatibility score
Suggested meeting time
💬 Group Collaboration System
Dedicated study group workspace
Real-time chat (MongoDB-backed)
Context-aware AI assistant (CampusBot)
Task management system
🤖 CampusBot AI (Gemini Powered)
Explains concepts (DSA, etc.)
Answers study queries
Uses chat context for smarter responses
Integrated inside group chat
📂 File Sharing (Study Resources)
Upload notes (PDF, images, documents)
Share resources within study groups
Persistent storage using MongoDB
📝 AI Quiz Generator
Generates quizzes from topics
Multiple-choice format
Helps reinforce learning
🏫 Campus Services
🍔 Food ordering system
📖 Library seat booking
📄 Certificate requests
🔔 Exam alerts
🧾 Complaint system
🏗️ Tech Stack

Frontend

React.js (Vite)
Tailwind CSS
Axios

Backend

FastAPI (Python)
REST APIs

Database

MongoDB Atlas

AI Integration

Google Gemini API (google-generativeai)
⚙️ Architecture
Frontend (React - Vercel)
        ↓
Backend (FastAPI - Render)
        ↓
Database (MongoDB Atlas)
        ↓
AI Layer (Google Gemini)
🚀 Getting Started (Local Setup)
1. Clone the Repository
git clone https://github.com/your-username/campushub.git
cd campushub
2. Backend Setup
cd backend
pip install -r requirements.txt

Create a .env file:

MONGO_URI=your_mongodb_uri
GEMINI_API_KEY=your_api_key

Run backend:

uvicorn main:app --reload
3. Frontend Setup
cd frontend
npm install
npm run dev

Open in browser:
👉 http://localhost:5173

📂 Project Structure
campushub/
│
├── backend/
│   ├── routes/
│   ├── services/
│   ├── models/
│   └── main.py
│
├── frontend/
│   ├── components/
│   ├── pages/
│   └── App.jsx
│
└── README.md
🔥 Highlights
AI-driven study group matching
Integrated chat + AI + file sharing
Scalable full-stack architecture
Modern UI with clean design
Solves real-world student collaboration problems
⚠️ Known Challenges (Handled)
Gemini API instability → handled using retry + fallback
MongoDB sync issues → resolved with proper API flow
UI clutter → improved using modular design
🚧 Future Improvements
WebSocket-based real-time chat
Notifications system
AI-based study recommendations
Mobile app version
🏆 Hackathon Value

CampusHub 2.0 demonstrates:

Real-world impact on student collaboration
Practical use of AI in education
Clean architecture and scalability
Strong UI/UX with interactive features
👨‍💻 Author

Jahnavi

📜 License

This project is developed for educational and hackathon purposes only.
