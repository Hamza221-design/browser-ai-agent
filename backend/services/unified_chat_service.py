import os
import json
import logging
import asyncio
import requests
import chromadb
import uuid
import traceback
from typing import Dict, List, Optional
from urllib.parse import urlparse
import re
from datetime import datetime

# Import existing services
from .chat_analyzer_service import ChatAnalyzerService
from .test_code_generator_service import TestCodeGeneratorService
from .test_executor_service import TestExecutorService

class ChatMessage:
    def __init__(self, role: str, content: str, timestamp: datetime, actions: List[Dict] = None):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.timestamp = timestamp
        self.actions = actions or []

class ChatSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_url = None
        self.test_cases = []
        self.generated_code = {}
        self.execution_results = {}
        self.embeddings_created = False
        self.last_action = None
        self.context = ""
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.messages = []  # List of ChatMessage objects
        self.execution_trace = []  # Track execution steps for debugging
    
    def add_message(self, role: str, content: str, actions: List[Dict] = None):
        """Add a message to the conversation history"""
        message = ChatMessage(role, content, datetime.now(), actions)
        self.messages.append(message)
        self.last_active = datetime.now()
        
        # Log message addition
        logging.info(f"[SESSION:{self.session_id}] Added {role} message: {content[:100]}...")
        if actions:
            logging.debug(f"[SESSION:{self.session_id}] Message actions: {actions}")
    
    def add_execution_trace(self, step: str, details: Dict = None):
        """Add execution trace step for debugging"""
        trace_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "details": details or {}
        }
        self.execution_trace.append(trace_entry)
        logging.info(f"[SESSION:{self.session_id}] EXECUTION_TRACE: {step}")
        if details:
            logging.debug(f"[SESSION:{self.session_id}] Trace details: {details}")
    
    def get_conversation_context(self, max_messages: int = 10) -> str:
        """Get recent conversation history for GPT context"""
        if not self.messages:
            return ""
        
        recent_messages = self.messages[-max_messages:]
        context = ""
        for msg in recent_messages:
            context += f"{msg.role}: {msg.content}\n"
        return context
    
    def get_session_summary(self) -> Dict:
        """Get a summary of the session state"""
        return {
            "session_id": self.session_id,
            "current_url": self.current_url,
            "test_cases_count": len(self.test_cases),
            "has_generated_code": bool(self.generated_code),
            "has_execution_results": bool(self.execution_results),
            "last_action": self.last_action,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": len(self.messages),
            "execution_trace_count": len(self.execution_trace)
        }

