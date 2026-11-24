# Lyftr AI – LLM Chatbot with Key Failover and Response Caching

A full-stack AI chatbot built with React, FastAPI, LiteLLM, Gemini and SQLite.

The application supports multi-turn conversations, API-key failover, LiteLLM response caching, per-request token tracking and persistent local session history.

---

## 1. Live URLs

### Frontend
https://lyftr-ai-assignment-alpha.vercel.app/

### Backend
https://lyftr-ai-assignment-wyyo.onrender.com

### Health Check
https://lyftr-ai-assignment-wyyo.onrender.com/health

### GitHub Repository
https://github.com/vaanimunjal/lyftr-ai-assignment

> Note: The backend is deployed on Render's free tier. After a period of inactivity, the first request may take longer while the service starts.

---

## 2. Run locally: with Docker and without

### Environment Configuration

Create `backend/.env` with:

```env
LLM_API_KEYS=your_first_api_key,your_second_api_key
DATABASE_URL=sqlite:///./app.db
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
ENABLE_FAILURE_SIMULATION=true
LLM_MODEL=gemini/gemini-3-flash-preview