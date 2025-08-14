from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.unified_service import UnifiedChatService
import os
import logging

router = APIRouter()

# Global service instance
_global_service = None

def get_service():
    """Get or create the global service instance"""
    global _global_service
    if _global_service is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        _global_service = UnifiedChatService(api_key)
        logging.info("Created global UnifiedChatService instance")
    return _global_service

class ChatMessageRequest(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    user_response: str
    actions: List[Dict]
    action_results: List[Dict]
    request_id: str

@router.post("/chat", response_model=ChatMessageResponse)
async def chat(request: ChatMessageRequest):
    try:
        logging.info(f"Processing chat message: {request.message[:100]}...")
        
        # Get OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.error("OpenAI API key not configured")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Configuration Error",
                    "detail": "OpenAI API key not configured",
                    "status_code": 500
                }
            )
        
        # Get global service instance
        service = get_service()
        
        # Process message
        result = await service.process_message(request.message)
        
        logging.info(f"Chat message processed successfully")
        
        return ChatMessageResponse(**result)
        
    except Exception as e:
        logging.error(f"Error processing chat message: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Chat Processing Error",
                "detail": str(e),
                "status_code": 500
            }
        ) 