from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai_client import get_ai_response

router = APIRouter()

class ChatMessage(BaseModel):
    user_message: str

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    try:
        reply = await get_ai_response(message.user_message)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))