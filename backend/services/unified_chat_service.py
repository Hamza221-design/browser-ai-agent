import os
import json
import logging
import asyncio
import requests
import chromadb
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
    
    def add_message(self, role: str, content: str, actions: List[Dict] = None):
        """Add a message to the conversation history"""
        message = ChatMessage(role, content, datetime.now(), actions)
        self.messages.append(message)
        self.last_active = datetime.now()
    
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
            "message_count": len(self.messages)
        }

class ChatSessionManager:
    def __init__(self):
        self.sessions = {}
    
    def get_or_create_session(self, session_id: str) -> ChatSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(session_id)
        return self.sessions[session_id]
    
    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
    
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
        self.chat_analyzer = ChatAnalyzerService(openai_api_key)
        self.test_code_generator = TestCodeGeneratorService(openai_api_key)
        self.test_executor = TestExecutorService(openai_api_key)
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_DB"),
            settings=chromadb.config.Settings(
                anonymized_telemetry=False
            )
        )

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain name from URL for collection naming."""
        parsed = urlparse(url)
        domain = parsed.netloc
        domain = re.sub(r'[^a-zA-Z0-9_-]', '_', domain)
        domain = domain.strip('_')
        if not domain:
            domain = 'default_domain'
        return domain

    def _create_unified_prompt(self, user_message: str, session: ChatSession) -> str:
        """Create prompt for GPT to understand intent and provide actions."""
        conversation_context = session.get_conversation_context()
        
        logging.info(f"Using conversation context with {len(session.messages)} messages")
        if conversation_context:
            logging.debug(f"Conversation context: {conversation_context[:200]}...")
        
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
        try:
            prompt = self._create_unified_prompt(user_message, session)
            
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
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            try:
                parsed = json.loads(content)
                return self._validate_gpt_response(parsed)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse GPT response as JSON: {content}")
                return self._get_fallback_response(user_message)
                
        except Exception as e:
            logging.error(f"Error getting GPT response: {str(e)}")
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
        
        logging.info(f"Executing action: {action_name} with parameters: {parameters}")
        
        try:
            if action_name == "extract_url":
                return await self._extract_url_action(parameters, session)
            elif action_name == "create_embeddings":
                return await self._create_embeddings_action(parameters, session)
            elif action_name == "generate_test_cases":
                return await self._generate_test_cases_action(parameters, session)
            elif action_name == "generate_test_code":
                return await self._generate_test_code_action(parameters, session)
            elif action_name == "execute_tests":
                return await self._execute_tests_action(parameters, session)
            elif action_name == "analyze_failure":
                return await self._analyze_failure_action(parameters, session)
            elif action_name == "modify_test":
                return await self._modify_test_action(parameters, session)
            elif action_name == "show_results":
                return await self._show_results_action(parameters, session)
            elif action_name == "clear_session":
                return await self._clear_session_action(parameters, session)
            elif action_name == "no_action":
                return {"status": "no_action_needed"}
            else:
                return {"status": "unknown_action", "action": action_name}
                
        except Exception as e:
            logging.error(f"Error executing action {action_name}: {str(e)}")
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
        if not session.current_url:
            return {"status": "error", "error": "No URL available for embeddings"}
        
        try:
            # Use existing chat analyzer to create embeddings
            domain = self._get_domain_from_url(session.current_url)
            page_data = await self.chat_analyzer._fetch_rendered_html_async(session.current_url)
            self.chat_analyzer._create_embeddings(domain, session.current_url, page_data)
            
            session.embeddings_created = True
            session.last_action = "create_embeddings"
            
            return {"status": "success", "embeddings_created": True}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _generate_test_cases_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Generate test cases using existing chat analyzer."""
        if not session.current_url:
            return {"status": "error", "error": "No URL available for test generation"}
        
        try:
            requirements = parameters.get("requirements", "general functionality")
            
            # Use existing chat analyzer to generate test cases
            test_cases = self.chat_analyzer._generate_test_cases_from_chunks_with_embeddings(
                requirements, session.current_url, []
            )
            
            session.test_cases = test_cases
            session.last_action = "generate_test_cases"
            
            return {
                "status": "success", 
                "test_cases_generated": len(test_cases),
                "test_cases": test_cases
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _generate_test_code_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Generate test code using existing test code generator."""
        if not session.test_cases:
            return {"status": "error", "error": "No test cases available for code generation"}
        
        try:
            # Generate code for the first test case (can be enhanced later)
            test_case = session.test_cases[0]
            test_case["url"] = session.current_url
            
            result = self.test_code_generator.generate_test_code(test_case)
            
            session.generated_code = result
            session.last_action = "generate_test_code"
            
            return {
                "status": "success", 
                "code_generated": True,
                "generated_code": result
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _execute_tests_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Execute tests using existing test executor."""
        if not session.generated_code:
            return {"status": "error", "error": "No test code available for execution"}
        
        try:
            # Prepare test case for execution
            test_case = {
                "test_code": session.generated_code.get("test_code", ""),
                "title": "Generated Test",
                "description": "Test generated from chat",
                "url": session.current_url
            }
            
            # Use existing test executor
            results = await self.test_executor.execute_tests([test_case])
            
            session.execution_results = results[0] if results else {}
            session.last_action = "execute_tests"
            
            return {
                "status": "success", 
                "execution_completed": True,
                "execution_results": results
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _analyze_failure_action(self, parameters: Dict, session: ChatSession) -> Dict:
        """Analyze test failures using existing test executor."""
        if not session.execution_results:
            return {"status": "error", "error": "No execution results available for analysis"}
        
        try:
            # Use existing test executor's GPT analysis
            test_case = {
                "test_code": session.generated_code.get("test_code", ""),
                "title": "Generated Test",
                "description": "Test generated from chat",
                "url": session.current_url
            }
            
            analysis = await self.test_executor._analyze_failed_test_with_gpt(
                test_case, session.execution_results
            )
            
            session.last_action = "analyze_failure"
            
            return {"status": "success", "analysis_completed": True}
        except Exception as e:
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
        session = self.session_manager.get_or_create_session(session_id)
        
        logging.info(f"Processing message for session {session_id}: {user_message[:100]}...")
        
        # Add user message to conversation history
        session.add_message("user", user_message)
        
        # Get GPT response with actions
        gpt_response = await self.get_gpt_response_with_actions(user_message, session)
        
        # Execute actions
        action_results = []
        for action in gpt_response.get("actions", []):
            result = await self.execute_action(action, session)
            action_results.append(result)
        
        # Update session with GPT suggestions
        session_updates = gpt_response.get("session_updates", {})
        if session_updates.get("current_url"):
            session.current_url = session_updates["current_url"]
        if session_updates.get("context"):
            session.context = session_updates["context"]
        
        # Add assistant response to conversation history
        user_response = gpt_response.get("user_response", "I understand your request.")
        session.add_message("assistant", user_response, action_results)
        
        # Return unified response
        return {
            "user_response": user_response,
            "action_results": action_results,
            "session_state": session.get_session_summary()
        }

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