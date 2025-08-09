from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from services.test_executor_service import TestExecutorService
import logging

router = APIRouter()

class TestExecutionRequest(BaseModel):
    test_code: str
    title: str
    description: str
    url: str

class TestExecutionsRequest(BaseModel):
    test_cases: List[TestExecutionRequest]

class TestExecutionResult(BaseModel):
    test_case_id: int
    title: str
    status: str
    output: str
    error: str
    execution_time: float

class TestExecutionsResponse(BaseModel):
    results: List[TestExecutionResult]
    summary: dict

@router.post("/execute-tests", response_model=TestExecutionsResponse)
async def execute_tests(request: TestExecutionsRequest):
    try:
        logging.info(f"Executing {len(request.test_cases)} test cases")
        
        service = TestExecutorService()
        
        # Convert request to dict format
        test_cases = []
        for test_case in request.test_cases:
            test_cases.append({
                'test_code': test_case.test_code,
                'title': test_case.title,
                'description': test_case.description,
                'url': test_case.url
            })
        
        # Execute tests
        results = await service.execute_tests(test_cases)
        
        # Calculate summary
        passed = sum(1 for r in results if r['status'] == 'passed')
        failed = sum(1 for r in results if r['status'] == 'failed')
        errors = sum(1 for r in results if r['status'] == 'error')
        total_time = sum(r['execution_time'] for r in results)
        
        summary = {
            'total': len(results),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'total_execution_time': round(total_time, 2)
        }
        
        logging.info(f"Test execution completed: {summary}")
        
        return TestExecutionsResponse(
            results=[TestExecutionResult(**result) for result in results],
            summary=summary
        )
        
    except Exception as e:
        logging.error(f"Error executing tests: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Test Execution Error",
                "detail": str(e),
                "status_code": 500
            }
        )
