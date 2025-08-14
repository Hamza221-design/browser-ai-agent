from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
import json
import asyncio
import logging
from typing import Dict, List
from services.unified_service.streaming_handler import StreamingHandler
from services.unified_service.unified_chat_service import UnifiedChatService
import os

router = APIRouter()
streaming_handler = StreamingHandler()

# Store active connections
active_connections: List[WebSocket] = []

@router.get("/test")
async def test_endpoint():
    return {"message": "Streaming routes are working!"}

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logging.info("WebSocket client connected")
    
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected to AI Testing Assistant",
            "timestamp": "2024-01-01T00:00:00Z"
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logging.info(f"Received WebSocket message: {data}")
            message = json.loads(data)
            
            # Process the message
            await process_streaming_message(websocket, message)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logging.info("WebSocket client disconnected")
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        if websocket in active_connections:
            active_connections.remove(websocket)

async def process_streaming_message(websocket: WebSocket, message: Dict):
    """Process incoming WebSocket messages and stream responses."""
    
    message_type = message.get("type", "chat")
    user_message = message.get("message", "")
    
    if message_type == "chat":
        await handle_chat_message(websocket, user_message)
    elif message_type == "test_execution":
        await handle_test_execution(websocket, message)
    else:
        await streaming_handler.send_update(websocket, "error", {
            "message": f"Unknown message type: {message_type}"
        }, "unknown_type")

async def handle_chat_message(websocket: WebSocket, user_message: str):
    """Handle regular chat messages with streaming."""
    
    # Initialize chat service
    chat_service = UnifiedChatService(os.getenv("OPENAI_API_KEY"))
    
    try:
        # Send initial response
        await streaming_handler.send_update(websocket, "status", {
            "message": "Processing your request...",
            "user_message": user_message
        }, "processing_start")
        
        # Process URL and embeddings
        await streaming_handler.send_update(websocket, "status", {
            "message": "Extracting URL and creating embeddings..."
        }, "url_processing")
        
        url_info = await chat_service._process_url_and_embeddings(user_message)
        
        await streaming_handler.send_update(websocket, "url_info", {
            "url": url_info.get("url"),
            "embeddings_created": url_info.get("embeddings_created"),
            "context_length": len(url_info.get("context", ""))
        }, "url_processed")
        
        # Create prompt
        await streaming_handler.send_update(websocket, "status", {
            "message": "Creating AI prompt..."
        }, "prompt_creation")
        
        prompt = chat_service.prompt_manager.create_prompt(user_message, url_info.get("context", ""))
        
        # Send to OpenAI
        await streaming_handler.send_update(websocket, "status", {
            "message": "Sending request to AI..."
        }, "ai_request")
        
        # Process with OpenAI (simplified for now)
        response = await chat_service._process_with_openai(prompt)
        
        await streaming_handler.send_update(websocket, "ai_response", {
            "response": response.get("user_response", ""),
            "actions_count": len(response.get("actions", []))
        }, "ai_processed")
        
        # Execute actions with streaming
        actions = response.get("actions", [])
        action_results = []
        
        for i, action in enumerate(actions):
            await streaming_handler.send_update(websocket, "action_start", {
                "action": action.get("action"),
                "action_number": i + 1,
                "total_actions": len(actions)
            }, f"action_{i+1}_start")
            
            if action.get("action") == "execute_test":
                # Stream test execution
                test_result = await stream_test_execution(
                    websocket, 
                    action.get("parameters", {}).get("python_code", ""),
                    action.get("parameters", {}).get("test_name", "Test"),
                    action.get("parameters", {}).get("url", ""),
                    url_info.get("context", ""),
                    user_message
                )
                action_results.append(test_result)
            else:
                # Execute other actions
                result = await chat_service.action_executor.execute_action(action)
                action_results.append(result)
                
                await streaming_handler.send_update(websocket, "action_complete", {
                    "action": action.get("action"),
                    "result": result
                }, f"action_{i+1}_complete")
        
        # Send final response
        await streaming_handler.send_update(websocket, "final_response", {
            "user_response": response.get("user_response", ""),
            "actions": actions,
            "action_results": action_results,
            "url_info": url_info
        }, "final_response")
        
    except Exception as e:
        await streaming_handler.send_update(websocket, "error", {
            "message": f"Error processing message: {str(e)}"
        }, "processing_error")

async def handle_test_execution(websocket: WebSocket, message: Dict):
    """Handle dedicated test execution requests."""
    
    test_code = message.get("test_code", "")
    test_name = message.get("test_name", "Test")
    url = message.get("url", "")
    user_requirements = message.get("user_requirements", "")
    
    await stream_test_execution(websocket, test_code, test_name, url, "", user_requirements)

async def stream_test_execution(websocket: WebSocket, test_code: str, test_name: str, 
                              url: str, context: str, user_requirements: str):
    """Stream test execution with real-time updates."""
    
    # Initialize chat service for test execution
    chat_service = UnifiedChatService(os.getenv("OPENAI_API_KEY"))
    
    # Use the existing _execute_test_with_retry but with streaming updates
    return await chat_service._execute_test_with_retry_streaming(
        websocket, test_code, test_name, url, context, user_requirements
    ) 