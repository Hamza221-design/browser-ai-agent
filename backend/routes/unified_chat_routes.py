from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.unified_chat_service import UnifiedChatService
import os
import logging
import uuid

router = APIRouter()

# Global service instance to maintain session state across requests
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
    session_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    user_response: str
    action_results: List[Dict]
    session_state: Dict
    session_id: str

class SessionInfoResponse(BaseModel):
    session_id: str
    current_url: Optional[str]
    test_cases_count: int
    has_generated_code: bool
    has_execution_results: bool
    last_action: Optional[str]
    context: str
    created_at: Optional[str]
    last_active: Optional[str]
    message_count: int

class ClearSessionResponse(BaseModel):
    status: str
    session_cleared: bool

class SessionsListResponse(BaseModel):
    sessions: List[SessionInfoResponse]
    total_count: int

# Future endpoints for user management (commented for later implementation):
# @router.get("/users/{user_id}/chats", response_model=SessionsListResponse)
# @router.get("/users/{user_id}/chats/{chat_id}", response_model=SessionInfoResponse)
# @router.delete("/users/{user_id}/chats/{chat_id}", response_model=ClearSessionResponse)
# @router.post("/users/{user_id}/chats", response_model=ChatMessageResponse)

@router.get("/sessions", response_model=SessionsListResponse)
async def list_sessions():
    try:
        logging.info("Listing all active sessions")
        
        # Get global service instance
        service = get_service()
        sessions = service.session_manager.list_sessions()
        
        return SessionsListResponse(
            sessions=[SessionInfoResponse(**session) for session in sessions],
            total_count=len(sessions)
        )
        
    except Exception as e:
        logging.error(f"Error listing sessions: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Session List Error",
                "detail": str(e),
                "status_code": 500
            }
        )

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
        
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        logging.info(f"Using session ID: {session_id} (provided: {request.session_id is not None})")
        
        # Get global service instance (maintains session state across requests)
        service = get_service()
        
        # Process message
        result = await service.process_message(session_id, request.message)
        
        # Add session ID to response
        result["session_id"] = session_id
        
        logging.info(f"Chat message processed successfully for session: {session_id}")
        
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

@router.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    try:
        logging.info(f"Getting session info for: {session_id}")
        
        # Get global service instance
        service = get_service()
        session_info = service.get_session_info(session_id)
        
        return SessionInfoResponse(**session_info)
        
    except Exception as e:
        logging.error(f"Error getting session info: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Session Info Error",
                "detail": str(e),
                "status_code": 500
            }
        )

@router.delete("/sessions/{session_id}", response_model=ClearSessionResponse)
async def clear_session(session_id: str):
    try:
        logging.info(f"Clearing session: {session_id}")
        
        # Get global service instance
        service = get_service()
        result = service.clear_session(session_id)
        
        return ClearSessionResponse(**result)
        
    except Exception as e:
        logging.error(f"Error clearing session: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Clear Session Error",
                "detail": str(e),
                "status_code": 500
            }
        )

@router.post("/sessions/{session_id}/reset", response_model=ClearSessionResponse)
async def reset_session(session_id: str):
    try:
        logging.info(f"Resetting session: {session_id}")
        
        # Get global service instance
        service = get_service()
        
        # Clear the session
        result = service.clear_session(session_id)
        
        # Create a new session with the same ID
        service.session_manager.get_or_create_session(session_id)
        
        return ClearSessionResponse(**result)
        
    except Exception as e:
        logging.error(f"Error resetting session: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Session Reset Error",
                "detail": str(e),
                "status_code": 500
            }
        ) 