class ChatSessionManager:
    def __init__(self):
        self.sessions = {}
    
    def get_or_create_session(self, session_id: str) -> ChatSession:
        if session_id not in self.sessions:
            logging.info(f"[SESSION_MANAGER] Creating new session: {session_id}")
            self.sessions[session_id] = ChatSession(session_id)
        else:
            logging.debug(f"[SESSION_MANAGER] Using existing session: {session_id}")
        return self.sessions[session_id]
    
    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            logging.info(f"[SESSION_MANAGER] Clearing session: {session_id}")
            del self.sessions[session_id]
        else:
            logging.warning(f"[SESSION_MANAGER] Attempted to clear non-existent session: {session_id}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a specific session"""
        if session_id in self.sessions:
            return self.sessions[session_id].get_session_summary()
        return None
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions (for future user management)"""
        return [
            session.get_session_summary() 
            for session in self.sessions.values()
        ]
    
    # Future endpoints for user management (commented for later implementation):
    # def get_or_create_user_session(self, user_id: str) -> UserSession:
    # def get_or_create_chat_session(self, user_id: str, chat_id: str) -> ChatSession:
    # def get_user_chats(self, user_id: str) -> List[Dict]:

class UnifiedChatService:
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.session_manager = ChatSessionManager()
        
        # Initialize existing services
        logging.info("[UNIFIED_CHAT_SERVICE] Initializing services...")
        self.chat_analyzer = ChatAnalyzerService(openai_api_key)
        self.test_code_generator = TestCodeGeneratorService(openai_api_key)
        self.test_executor = TestExecutorService(openai_api_key)
        
        # Initialize ChromaDB client
        logging.info("[UNIFIED_CHAT_SERVICE] Initializing ChromaDB client...")
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_DB"),
            settings=chromadb.config.Settings(
                anonymized_telemetry=False
            )
        )
        logging.info("[UNIFIED_CHAT_SERVICE] Initialization complete")

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain name from URL for collection naming."""
        logging.debug(f"[UNIFIED_CHAT_SERVICE] Extracting domain from URL: {url}")
        parsed = urlparse(url)
        domain = parsed.netloc
        domain = re.sub(r'[^a-zA-Z0-9_-]', '_', domain)
        domain = domain.strip('_')
        if not domain:
            domain = 'default_domain'
        logging.debug(f"[UNIFIED_CHAT_SERVICE] Extracted domain: {domain}")
        return domain

    def _create_unified_prompt(self, user_message: str, session: ChatSession) -> str:
        """Create prompt for GPT to understand intent and provide actions."""
        conversation_context = session.get_conversation_context()
        
        logging.info(f"[SESSION:{session.session_id}] Creating unified prompt")
        logging.info(f"[SESSION:{session.session_id}] Using conversation context with {len(session.messages)} messages")
        if conversation_context:
            logging.debug(f"[SESSION:{session.session_id}] Conversation context: {conversation_context[:200]}...")
        
        # Add execution trace to prompt context
        trace_context = ""
        if session.execution_trace:
            recent_traces = session.execution_trace[-5:]  # Last 5 execution steps
            trace_context = "\nRecent execution steps:\n"
            for trace in recent_traces:
                trace_context += f"- {trace['step']}: {trace['timestamp']}\n"
        
        return f"""
You are an AI testing assistant. The user has sent a message and you need to:
1. Respond naturally to the user
2. Determine what actions to take

Recent conversation history:
{conversation_context if conversation_context else "No previous conversation."}

Current session context:
- URL: {session.current_url or 'None'}
- Test cases: {len(session.test_cases)}
- Generated code: {len(session.generated_code)}
- Last action: {session.last_action or 'None'}
- Context: {session.context or 'None'}
{trace_context}

User message: {user_message}

Available actions:
- extract_url: Extract URL from message
- create_embeddings: Create embeddings for a URL
- generate_test_cases: Generate test cases
- generate_test_code: Generate test code
- execute_tests: Run tests
- analyze_failure: Analyze test failures
- modify_test: Modify existing tests
- show_results: Show previous results
- clear_session: Reset session
- no_action: Just respond, no action needed

Respond in this JSON format:
{{
    "user_response": "Your natural response to the user",
    "actions": [
        {{
            "action": "action_name",
            "parameters": {{"param": "value"}}
        }}
    ],
    "session_updates": {{
        "current_url": "url_if_changed",
        "context": "updated_context"
    }}
}}

Only include actions that are actually needed. If the user is just chatting or asking questions, use "no_action".
Consider the conversation history when determining the appropriate response and actions.
"""

    async def get_gpt_response_with_actions(self, user_message: str, session: ChatSession) -> Dict:
        """Get GPT response with structured actions."""
        request_id = str(uuid.uuid4())[:8]
        logging.info(f"[SESSION:{session.session_id}][REQ:{request_id}] Starting GPT request")
        
        try:
            session.add_execution_trace("gpt_request_started", {"request_id": request_id})
            
            prompt = self._create_unified_prompt(user_message, session)
            logging.debug(f"[SESSION:{session.session_id}][REQ:{request_id}] Prompt created, length: {len(prompt)}")
            
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
                "temperature": 0.3,
                "max_tokens": 1500
            }
            
            logging.info(f"[SESSION:{session.session_id}][REQ:{request_id}] Sending request to OpenAI API")
            session.add_execution_trace("openai_api_call", {"model": "gpt-4o-mini", "max_tokens": 1500})
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            logging.info(f"[SESSION:{session.session_id}][REQ:{request_id}] Received response from OpenAI, length: {len(content)}")
            
            # Parse JSON response
            try:
                parsed = json.loads(content)
                logging.debug(f"[SESSION:{session.session_id}][REQ:{request_id}] Successfully parsed JSON response")
                session.add_execution_trace("gpt_response_parsed", {"actions_count": len(parsed.get("actions", []))})
                return self._validate_gpt_response(parsed)
            except json.JSONDecodeError:
                logging.error(f"[SESSION:{session.session_id}][REQ:{request_id}] Failed to parse GPT response as JSON: {content[:200]}...")
                session.add_execution_trace("gpt_response_parse_error", {"error": "JSON decode error"})
                return self._get_fallback_response(user_message)
                
        except Exception as e:
            logging.error(f"[SESSION:{session.session_id}][REQ:{request_id}] Error getting GPT response: {str(e)}")
            logging.error(f"[SESSION:{session.session_id}][REQ:{request_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("gpt_request_error", {"error": str(e)})
            return self._get_fallback_response(user_message)

    def _validate_gpt_response(self, response: Dict) -> Dict:
        """Validate and ensure GPT response has required structure."""
        if not isinstance(response, dict):
            return self._get_fallback_response("")
        
        # Ensure required fields exist
        if "user_response" not in response:
            response["user_response"] = "I understand your request."
        
        if "actions" not in response:
            response["actions"] = [{"action": "no_action"}]
        
        if "session_updates" not in response:
            response["session_updates"] = {}
        
        return response

    def _get_fallback_response(self, user_message: str) -> Dict:
        """Get fallback response when GPT fails."""
        return {
            "user_response": f"I understand you said: {user_message}. Let me help you with that.",
            "actions": [{"action": "no_action"}],
            "session_updates": {}
        }

    async def execute_action(self, action: Dict, session: ChatSession) -> Dict:
        """Execute a specific action."""
        action_name = action.get("action", "no_action")
        parameters = action.get("parameters", {})
        action_id = str(uuid.uuid4())[:8]
        
        logging.info(f"[SESSION:{session.session_id}][ACTION:{action_id}] Executing action: {action_name}")
        logging.debug(f"[SESSION:{session.session_id}][ACTION:{action_id}] Action parameters: {parameters}")
        
        session.add_execution_trace("action_started", {
            "action_id": action_id,
            "action_name": action_name,
            "parameters": parameters
        })
        
        try:
            if action_name == "extract_url":
                result = await self._extract_url_action(parameters, session)
            elif action_name == "create_embeddings":
                result = await self._create_embeddings_action(parameters, session)
            elif action_name == "generate_test_cases":
                result = await self._generate_test_cases_action(parameters, session)
            elif action_name == "generate_test_code":
                result = await self._generate_test_code_action(parameters, session)
            elif action_name == "execute_tests":
                result = await self._execute_tests_action(parameters, session)
            elif action_name == "analyze_failure":
                result = await self._analyze_failure_action(parameters, session)
            elif action_name == "modify_test":
                result = await self._modify_test_action(parameters, session)
            elif action_name == "show_results":
                result = await self._show_results_action(parameters, session)
            elif action_name == "clear_session":
                result = await self._clear_session_action(parameters, session)
            elif action_name == "no_action":
                result = {"status": "no_action_needed"}
            else:
                result = {"status": "unknown_action", "action": action_name}
            
            logging.info(f"[SESSION:{session.session_id}][ACTION:{action_id}] Action completed: {action_name}")
            session.add_execution_trace("action_completed", {
                "action_id": action_id,
                "action_name": action_name,
                "result_status": result.get("status", "unknown")
            })
            
            return result
                
        except Exception as e:
            logging.error(f"[SESSION:{session.session_id}][ACTION:{action_id}] Error executing action {action_name}: {str(e)}")
            logging.error(f"[SESSION:{session.session_id}][ACTION:{action_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("action_error", {
                "action_id": action_id,
                "action_name": action_name,
                "error": str(e)
            })
            return {"status": "error", "error": str(e)}

    async def _extract_url_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Extract URL from parameters and update session."""
        url = parameters.get("url")
        if url:
            session.current_url = url
            session.last_action = "extract_url"
            return {"status": "success", "url": url}
        return {"status": "error", "error": "No URL provided"}

    async def _create_embeddings_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Create embeddings for the current URL."""
        logging.info(f"[SESSION:{session.session_id}] Creating embeddings for URL: {session.current_url}")
        
        if not session.current_url:
            logging.error(f"[SESSION:{session.session_id}] No URL available for embeddings")
            return {"status": "error", "error": "No URL available for embeddings"}
        
        try:
            session.add_execution_trace("embeddings_creation_started", {"url": session.current_url})
            
            # Use existing chat analyzer to create embeddings
            domain = self._get_domain_from_url(session.current_url)
            logging.debug(f"[SESSION:{session.session_id}] Extracted domain: {domain}")
            
            logging.info(f"[SESSION:{session.session_id}] Fetching rendered HTML")
            session.add_execution_trace("html_fetching_started", {"url": session.current_url})
            page_data = await self.chat_analyzer._fetch_rendered_html_async(session.current_url)
            logging.info(f"[SESSION:{session.session_id}] HTML fetched, size: {len(page_data) if page_data else 0} bytes")
            
            logging.info(f"[SESSION:{session.session_id}] Creating embeddings")
            session.add_execution_trace("embeddings_generation_started", {"domain": domain})
            self.chat_analyzer._create_embeddings(domain, session.current_url, page_data)
            logging.info(f"[SESSION:{session.session_id}] Embeddings created successfully")
            
            session.embeddings_created = True
            session.last_action = "create_embeddings"
            session.add_execution_trace("embeddings_creation_completed", {"domain": domain})
            
            return {"status": "success", "embeddings_created": True}
        except Exception as e:
            logging.error(f"[SESSION:{session.session_id}] Error creating embeddings: {str(e)}")
            logging.error(f"[SESSION:{session.session_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("embeddings_creation_error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    async def _generate_test_cases_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Generate test cases using existing chat analyzer."""
        logging.info(f"[SESSION:{session.session_id}] Generating test cases for URL: {session.current_url}")
        
        if not session.current_url:
            logging.error(f"[SESSION:{session.session_id}] No URL available for test generation")
            return {"status": "error", "error": "No URL available for test generation"}
        
        try:
            requirements = parameters.get("requirements", "general functionality")
            logging.info(f"[SESSION:{session.session_id}] Test requirements: {requirements}")
            
            session.add_execution_trace("test_cases_generation_started", {
                "url": session.current_url,
                "requirements": requirements
            })
            
            # Use existing chat analyzer to generate test cases
            logging.info(f"[SESSION:{session.session_id}] Calling chat analyzer for test case generation")
            test_cases = self.chat_analyzer._generate_test_cases_from_chunks_with_embeddings(
                requirements, session.current_url, []
            )
            
            logging.info(f"[SESSION:{session.session_id}] Generated {len(test_cases)} test cases")
            session.add_execution_trace("test_cases_generation_completed", {
                "test_cases_count": len(test_cases)
            })
            
            session.test_cases = test_cases
            session.last_action = "generate_test_cases"
            
            return {
                "status": "success", 
                "test_cases_generated": len(test_cases),
                "test_cases": test_cases
            }
        except Exception as e:
            logging.error(f"[SESSION:{session.session_id}] Error generating test cases: {str(e)}")
            logging.error(f"[SESSION:{session.session_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("test_cases_generation_error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    async def _generate_test_code_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Generate test code using existing test code generator."""
        logging.info(f"[SESSION:{session.session_id}] Generating test code")
        
        if not session.test_cases:
            logging.error(f"[SESSION:{session.session_id}] No test cases available for code generation")
            return {"status": "error", "error": "No test cases available for code generation"}
        
        try:
            logging.info(f"[SESSION:{session.session_id}] Using {len(session.test_cases)} test cases for code generation")
            session.add_execution_trace("test_code_generation_started", {
                "test_cases_count": len(session.test_cases)
            })
            
            # Generate code for the first test case (can be enhanced later)
            test_case = session.test_cases[0]
            test_case["url"] = session.current_url
            
            logging.info(f"[SESSION:{session.session_id}] Generating code for test case: {test_case.get('title', 'Untitled')}")
            result = self.test_code_generator.generate_test_code(test_case)
            
            logging.info(f"[SESSION:{session.session_id}] Test code generated successfully")
            session.add_execution_trace("test_code_generation_completed", {
                "test_case_title": test_case.get('title', 'Untitled'),
                "has_test_code": bool(result.get('test_code'))
            })
            
            session.generated_code = result
            session.last_action = "generate_test_code"
            
            return {
                "status": "success", 
                "code_generated": True,
                "generated_code": result
            }
        except Exception as e:
            logging.error(f"[SESSION:{session.session_id}] Error generating test code: {str(e)}")
            logging.error(f"[SESSION:{session.session_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("test_code_generation_error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    async def _execute_tests_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Execute tests using existing test executor."""
        logging.info(f"[SESSION:{session.session_id}] Executing tests")
        
        if not session.generated_code:
            logging.error(f"[SESSION:{session.session_id}] No test code available for execution")
            return {"status": "error", "error": "No test code available for execution"}
        
        try:
            logging.info(f"[SESSION:{session.session_id}] Preparing test case for execution")
            session.add_execution_trace("test_execution_started", {
                "has_generated_code": bool(session.generated_code)
            })
            
            # Prepare test case for execution
            test_case = {
                "test_code": session.generated_code.get("test_code", ""),
                "title": "Generated Test",
                "description": "Test generated from chat",
                "url": session.current_url
            }
            
            logging.info(f"[SESSION:{session.session_id}] Test code length: {len(test_case['test_code'])} characters")
            logging.info(f"[SESSION:{session.session_id}] Calling test executor")
            
            # Use existing test executor
            results = await self.test_executor.execute_tests([test_case])
            
            logging.info(f"[SESSION:{session.session_id}] Test execution completed")
            session.add_execution_trace("test_execution_completed", {
                "results_count": len(results) if results else 0
            })
            
            session.execution_results = results[0] if results else {}
            session.last_action = "execute_tests"
            
            return {
                "status": "success", 
                "execution_completed": True,
                "execution_results": results
            }
        except Exception as e:
            logging.error(f"[SESSION:{session.session_id}] Error executing tests: {str(e)}")
            logging.error(f"[SESSION:{session.session_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("test_execution_error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    async def _analyze_failure_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Analyze test failures using existing test executor."""
        logging.info(f"[SESSION:{session.session_id}] Analyzing test failures")
        
        if not session.execution_results:
            logging.error(f"[SESSION:{session.session_id}] No execution results available for analysis")
            return {"status": "error", "error": "No execution results available for analysis"}
        
        try:
            logging.info(f"[SESSION:{session.session_id}] Starting failure analysis")
            session.add_execution_trace("failure_analysis_started", {
                "has_execution_results": bool(session.execution_results)
            })
            
            # Use existing test executor's GPT analysis
            test_case = {
                "test_code": session.generated_code.get("test_code", ""),
                "title": "Generated Test",
                "description": "Test generated from chat",
                "url": session.current_url
            }
            
            logging.info(f"[SESSION:{session.session_id}] Calling GPT analysis for test failure")
            analysis = await self.test_executor._analyze_failed_test_with_gpt(
                test_case, session.execution_results
            )
            
            logging.info(f"[SESSION:{session.session_id}] Failure analysis completed")
            session.add_execution_trace("failure_analysis_completed", {
                "analysis_length": len(str(analysis)) if analysis else 0
            })
            
            session.last_action = "analyze_failure"
            
            return {"status": "success", "analysis_completed": True}
        except Exception as e:
            logging.error(f"[SESSION:{session.session_id}] Error analyzing test failure: {str(e)}")
            logging.error(f"[SESSION:{session.session_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("failure_analysis_error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    async def _modify_test_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Modify existing test cases."""
        # Placeholder for test modification
        return {"status": "not_implemented", "message": "Test modification not yet implemented"}

    async def _show_results_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Show previous results."""
        return {
            "status": "success",
            "session_summary": {
                "current_url": session.current_url,
                "test_cases_count": len(session.test_cases),
                "has_generated_code": bool(session.generated_code),
                "has_execution_results": bool(session.execution_results),
                "last_action": session.last_action
            }
        }

    async def _clear_session_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Clear session data."""
        session.current_url = None
        session.test_cases = []
        session.generated_code = {}
        session.execution_results = {}
        session.embeddings_created = False
        session.last_action = None
        session.context = ""
        
        return {"status": "success", "session_cleared": True}

    async def process_message(self, session_id: str, user_message: str) -> Dict:
        """Main method to process user message."""
        process_id = str(uuid.uuid4())[:8]
        logging.info(f"[PROCESS:{process_id}] Starting message processing for session {session_id}")
        logging.info(f"[PROCESS:{process_id}] User message: {user_message[:100]}...")
        
        session = self.session_manager.get_or_create_session(session_id)
        session.add_execution_trace("message_processing_started", {
            "process_id": process_id,
            "message_length": len(user_message)
        })
        
        try:
            # Add user message to conversation history
            logging.debug(f"[PROCESS:{process_id}] Adding user message to conversation history")
            session.add_message("user", user_message)
            
            # Get GPT response with actions
            logging.info(f"[PROCESS:{process_id}] Getting GPT response with actions")
            session.add_execution_trace("gpt_analysis_started", {"process_id": process_id})
            gpt_response = await self.get_gpt_response_with_actions(user_message, session)
            
            # Execute actions
            action_results = []
            actions = gpt_response.get("actions", [])
            logging.info(f"[PROCESS:{process_id}] Executing {len(actions)} actions")
            session.add_execution_trace("actions_execution_started", {"actions_count": len(actions)})
            
            for i, action in enumerate(actions):
                logging.info(f"[PROCESS:{process_id}] Executing action {i+1}/{len(actions)}: {action.get('action', 'unknown')}")
                result = await self.execute_action(action, session)
                action_results.append(result)
                logging.debug(f"[PROCESS:{process_id}] Action {i+1} result: {result.get('status', 'unknown')}")
            
            # Update session with GPT suggestions
            session_updates = gpt_response.get("session_updates", {})
            if session_updates.get("current_url"):
                logging.info(f"[PROCESS:{process_id}] Updating session URL: {session_updates['current_url']}")
                session.current_url = session_updates["current_url"]
            if session_updates.get("context"):
                logging.info(f"[PROCESS:{process_id}] Updating session context")
                session.context = session_updates["context"]
            
            # Add assistant response to conversation history
            user_response = gpt_response.get("user_response", "I understand your request.")
            logging.debug(f"[PROCESS:{process_id}] Adding assistant response to conversation history")
            session.add_message("assistant", user_response, action_results)
            
            # Log final processing summary
            logging.info(f"[PROCESS:{process_id}] Message processing completed successfully")
            session.add_execution_trace("message_processing_completed", {
                "process_id": process_id,
                "actions_executed": len(action_results),
                "response_length": len(user_response)
            })
            
            # Return unified response
            return {
                "user_response": user_response,
                "action_results": action_results,
                "session_state": session.get_session_summary()
            }
            
        except Exception as e:
            logging.error(f"[PROCESS:{process_id}] Error during message processing: {str(e)}")
            logging.error(f"[PROCESS:{process_id}] Traceback: {traceback.format_exc()}")
            session.add_execution_trace("message_processing_error", {
                "process_id": process_id,
                "error": str(e)
            })
            raise

    def clear_session(self, session_id: str) -> Dict:
        """Clear a specific session."""
        self.session_manager.clear_session(session_id)
        return {"status": "success", "session_cleared": True}

    def get_session_info(self, session_id: str) -> Dict:
        """Get information about a session."""
        session_info = self.session_manager.get_session_info(session_id)
        if session_info:
            return session_info
        else:
            return {
                "session_id": session_id,
                "current_url": None,
                "test_cases_count": 0,
                "has_generated_code": False,
                "has_execution_results": False,
                "last_action": None,
                "context": "",
                "created_at": None,
                "last_active": None,
                "message_count": 0
            } 