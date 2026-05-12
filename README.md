# 🎓 CampusHub 2.0

CampusHub 2.0 is a full-stack smart campus platform that combines essential student services with AI-powered collaboration tools.

It transforms traditional campus applications into an intelligent ecosystem where students can:

- Access campus services
- Find study partners using AI
- Collaborate in real-time using chat, file sharing, and AI assistance

---

# 📌 Overview

CampusHub 2.0 bridges the gap between academic collaboration and campus services by integrating them into one AI-powered platform.

---

# 🌟 Core Features

## 🧠 StudySync (AI Study Group Matching)

Automatically forms study groups (2–4 students) based on:

- Subjects
- Availability
- Skill level

### Outputs
- Compatibility score
- Suggested meeting time

---

## 💬 Group Collaboration System

- Dedicated study group workspace
- Real-time chat system
- Context-aware AI assistant (CampusBot)
- Task management system

---

## 🤖 CampusBot AI (Gemini Powered)

- Explains concepts (DSA, etc.)
- Answers study-related queries
- Uses chat context for smarter responses
- Integrated directly inside group chat

---

## 📂 File Sharing System

- Upload notes (PDFs, images, documents)
- Share resources within study groups
- Persistent storage using MongoDB

---

## 📝 AI Quiz Generator

- Generates quizzes from topics
- Multiple-choice question format
- Helps reinforce learning

---

## 🏫 Campus Services

- 🍔 Food ordering system
- 📖 Library seat booking
- 📄 Certificate requests
- 🔔 Exam alerts
- 🧾 Complaint system

---

# 🏗️ Tech Stack

## Frontend
- React.js (Vite)
- Tailwind CSS
- Axios

## Backend
- FastAPI (Python)
- REST APIs

## Database
- MongoDB Atlas

## AI Integration
- Google Gemini API (`google-generativeai`)

---

# ⚙️ Architecture

```text
React Frontend (Vercel)
        ↓
FastAPI Backend (Render)
        ↓
MongoDB Atlas
        ↓
Google Gemini AI
```

---

# 🚀 Getting Started

## 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/campushub.git
cd campushub
```

---

## 2️⃣ Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### Create `.env` file

```env
MONGO_URI=your_mongodb_uri
GEMINI_API_KEY=your_api_key
```

### Run Backend

```bash
uvicorn main:app --reload
```

---

## 3️⃣ Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open in browser:

```text
http://localhost:5173
```

---

# 📂 Project Structure

```text
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
```

---

# 🔥 Highlights

- AI-driven study group matching
- Integrated chat + AI + file sharing
- Full-stack scalable architecture
- Modern UI with premium design
- Real-world student collaboration solution

---

# ⚠️ Challenges Faced

| Challenge | Solution |
|-----------|----------|
| Gemini API instability | Retry + fallback mechanism |
| MongoDB sync issues | Improved API flow |
| UI clutter | Modular component structure |

---

# 🚧 Future Improvements

- WebSocket real-time chat
- Notification system
- AI-based study recommendations
- Mobile app version

---

# 🏆 Hackathon Value

CampusHub 2.0 demonstrates:

- Real-world impact on student collaboration
- Practical AI integration in education
- Clean architecture and scalability
- Strong UI/UX experience

---

# 👨‍💻 Author

*Jahnavi Yenneti*

---

# 📜 License

This project is developed for educational and hackathon purposes only.
