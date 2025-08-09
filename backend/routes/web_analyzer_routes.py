from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from services.web_analyzer_service import WebAnalyzerService
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

router = APIRouter()

# Get default values from environment
DEFAULT_EXTRACT_ELEMENTS = os.getenv('DEFAULT_EXTRACT_ELEMENTS', 'forms,links').split(',')
DEFAULT_TEST_TYPES = os.getenv('DEFAULT_TEST_TYPES', 'functional,validation,negative,positive,error_handling').split(',')
DEFAULT_CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 2000))

class WebAnalysisRequest(BaseModel):
    url: str
    extract_elements: Optional[List[str]] = DEFAULT_EXTRACT_ELEMENTS
    test_types: Optional[List[str]] = DEFAULT_TEST_TYPES
    chunk_size: Optional[int] = DEFAULT_CHUNK_SIZE

class WebAnalysisResponse(BaseModel):
    url: str
    test_cases: List[dict]
    total_cases: int
    element_counts: dict
    
    class Config:
        extra = "allow"

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int

@router.post("/analyze", response_model=WebAnalysisResponse)
async def analyze_web_page(request: WebAnalysisRequest):
    try:
        logging.info(f"Starting analysis for URL: {request.url}")
        
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
        
        service = WebAnalyzerService(api_key)
        result = await service.analyze_url_with_config(
            url=request.url,
            extract_elements=request.extract_elements,
            test_types=request.test_types,
            chunk_size=request.chunk_size
        )
        
        logging.info(f"Analysis completed for URL: {request.url}, generated {result['total_cases']} test cases")
        if result['test_cases']:
            logging.debug(f"First test case keys: {list(result['test_cases'][0].keys())}")
        return WebAnalysisResponse(**result)
    
    except Exception as e:
        logging.error(f"Error analyzing URL {request.url}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Analysis Error",
                "detail": str(e),
                "status_code": 500
            }
        )
