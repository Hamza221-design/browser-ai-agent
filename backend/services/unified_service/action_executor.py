import os
import logging
import re
from typing import Dict
from urllib.parse import urlparse
import chromadb
from .url_actions import URLActions
from .embedding_actions import EmbeddingActions
from .embedding_retriever import EmbeddingRetriever
from ..test_executor_service import TestExecutorService

class ActionExecutor:
    def __init__(self):
        # Set ChromaDB environment variables for model caching
        chroma_db_path = os.getenv("CHROMA_DB", "db/chromadb")
        os.environ["CHROMA_CACHE_DIR"] = os.path.join(chroma_db_path, "chroma_models")
        os.environ["CHROMA_TELEMETRY"] = "False"
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        # Disable Hugging Face tokenizers parallelism to avoid forking warnings
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Ensure the database directory exists and has proper permissions
        try:
            os.makedirs(chroma_db_path, exist_ok=True)
            os.makedirs(os.path.join(chroma_db_path, "chroma_models"), exist_ok=True)
            logging.info(f"ChromaDB directories created/verified: {chroma_db_path}")
        except Exception as e:
            logging.error(f"Error creating ChromaDB directories: {str(e)}")
        
        # Initialize ChromaDB client with new configuration
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=chroma_db_path,
                settings=chromadb.config.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            logging.info(f"ChromaDB client initialized successfully with path: {chroma_db_path}")
        except Exception as e:
            logging.error(f"Error initializing ChromaDB client: {str(e)}")
            raise
        
        # Initialize action handlers
        self.url_actions = URLActions(self.chroma_client)
        self.embedding_actions = EmbeddingActions(self.chroma_client)
        self.embedding_retriever = EmbeddingRetriever(self.chroma_client)
        
        # Initialize test executor service
        self.test_executor = TestExecutorService()
        
        logging.info("[ACTION_EXECUTOR] Initialized with ChromaDB model caching and TestExecutorService")

    async def execute_action(self, action: Dict) -> Dict:
        """Execute a specific action."""
        action_name = action.get("action", "no_action")
        parameters = action.get("parameters", {})
        
        logging.info(f"Executing action: {action_name}")
        logging.info(f"Action parameters: {parameters}")
        
        try:
            if action_name == "extract_url":
                return self.url_actions.extract_url(parameters)
            elif action_name == "create_embeddings":
                return await self.embedding_actions.create_embeddings(parameters)
            elif action_name == "list_domain_pages":
                return self.embedding_actions.list_domain_pages(parameters)
            elif action_name == "get_relevant_embeddings":
                return self.get_relevant_embeddings_action(parameters)
            elif action_name == "execute_test":
                return await self.execute_test_action(parameters)
            elif action_name == "no_action":
                return {"status": "no_action_needed"}
            else:
                return {"status": "not_implemented", "action": action_name}
                
        except Exception as e:
            logging.error(f"Error executing action {action_name}: {str(e)}")
            return {"status": "error", "error": str(e)}

    def get_relevant_embeddings_action(self, parameters: Dict) -> Dict:
        """Get relevant embeddings for a query and URL."""
        query = parameters.get("query")
        url = parameters.get("url")
        max_distance = parameters.get("max_distance", 1.8)
        max_results = parameters.get("max_results", 3)
        
        if not query or not url:
            return {"status": "error", "error": "Both query and URL are required"}
        
        try:
            relevant_embeddings = self.embedding_retriever.get_relevant_embeddings_for_url(
                query, url, max_distance, max_results
            )
            
            context = self.embedding_retriever.format_embeddings_for_prompt(relevant_embeddings)
            
            return {
                "status": "success",
                "embeddings_found": len(relevant_embeddings),
                "max_distance": max_distance,
                "context": context,
                "embeddings": relevant_embeddings
            }
            
        except Exception as e:
            logging.error(f"Error getting relevant embeddings: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def execute_test_action(self, parameters: Dict) -> Dict:
        """Execute test code using the existing TestExecutorService."""
        test_code = parameters.get("python_code")
        test_name = parameters.get("test_name", "Generated Test")
        url = parameters.get("url")
        
        if not test_code:
            return {"status": "error", "error": "No Python code provided"}
        
        try:
            logging.info(f"Executing test using TestExecutorService: {test_name}")
            logging.debug(f"Test code: {test_code[:200]}...")
            
            # Create a test case in the format expected by TestExecutorService
            test_case = {
                "title": test_name,
                "test_code": test_code,
                "url": url,
                "description": f"Generated test for {url}",
                "test_type": "functional",
                "element_type": "general"
            }
            
            # Execute the test using the existing service
            results = await self.test_executor.execute_tests([test_case])
            
            if results and len(results) > 0:
                result = results[0]  # Get the first (and only) result
                
                # Map the result to our expected format
                return {
                    "status": "success" if result.get("status") == "passed" else "failed",
                    "test_name": test_name,
                    "url": url,
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "execution_time": result.get("execution_time", 0),
                    "message": f"Test '{test_name}' {'passed' if result.get('status') == 'passed' else 'failed'}"
                }
            else:
                return {
                    "status": "error",
                    "test_name": test_name,
                    "url": url,
                    "error": "No results returned from test execution",
                    "message": f"Test '{test_name}' failed to execute"
                }
                
        except Exception as e:
            logging.error(f"Error executing test: {str(e)}")
            return {"status": "error", "error": str(e)} 