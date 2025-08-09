from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from services.chat_analyzer_service import ChatAnalyzerService
from services.test_code_generator_service import TestCodeGeneratorService
import os
import logging
from dotenv import load_dotenv

load_dotenv('config.env')

router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str

class ChatAnalysisResponse(BaseModel):
    url: Optional[str] = None
    requirements: Optional[str] = None
    test_cases: Optional[List[dict]] = None
    total_cases: Optional[int] = None
    element_counts: Optional[dict] = None
    message: str
    error: Optional[str] = None

class GenerateCodeRequest(BaseModel):
    test_cases: List[dict]
    url: str

class GenerateCodeResponse(BaseModel):
    results: List[dict]

@router.post("/chat-analyze", response_model=ChatAnalysisResponse)
async def chat_analyze(request: ChatMessageRequest):
    try:
        logging.info(f"Processing chat message: {request.message}")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.error("OpenAI API key not configured")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Configuration Error",
                    "message": "OpenAI API key not configured"
                }
            )
        
        service = ChatAnalyzerService(api_key)
        result = await service.process_chat_message(request.message)
        
        if "error" in result:
            return ChatAnalysisResponse(**result)
        
        logging.info(f"Chat analysis completed: {result['total_cases']} test cases generated")
        return ChatAnalysisResponse(**result)
    
    except Exception as e:
        logging.error(f"Error in chat analysis: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Chat Analysis Error",
                "message": str(e)
            }
        )

@router.post("/chat-generate-code", response_model=GenerateCodeResponse)
async def chat_generate_code(request: GenerateCodeRequest):
    try:
        logging.info(f"Generating code for {len(request.test_cases)} test cases from chat")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.error("OpenAI API key not configured")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Configuration Error",
                    "message": "OpenAI API key not configured"
                }
            )
        
        service = TestCodeGeneratorService(api_key)
        results = []
        
        for test_case in request.test_cases:
            # Add URL to test case if not present
            if 'url' not in test_case:
                test_case['url'] = request.url
                
            result = service.generate_test_code(test_case)
            results.append(result)
        
        logging.info(f"Code generation completed for {len(results)} test cases")
        return GenerateCodeResponse(results=results)
    
    except Exception as e:
        logging.error(f"Error generating code from chat: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Code Generation Error",
                "message": str(e)
            }
        )
