from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from services.test_code_generator_service import TestCodeGeneratorService
import os
import logging
from dotenv import load_dotenv

load_dotenv('config.env')

router = APIRouter()

class TestCaseRequest(BaseModel):
    url: str
    title: str
    description: str
    test_type: str
    element_type: str
    test_steps: List[str]
    expected_behavior: str
    html_chunk: str

class TestCasesRequest(BaseModel):
    test_cases: List[TestCaseRequest]

class TestCodeResponse(BaseModel):
    test_code: str
    filename: str
    status: str

class TestCodesResponse(BaseModel):
    results: List[TestCodeResponse]

@router.post("/generate-test-code", response_model=TestCodesResponse)
async def generate_test_code(request: TestCasesRequest):
    try:
        logging.info(f"Generating test code for {len(request.test_cases)} test cases")
        
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
        
        service = TestCodeGeneratorService(api_key)
        results = []
        
        for test_case in request.test_cases:
            test_case_dict = {
                "url": test_case.url,
                "title": test_case.title,
                "description": test_case.description,
                "test_type": test_case.test_type,
                "element_type": test_case.element_type,
                "test_steps": test_case.test_steps,
                "expected_behavior": test_case.expected_behavior,
                "html_chunk": test_case.html_chunk
            }
            
            result = service.generate_test_code(test_case_dict)
            results.append(TestCodeResponse(**result))
        
        logging.info(f"Test code generated successfully for {len(results)} test cases")
        return TestCodesResponse(results=results)
    
    except Exception as e:
        logging.error(f"Error generating test code: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Test Code Generation Error",
                "detail": str(e),
                "status_code": 500
            }
        )
