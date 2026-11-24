import os
import json

from typing import Optional

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException,
    Header
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field

from database import (
    init_db,
    get_messages,
    add_message
)

from llm_service import (
    generate_reply,
    API_KEYS
)


load_dotenv()


app = FastAPI(
    title="Lyftr AI Chatbot",
    version="1.0.0"
)


# -----------------------
# CORS
# -----------------------

origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# -----------------------
# Startup
# -----------------------

@app.on_event("startup")
def startup_event():
    init_db()


# -----------------------
# Request Model
# -----------------------

class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000
    )

    system_prompt: Optional[str] = None


# -----------------------
# Health
# -----------------------

@app.get("/health")
def health_check():

    if len(API_KEYS) < 2:
        raise HTTPException(
            status_code=503,
            detail="key pool not configured"
        )

    return {
        "status": "ok",
        "keys_configured": len(API_KEYS),
        "cache_enabled": True
    }


# -----------------------
# Session History
# -----------------------

@app.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):

    rows = get_messages(session_id)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="session not found"
        )

    messages = []

    for row in rows:

        item = {
            "role": row["role"],
            "content": row["content"]
        }

        if row["metadata"]:
            item["metadata"] = json.loads(
                row["metadata"]
            )

        messages.append(item)

    return {
        "session_id": session_id,
        "messages": messages
    }


# -----------------------
# Chat
# -----------------------

@app.post("/chat")
def chat(
    request: ChatRequest,
    x_simulate_failure: Optional[str] = Header(
        default=None,
        alias="X-Simulate-Failure"
    )
):

    session_id = request.session_id.strip()
    message_text = request.message.strip()

    if not session_id:
        raise HTTPException(
            status_code=422,
            detail="session_id cannot be empty"
        )

    if not message_text:
        raise HTTPException(
            status_code=422,
            detail="message cannot be empty"
        )

    history = get_messages(session_id)

    llm_messages = []

    if request.system_prompt:
        llm_messages.append({
            "role": "system",
            "content": request.system_prompt
        })

    for row in history:
        llm_messages.append({
            "role": row["role"],
            "content": row["content"]
        })

    llm_messages.append({
        "role": "user",
        "content": message_text
    })

    try:
        result = generate_reply(
            llm_messages,
            simulate_failure=x_simulate_failure
        )

    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="all providers unavailable"
        )

    # Only successful requests enter history

    add_message(
        session_id,
        "user",
        message_text
    )

    add_message(
        session_id,
        "assistant",
        result["reply"],
        json.dumps(result["metadata"])
    )

    return {
        "session_id": session_id,
        "reply": result["reply"],
        "metadata": result["metadata"]
    }