📌 Overview
CampusHub 2.0 is a full-stack smart campus platform that combines essential student services with AI-powered collaboration tools.

It transforms traditional campus apps into an intelligent ecosystem, where students can:

Access services (food, library, certificates)
Find study partners using AI
Collaborate in real-time with chat, files, and AI assistance
🌟 Core Features
🧠 StudySync (AI Study Group Matching)
Automatically forms study groups (2–4 students)

Based on:

Subjects
Availability
Skill level
Outputs:

Compatibility score
Suggested meeting time
💬 Group Collaboration System
Dedicated study group page
Real-time chat (MongoDB-backed)
Context-aware AI assistant (CampusBot)
Task management system
🤖 CampusBot AI (Gemini Powered)
Explains concepts (DSA, etc.)
Answers study queries
Uses chat context for smarter responses
Integrated inside group chat
📂 File Sharing (Study Resources)
Upload notes (PDF, images, docs)
Shared within study groups
Persistent storage with MongoDB
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
React (Frontend - Vercel)
        ↓
FastAPI (Backend - Render)
        ↓
MongoDB Atlas
        ↓
Gemini AI (Google)
🚀 Getting Started (Local Setup)
1️⃣ Clone Repository
git clone https://github.com/your-username/campushub.git
cd campushub
2️⃣ Backend Setup
cd backend
pip install -r requirements.txt
Create .env file:

MONGO_URI=your_mongodb_uri
GEMINI_API_KEY=your_api_key
Run backend:

uvicorn main:app --reload
3️⃣ Frontend Setup
cd frontend
npm install
npm run dev
App runs at:

http://localhost:5173
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
Full-stack scalable architecture
Modern dark UI with premium feel
Real-world problem solving
⚠️ Known Challenges (Handled)
Gemini API instability → fixed with retry + fallback
MongoDB sync issues → resolved with proper API flow
UI clutter → improved with modular layout
🚧 Future Improvements
WebSocket real-time chat
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
JAHNAVI

📜 License
This project is developed for educational and hackathon purposes.
