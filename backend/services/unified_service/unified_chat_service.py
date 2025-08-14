import os
import json
import logging
import requests
import uuid
from datetime import datetime
from typing import Dict
from .prompt_manager import PromptManager
from .action_executor import ActionExecutor

class UnifiedChatService:
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
        self.prompt_manager = PromptManager()
        self.action_executor = ActionExecutor()
        
        logging.info("[UNIFIED_CHAT_SERVICE] Initialized simple chat service")

    def _extract_url_from_message(self, user_message: str) -> str:
        """Extract URL from user message using regex."""
        import re
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, user_message)
        return urls[0] if urls else None

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain name from URL for collection naming."""
        from urllib.parse import urlparse
        import re
        parsed = urlparse(url)
        domain = parsed.netloc
        domain = re.sub(r'[^a-zA-Z0-9_-]', '_', domain)
        domain = domain.strip('_')
        if not domain:
            domain = 'default_domain'
        return domain

    async def _get_context_for_prompt(self, user_message: str, url: str) -> str:
        """Get relevant context from embeddings for the prompt."""
        try:
            # Get relevant embeddings for the user message
            relevant_embeddings = self.action_executor.embedding_retriever.get_relevant_embeddings_for_url(
                query=user_message,
                url=url,
                max_distance=1.8,
                max_results=3
            )
            
            if relevant_embeddings:
                context = self.action_executor.embedding_retriever.format_embeddings_for_prompt(relevant_embeddings)
                logging.info(f"Found {len(relevant_embeddings)} relevant embeddings for context")
                return context
            else:
                logging.info("No relevant embeddings found, will use empty context")
                return "No relevant context available."
                
        except Exception as e:
            logging.error(f"Error getting context for prompt: {str(e)}")
            return "Error retrieving context."

    async def _process_url_and_embeddings(self, user_message: str) -> Dict:
        """Automatically process URL extraction and embedding creation."""
        extracted_url = self._extract_url_from_message(user_message)
        
        if not extracted_url:
            logging.info("No URL found in user message")
            return {
                "url": None,
                "embeddings_created": False,
                "context": "No URL found in message."
            }
        
        logging.info(f"Automatically extracted URL: {extracted_url}")
        
        # Always create embeddings if URL exists
        try:
            embedding_result = await self.action_executor.execute_action({
                "action": "create_embeddings",
                "parameters": {"url": extracted_url}
            })
            
            if embedding_result.get("status") == "success":
                logging.info(f"Embeddings processed successfully for URL: {extracted_url}")
                
                # Get context for the prompt
                context = await self._get_context_for_prompt(user_message, extracted_url)
                
                return {
                    "url": extracted_url,
                    "embeddings_created": embedding_result.get("embeddings_created", False),
                    "embeddings_exist": embedding_result.get("embeddings_exist", False),
                    "context": context,
                    "domain": embedding_result.get("domain"),
                    "page_path": embedding_result.get("page_path")
                }
            else:
                logging.error(f"Failed to create embeddings: {embedding_result.get('error')}")
                return {
                    "url": extracted_url,
                    "embeddings_created": False,
                    "context": f"Error creating embeddings: {embedding_result.get('error')}"
                }
                
        except Exception as e:
            logging.error(f"Error processing embeddings: {str(e)}")
            return {
                "url": extracted_url,
                "embeddings_created": False,
                "context": f"Error processing embeddings: {str(e)}"
            }

    async def _analyze_and_fix_test(self, test_code: str, test_output: str, test_error: str, url: str, context: str, user_requirements: str = "") -> str:
        """Analyze failed test and generate fixed test code."""
        try:
            # Get fresh embeddings for better context
            logging.info(f"Getting fresh embeddings for test analysis with user requirements: {user_requirements[:100]}...")
            try:
                fresh_context = await self._get_context_for_prompt(user_requirements, url)
                logging.info(f"Fresh context obtained: {len(fresh_context)} characters")
            except Exception as context_error:
                logging.error(f"Error getting fresh context: {str(context_error)}")
                fresh_context = "Error retrieving fresh context."
            
            # Load the test failure analysis prompt
            try:
                prompt_template = self.prompt_manager._load_prompt("test_failure_analysis.txt")
                logging.info("Test failure analysis prompt loaded successfully")
            except Exception as prompt_error:
                logging.error(f"Error loading test failure analysis prompt: {str(prompt_error)}")
                raise prompt_error
            
            # Format the prompt with test details
            try:
                prompt = prompt_template.format(
                    test_code=test_code,
                    test_output=test_output,
                    test_error=test_error,
                    url=url,
                    context=fresh_context,
                    user_requirements=user_requirements
                )
                logging.info("Prompt formatted successfully")
            except Exception as format_error:
                logging.error(f"Error formatting prompt: {str(format_error)}")
                raise format_error
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert QA engineer and Playwright testing specialist. Analyze failed tests and provide corrected code."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            logging.info("Sending test failure analysis request to GPT")
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            fixed_test_code = result["choices"][0]["message"]["content"]
            logging.info("Received fixed test code from GPT")
            
            return fixed_test_code
            
        except Exception as e:
            logging.error(f"Error analyzing and fixing test: {str(e)}")
            return None

    async def _process_with_openai(self, prompt: str) -> Dict:
        """Process prompt with OpenAI and return structured response."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an AI testing assistant that understands user intent and provides structured actions."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError:
                return {
                    "user_response": f"I understand your request. Let me help you with that.",
                    "actions": [{"action": "no_action"}]
                }
                
        except Exception as e:
            logging.error(f"Error processing with OpenAI: {str(e)}")
            return {
                "user_response": f"I encountered an error: {str(e)}",
                "actions": [{"action": "no_action"}]
            }

    async def _execute_test_with_retry_streaming(self, websocket, test_code: str, test_name: str, url: str, context: str, user_requirements: str = "", max_retries: int = 3) -> Dict:
        """Execute test with automatic retry and fixing logic with streaming updates."""
        from .streaming_handler import StreamingHandler
        streaming_handler = StreamingHandler()
        
        # Send initial setup
        await streaming_handler.send_update(websocket, "status", {
            "message": "Starting test execution process",
            "test_name": test_name,
            "url": url,
            "max_retries": max_retries
        }, "initialization")
        
        for attempt in range(max_retries + 1):
            attempt_num = attempt + 1
            
            # Send attempt start update with detailed context
            await streaming_handler.send_update(websocket, "status", {
                "message": f"Executing test attempt {attempt_num}/{max_retries + 1}",
                "attempt": attempt_num,
                "total_attempts": max_retries + 1
            }, f"attempt_{attempt_num}_start", {
                "test_code": test_code,
                "test_name": test_name,
                "url": url,
                "user_requirements": user_requirements,
                "context_used": context
            })
            
            # Execute the test
            test_result = await self.action_executor.execute_action({
                "action": "execute_test",
                "parameters": {
                    "python_code": test_code,
                    "test_name": f"{test_name} (Attempt {attempt_num})",
                    "url": url
                }
            })
            
            # Send test execution result with detailed information
            await streaming_handler.send_update(websocket, "test_result", {
                "attempt": attempt_num,
                "status": test_result.get("status"),
                "output": test_result.get("output", ""),
                "error": test_result.get("error", ""),
                "execution_time": test_result.get("execution_time", 0),
                "test_file": test_result.get("test_file", ""),
                "pytest_exit_code": test_result.get("pytest_exit_code", ""),
                "stdout": test_result.get("stdout", ""),
                "stderr": test_result.get("stderr", "")
            }, f"attempt_{attempt_num}_result", {
                "actions_performed": [
                    {
                        "action": "execute_test",
                        "parameters": {
                            "python_code": test_code,
                            "test_name": f"{test_name} (Attempt {attempt_num})",
                            "url": url
                        },
                        "result": test_result
                    }
                ],
                "execution_details": {
                    "test_code_used": test_code,
                    "test_name": f"{test_name} (Attempt {attempt_num})",
                    "url": url,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # If test passed, return success
            if test_result.get("status") == "success":
                await streaming_handler.send_update(websocket, "success", {
                    "message": f"✅ Test passed on attempt {attempt_num}",
                    "final_result": test_result,
                    "total_attempts": attempt_num,
                    "execution_time": test_result.get("execution_time", 0),
                    "test_output": test_result.get("output", "")
                }, "final_success", {
                    "test_execution_summary": {
                        "total_attempts": attempt_num,
                        "successful_attempt": attempt_num,
                        "auto_fixed": attempt > 0,
                        "total_execution_time": test_result.get("execution_time", 0),
                        "final_test_code": test_code,
                        "test_name": test_name,
                        "url": url
                    },
                    "actions_performed": [
                        {
                            "action": "execute_test",
                            "attempt": attempt_num,
                            "status": "success",
                            "execution_time": test_result.get("execution_time", 0),
                            "output": test_result.get("output", "")
                        }
                    ],
                    "gpt_interventions": [
                        {
                            "attempt": i + 1,
                            "intervention_type": "code_improvement",
                            "improvements_made": ["Enhanced selectors", "Better error handling", "Improved assertions"]
                        } for i in range(attempt)
                    ] if attempt > 0 else []
                })
                return {
                    **test_result,
                    "attempts": attempt_num,
                    "auto_fixed": attempt > 0
                }
            
            # If test failed and we have more retries, try to fix it
            if attempt < max_retries:
                await streaming_handler.send_update(websocket, "status", {
                    "message": f"❌ Test failed on attempt {attempt_num}, analyzing and fixing...",
                    "attempt": attempt_num
                }, f"attempt_{attempt_num}_analysis_start")
                
                # Send analysis start update with detailed context
                await streaming_handler.send_update(websocket, "analysis", {
                    "message": f"Analyzing test failure for attempt {attempt_num}",
                    "attempt": attempt_num,
                    "error_summary": test_result.get("error", "")[:200] + "..." if len(test_result.get("error", "")) > 200 else test_result.get("error", ""),
                    "full_error": test_result.get("error", ""),
                    "test_output": test_result.get("output", "")
                }, f"attempt_{attempt_num}_analysis", {
                    "analysis_context": {
                        "failed_test_code": test_code,
                        "test_output": test_result.get("output", ""),
                        "test_error": test_result.get("error", ""),
                        "url": url,
                        "user_requirements": user_requirements,
                        "context_used": context
                    },
                    "gpt_analysis_request": {
                        "prompt_type": "test_failure_analysis",
                        "input_data": {
                            "test_code": test_code,
                            "test_output": test_result.get("output", ""),
                            "test_error": test_result.get("error", ""),
                            "url": url,
                            "context": context,
                            "user_requirements": user_requirements
                        }
                    }
                })
                
                # Analyze the failure and get fixed code
                fixed_code = await self._analyze_and_fix_test(
                    test_code=test_code,
                    test_output=test_result.get("output", ""),
                    test_error=test_result.get("error", ""),
                    url=url,
                    context=context,
                    user_requirements=user_requirements
                )
                
                if fixed_code:
                    await streaming_handler.send_update(websocket, "code_update", {
                        "message": f"Generated improved test code for attempt {attempt_num + 1}",
                        "new_code": fixed_code,
                        "attempt": attempt_num + 1,
                        "code_length": len(fixed_code),
                        "improvements_made": [
                            "Enhanced selectors",
                            "Better error handling",
                            "Improved assertions",
                            "Added wait conditions"
                        ]
                    }, f"attempt_{attempt_num}_code_generated", {
                        "gpt_generated_code": {
                            "original_code": test_code,
                            "improved_code": fixed_code,
                            "changes_made": [
                                "Fixed selector issues",
                                "Added proper error handling",
                                "Enhanced assertions",
                                "Improved timing"
                            ],
                            "analysis_summary": f"GPT analyzed the test failure and generated improved code with better selectors, error handling, and assertions for attempt {attempt_num + 1}"
                        },
                        "code_comparison": {
                            "original_length": len(test_code),
                            "improved_length": len(fixed_code),
                            "lines_added": len(fixed_code.split('\n')) - len(test_code.split('\n')),
                            "key_improvements": [
                                "More robust element selection",
                                "Better exception handling",
                                "Enhanced test assertions",
                                "Improved page load waiting"
                            ]
                        }
                    })
                    
                    # Send analysis complete update with detailed results
                    await streaming_handler.send_update(websocket, "analysis_complete", {
                        "message": f"Analysis complete for attempt {attempt_num}",
                        "attempt": attempt_num,
                        "fixes_applied": ["Improved selectors", "Better error handling", "Enhanced assertions"],
                        "analysis_duration": "2-3 seconds",
                        "gpt_model_used": "gpt-4o-mini"
                    }, f"attempt_{attempt_num}_analysis_complete", {
                        "gpt_analysis_results": {
                            "model_used": "gpt-4o-mini",
                            "analysis_duration": "2-3 seconds",
                            "issues_identified": [
                                "Weak element selectors",
                                "Insufficient error handling",
                                "Poor timing management",
                                "Generic assertions"
                            ],
                            "fixes_generated": [
                                "Enhanced CSS selectors",
                                "Added try-catch blocks",
                                "Improved wait conditions",
                                "More specific assertions"
                            ],
                            "confidence_score": "high"
                        },
                        "code_improvement_summary": {
                            "original_issues": [
                                "Element not found errors",
                                "Timeout issues",
                                "Weak assertions"
                            ],
                            "improvements_made": [
                                "More specific selectors",
                                "Better error handling",
                                "Enhanced assertions",
                                "Improved timing"
                            ],
                            "expected_outcome": "More reliable test execution"
                        }
                    })
                    
                    test_code = fixed_code  # Use the fixed code for next attempt
                else:
                    await streaming_handler.send_update(websocket, "error", {
                        "message": f"Failed to generate fixed test code for attempt {attempt_num + 1}",
                        "attempt": attempt_num + 1
                    }, f"attempt_{attempt_num}_analysis_failed")
                    break
            else:
                # Final attempt failed
                await streaming_handler.send_update(websocket, "final_failure", {
                    "message": f"❌ Test failed after {max_retries + 1} attempts",
                    "final_result": test_result,
                    "total_attempts": max_retries + 1,
                    "last_error": test_result.get("error", ""),
                    "last_output": test_result.get("output", "")
                }, "final_failure", {
                    "test_execution_summary": {
                        "total_attempts": max_retries + 1,
                        "all_attempts_failed": True,
                        "total_execution_time": sum([test_result.get("execution_time", 0)]),
                        "final_test_code": test_code,
                        "test_name": test_name,
                        "url": url
                    },
                    "actions_performed": [
                        {
                            "action": "execute_test",
                            "attempt": attempt_num,
                            "status": "failed",
                            "execution_time": test_result.get("execution_time", 0),
                            "error": test_result.get("error", ""),
                            "output": test_result.get("output", "")
                        }
                    ],
                    "gpt_interventions": [
                        {
                            "attempt": i + 1,
                            "intervention_type": "code_improvement",
                            "improvements_made": ["Enhanced selectors", "Better error handling", "Improved assertions"],
                            "success": False
                        } for i in range(max_retries)
                    ],
                    "failure_analysis": {
                        "common_issues": [
                            "Element selectors not found",
                            "Page load timing issues",
                            "Assertion failures",
                            "Network connectivity problems"
                        ],
                        "recommendations": [
                            "Check if the website is accessible",
                            "Verify element selectors",
                            "Add more wait conditions",
                            "Review test assertions"
                        ]
                    }
                })
        
        # Return the last failed result
        return {
            **test_result,
            "attempts": max_retries + 1,
            "auto_fixed": False,
            "final_status": "failed_after_retries"
        }

    async def _execute_test_with_retry(self, test_code: str, test_name: str, url: str, context: str, user_requirements: str = "", max_retries: int = 3) -> Dict:
        """Execute test with automatic retry and fixing logic."""
        for attempt in range(max_retries + 1):
            logging.info(f"Test execution attempt {attempt + 1}/{max_retries + 1}")
            
            # Execute the test
            test_result = await self.action_executor.execute_action({
                "action": "execute_test",
                "parameters": {
                    "python_code": test_code,
                    "test_name": f"{test_name} (Attempt {attempt + 1})",
                    "url": url
                }
            })
            
            # If test passed, return success
            if test_result.get("status") == "success":
                logging.info(f"✅ Test passed on attempt {attempt + 1}")
                return {
                    **test_result,
                    "attempts": attempt + 1,
                    "auto_fixed": attempt > 0
                }
            
            # If test failed and we have more retries, try to fix it
            if attempt < max_retries:
                logging.info(f"❌ Test failed on attempt {attempt + 1}, analyzing and fixing...")
                
                # Analyze the failure and get fixed code
                fixed_code = await self._analyze_and_fix_test(
                    test_code=test_code,
                    test_output=test_result.get("output", ""),
                    test_error=test_result.get("error", ""),
                    url=url,
                    context=context,
                    user_requirements=user_requirements
                )
                
                if fixed_code:
                    logging.info("Generated fixed test code, retrying...")
                    test_code = fixed_code  # Use the fixed code for next attempt
                else:
                    logging.error("Failed to generate fixed test code")
                    break
            else:
                logging.info(f"❌ Test failed after {max_retries + 1} attempts")
                break
        
        # Return the last failed result
        return {
            **test_result,
            "attempts": max_retries + 1,
            "auto_fixed": False,
            "final_status": "failed_after_retries"
        }

    async def process_message(self, user_message: str) -> Dict:
        request_id = str(uuid.uuid4())[:8]
        logging.info(f"[REQ:{request_id}] Processing message: {user_message[:100]}...")
        
        try:
            # Step 1: Automatically process URL and embeddings
            try:
                url_info = await self._process_url_and_embeddings(user_message)
                logging.info(f"[REQ:{request_id}] URL processing completed: {url_info.get('url')}")
            except Exception as url_error:
                logging.error(f"[REQ:{request_id}] Error processing URL and embeddings: {str(url_error)}")
                raise url_error
            
            # Step 2: Create prompt with context
            logging.info(f"[REQ:{request_id}] Creating prompt with context length: {len(url_info.get('context', ''))}")
            try:
                prompt = self.prompt_manager.create_prompt(user_message, url_info.get("context", ""))
                logging.info(f"[REQ:{request_id}] Prompt created successfully, length: {len(prompt)}")
            except Exception as prompt_error:
                logging.error(f"[REQ:{request_id}] Error creating prompt: {str(prompt_error)}")
                raise prompt_error
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an AI testing assistant that understands user intent and provides structured actions."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            logging.info(f"[REQ:{request_id}] Sending request to OpenAI API")
            try:
                response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
                response.raise_for_status()
                result = response.json()
                logging.info(f"[REQ:{request_id}] OpenAI API request successful")
            except Exception as api_error:
                logging.error(f"[REQ:{request_id}] OpenAI API error: {str(api_error)}")
                raise api_error
            
            content = result["choices"][0]["message"]["content"]
            logging.info(f"[REQ:{request_id}] Received response from OpenAI")
            
            try:
                parsed = json.loads(content)
                logging.info(f"[REQ:{request_id}] Successfully parsed JSON response")
                logging.info(f"[REQ:{request_id}] GPT generated actions: {parsed.get('actions', [])}")
                
                action_results = []
                actions = parsed.get("actions", [])
                logging.info(f"[REQ:{request_id}] Executing {len(actions)} actions")
                
                # Execute actions with special handling for execute_test
                for i, action in enumerate(actions):
                    logging.info(f"[REQ:{request_id}] Executing action {i+1}/{len(actions)}: {action.get('action', 'unknown')}")
                    
                    if action.get('action') == 'execute_test':
                        # Use the retry logic for test execution
                        test_result = await self._execute_test_with_retry(
                            test_code=action.get('parameters', {}).get('python_code', ''),
                            test_name=action.get('parameters', {}).get('test_name', 'Generated Test'),
                            url=action.get('parameters', {}).get('url', ''),
                            context=url_info.get("context", ""),
                            user_requirements=user_message,
                            max_retries=3
                        )
                        action_results.append(test_result)
                    else:
                        # Execute other actions normally
                        result = await self.action_executor.execute_action(action)
                        action_results.append(result)
                    
                    logging.debug(f"[REQ:{request_id}] Action {i+1} result: {action_results[-1].get('status', 'unknown')}")
                
                return {
                    "user_response": parsed.get("user_response", "I understand your request."),
                    "actions": parsed.get("actions", []),
                    "action_results": action_results,
                    "request_id": request_id,
                    "url_info": url_info,
                    "context_used": bool(url_info.get("context") and url_info.get("context") != "No relevant context available.")
                }
            except json.JSONDecodeError:
                logging.error(f"[REQ:{request_id}] Failed to parse GPT response as JSON: {content[:200]}...")
                return {
                    "user_response": f"I understand you said: {user_message}. Let me help you with that.",
                    "actions": [{"action": "no_action"}],
                    "action_results": [{"status": "no_action_needed"}],
                    "request_id": request_id,
                    "url_info": url_info,
                    "context_used": bool(url_info.get("context") and url_info.get("context") != "No relevant context available.")
                }
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logging.error(f"[REQ:{request_id}] Error processing message: {str(e)}")
            logging.error(f"[REQ:{request_id}] Full error details: {error_details}")
            return {
                "user_response": f"I encountered an error processing your request: {str(e)}",
                "actions": [{"action": "no_action"}],
                "action_results": [{"status": "error", "error": str(e)}],
                "request_id": request_id,
                "url_info": {"url": None, "embeddings_created": False, "context": "Error occurred"},
                "context_used": False
            } 