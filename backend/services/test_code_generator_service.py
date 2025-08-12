import os
# Disable ChromaDB telemetry before importing
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import requests
import json
import re
import logging
import chromadb
from urllib.parse import urlparse
from typing import Dict, List, Optional

class TestCodeGeneratorService:
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.prompts_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        
        # Initialize ChromaDB client with telemetry disabled
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_DB"),
            settings=chromadb.config.Settings(
                anonymized_telemetry=False
            )
        )

    def _load_prompt(self, prompt_name: str) -> str:
        """Load prompt from file."""
        prompt_path = os.path.join(self.prompts_dir, f"{prompt_name}.txt")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logging.error(f"Prompt file not found: {prompt_path}")
            return ""

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain name from URL for collection naming."""
        parsed = urlparse(url)
        # Replace all invalid characters for ChromaDB collection names
        # Only allow alphanumeric characters, underscores, and hyphens
        domain = parsed.netloc
        # Replace dots, hyphens, colons, and other special characters with underscores
        domain = re.sub(r'[^a-zA-Z0-9_-]', '_', domain)
        # Ensure it doesn't start or end with underscore
        domain = domain.strip('_')
        # Ensure it's not empty
        if not domain:
            domain = 'default_domain'
        return domain

    def _get_relevant_embeddings(self, domain: str, test_case: Dict, max_distance: float = 2.0) -> List[Dict]:
        """Retrieve relevant embeddings based on test case content."""
        try:
            collection = self.chroma_client.get_collection(name=domain)
            
            # Create a comprehensive query from test case content
            query_text = self._create_query_from_test_case(test_case)
            
            logging.info(f"Searching embeddings for domain: {domain}")
            logging.info(f"Query text: {query_text[:200]}...")
            
            # Query embeddings with the test case content
            results = collection.query(
                query_texts=[query_text],
                n_results=4,  # Get top 5 most relevant embeddings
                where={"domain": domain}
            )
            
            relevant_docs = []
            for i, distance in enumerate(results['distances'][0]):
                if distance <= max_distance:
                    relevant_docs.append({
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': distance
                    })
            
            # If no relevant docs found, try with broader search
            if not relevant_docs:
                logging.info(f"No embeddings found with distance <= {max_distance}, trying broader search")
                # Get all embeddings for the domain
                all_results = collection.get(where={"domain": domain})
                if all_results['ids']:
                    # Use the first few embeddings as context
                    for i in range(min(3, len(all_results['ids']))):
                        relevant_docs.append({
                            'content': all_results['documents'][i],
                            'metadata': all_results['metadatas'][0][i],
                            'distance': 3.0  # High distance to indicate it's a fallback
                        })
                    logging.info(f"Using {len(relevant_docs)} fallback embeddings from domain")
            else:
                logging.info(f"Found {len(relevant_docs)} relevant embeddings for test case")
            
            return relevant_docs
            
        except Exception as e:
            logging.error(f"Error retrieving embeddings: {str(e)}")
            return []

    def _create_query_from_test_case(self, test_case: Dict) -> str:
        """Create a comprehensive query string from test case content."""
        query_parts = []
        
        # Add title
        if test_case.get('title'):
            query_parts.append(test_case['title'])
        
        # Add description
        if test_case.get('description'):
            query_parts.append(test_case['description'])
        
        # Add expected behavior
        if test_case.get('expected_behavior'):
            query_parts.append(test_case['expected_behavior'])
        
        # Add element type
        if test_case.get('element_type'):
            query_parts.append(test_case['element_type'])
        
        # Add test steps
        if test_case.get('test_steps'):
            test_steps_text = ' '.join(test_case['test_steps'])
            query_parts.append(test_steps_text)
        
        # Add HTML code if available
        if test_case.get('html_code'):
            # Extract text content from HTML (basic extraction)
            html_text = re.sub(r'<[^>]+>', ' ', test_case['html_code'])
            html_text = re.sub(r'\s+', ' ', html_text).strip()
            if html_text:
                query_parts.append(html_text)
        
        return ' '.join(query_parts)

    def _format_embeddings_for_prompt(self, embeddings: List[Dict]) -> str:
        """Format embeddings into a readable context for the prompt."""
        if not embeddings:
            return ""
        
        formatted_parts = []
        formatted_parts.append("=== RELEVANT PAGE CONTEXT ===")
        
        for i, embedding in enumerate(embeddings, 1):
            content = embedding['content']
            metadata = embedding['metadata']
            distance = embedding['distance']
            
            # Truncate content if too long
            if len(content) > 500:
                content = content[:500] + "..."
            
            formatted_parts.append(f"\n--- Context {i} (Relevance: {distance:.2f}) ---")
            formatted_parts.append(f"Type: {metadata.get('chunk_type', 'unknown')}")
            formatted_parts.append(f"Content: {content}")
            
            # Add metadata if available
            if metadata.get('title'):
                formatted_parts.append(f"Page Title: {metadata['title']}")
            if metadata.get('meta_description'):
                formatted_parts.append(f"Description: {metadata['meta_description']}")
        
        formatted_parts.append("\n=== END CONTEXT ===\n")
        
        return '\n'.join(formatted_parts)

    def generate_test_code(self, test_case: Dict) -> Dict:
        """Generate test code from test case details with embedding context."""
        logging.info(f"Generating test code for: {test_case.get('title', 'Unknown')}")
        
        # Get URL from test case
        url = test_case.get('url', '')
        if not url:
            logging.error("No URL found in test case")
            return self._fallback_response(test_case)
        
        # Get domain for ChromaDB collection
        domain = self._get_domain_from_url(url)
        logging.info(f"Using domain: {domain} for embedding search")
        
        # Get relevant embeddings for this test case
        relevant_embeddings = self._get_relevant_embeddings(domain, test_case, max_distance=2.0)
        
        if relevant_embeddings:
            logging.info(f"Found {len(relevant_embeddings)} relevant embeddings for test case")
            # Log embedding types for debugging
            embedding_types = [emb['metadata'].get('chunk_type', 'unknown') for emb in relevant_embeddings]
            logging.info(f"Embedding types: {embedding_types}")
        else:
            logging.info("No relevant embeddings found, will generate test code without context")
        
        prompt_template = self._load_prompt("generate_test_code")
        if not prompt_template:
            logging.error("Failed to load prompt template")
            return self._fallback_response(test_case)
        
        # Format test steps as a list
        test_steps = test_case.get('test_steps', [])
        test_steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(test_steps)])
        
        # Format embeddings for the prompt
        embeddings_context = ""
        if relevant_embeddings:
            embeddings_context = self._format_embeddings_for_prompt(relevant_embeddings)
        
        prompt = prompt_template.format(
            title=test_case.get('title', ''),
            url=test_case.get('url', ''),
            description=test_case.get('description', ''),
            test_type=test_case.get('test_type', ''),
            element_type=test_case.get('element_type', ''),
            test_steps=test_steps_str,
            expected_behavior=test_case.get('expected_behavior', ''),
            html_code=test_case.get('html_code', ''),
            embeddings_context=embeddings_context
        )

        logging.info(f"Prompt length: {len(prompt)} characters")
        if relevant_embeddings:
            logging.info(f"Using {len(relevant_embeddings)} embeddings for context")
        else:
            logging.info("No embeddings found, generating test code without context")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert QA engineer who generates Playwright test scripts in Python."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 3000
            }
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            content = result["choices"][0]["message"]["content"]
            
            return {
                "test_code": content,
                "filename": f"test_{test_case.get('title', 'case').lower().replace(' ', '_').replace('-', '_')}.py",
                "status": "success"
            }
            
        except Exception as e:
            logging.error(f"Error generating test code: {str(e)}")
            return self._fallback_response(test_case)

    def _fallback_response(self, test_case: Dict) -> Dict:
        """Generate fallback test code."""
        title = test_case.get('title', 'Test Case')
        element_type = test_case.get('element_type', 'element')
        
        fallback_code = f'''import pytest
from playwright.sync_api import expect

def test_{title.lower().replace(' ', '_').replace('-', '_')}():
    """
    {test_case.get('description', 'Test case description')}
    """
    # TODO: Implement test based on {element_type} elements
    # This is a fallback test template
    
    # Add your test implementation here
    pass
'''
        
        return {
            "test_code": fallback_code,
            "filename": f"test_{title.lower().replace(' ', '_').replace('-', '_')}.py",
            "status": "fallback"
        }
