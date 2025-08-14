import json
import asyncio
import logging
from typing import Dict, List, Any, Callable
from datetime import datetime

class StreamingHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def send_update(self, websocket, update_type: str, data: Dict, step: str = "", additional_info: Dict = None):
        """Send a streaming update to the client with additional context."""
        try:
            message = {
                "type": update_type,
                "timestamp": datetime.now().isoformat(),
                "step": step,
                "data": data
            }
            
            # Add additional context if provided
            if additional_info:
                message["context"] = additional_info
            
            await websocket.send_text(json.dumps(message))
            self.logger.info(f"Sent {update_type} update: {step}")
            
        except Exception as e:
            self.logger.error(f"Error sending streaming update: {str(e)}")
    
    async def stream_test_execution(self, websocket, test_code: str, test_name: str, url: str, 
                                  context: str, user_requirements: str, max_retries: int = 3):
        """Stream the entire test execution process."""
        
        # Step 1: Initial setup
        await self.send_update(websocket, "status", {
            "message": "Starting test execution process",
            "test_name": test_name,
            "url": url,
            "max_retries": max_retries
        }, "initialization")
        
        # Step 2: Test execution attempts
        for attempt in range(max_retries + 1):
            attempt_num = attempt + 1
            
            # Send attempt start update
            await self.send_update(websocket, "status", {
                "message": f"Executing test attempt {attempt_num}/{max_retries + 1}",
                "attempt": attempt_num,
                "total_attempts": max_retries + 1
            }, f"attempt_{attempt_num}_start")
            
            # Execute test (this would call your existing test executor)
            test_result = await self._execute_test_attempt(test_code, test_name, url, attempt_num)
            
            # Send test execution result
            await self.send_update(websocket, "test_result", {
                "attempt": attempt_num,
                "status": test_result.get("status"),
                "output": test_result.get("output", ""),
                "error": test_result.get("error", ""),
                "execution_time": test_result.get("execution_time", 0)
            }, f"attempt_{attempt_num}_result")
            
            # If test passed, send success and return
            if test_result.get("status") == "success":
                await self.send_update(websocket, "success", {
                    "message": f"Test passed on attempt {attempt_num}",
                    "final_result": test_result,
                    "total_attempts": attempt_num
                }, "final_success")
                return test_result
            
            # If test failed and we have more retries, analyze and fix
            if attempt < max_retries:
                await self.send_update(websocket, "status", {
                    "message": f"Test failed on attempt {attempt_num}, analyzing and generating fix...",
                    "attempt": attempt_num
                }, f"attempt_{attempt_num}_analysis_start")
                
                # Analyze and fix test
                fixed_code = await self._analyze_and_fix_test(
                    test_code, test_result.get("output", ""), test_result.get("error", ""),
                    url, context, user_requirements, websocket, attempt_num
                )
                
                if fixed_code:
                    await self.send_update(websocket, "code_update", {
                        "message": f"Generated improved test code for attempt {attempt_num + 1}",
                        "new_code": fixed_code,
                        "attempt": attempt_num + 1
                    }, f"attempt_{attempt_num}_code_generated")
                    
                    test_code = fixed_code  # Use fixed code for next attempt
                else:
                    await self.send_update(websocket, "error", {
                        "message": f"Failed to generate fixed test code for attempt {attempt_num + 1}",
                        "attempt": attempt_num + 1
                    }, f"attempt_{attempt_num}_analysis_failed")
                    break
            else:
                # Final attempt failed
                await self.send_update(websocket, "final_failure", {
                    "message": f"Test failed after {max_retries + 1} attempts",
                    "final_result": test_result,
                    "total_attempts": max_retries + 1
                }, "final_failure")
        
        return test_result
    
    async def _execute_test_attempt(self, test_code: str, test_name: str, url: str, attempt_num: int) -> Dict:
        """Execute a single test attempt."""
        # This would call your existing test executor service
        # For now, returning a mock result
        return {
            "status": "failed",  # Mock - replace with actual execution
            "output": f"Mock test output for attempt {attempt_num}",
            "error": f"Mock test error for attempt {attempt_num}",
            "execution_time": 5.0
        }
    
    async def _analyze_and_fix_test(self, test_code: str, test_output: str, test_error: str,
                                  url: str, context: str, user_requirements: str,
                                  websocket, attempt_num: int) -> str:
        """Analyze failed test and generate fixed code with streaming updates."""
        
        # Send analysis start update
        await self.send_update(websocket, "analysis", {
            "message": f"Analyzing test failure for attempt {attempt_num}",
            "attempt": attempt_num,
            "error_summary": test_error[:200] + "..." if len(test_error) > 200 else test_error
        }, f"attempt_{attempt_num}_analysis")
        
        # This would call your existing analysis function
        # For now, returning a mock fixed code
        await asyncio.sleep(2)  # Simulate analysis time
        
        fixed_code = f"# Fixed test code for attempt {attempt_num + 1}\n{test_code}"
        
        # Send analysis complete update
        await self.send_update(websocket, "analysis_complete", {
            "message": f"Analysis complete for attempt {attempt_num}",
            "attempt": attempt_num,
            "fixes_applied": ["Improved selectors", "Better error handling"]
        }, f"attempt_{attempt_num}_analysis_complete")
        
        return fixed_code 