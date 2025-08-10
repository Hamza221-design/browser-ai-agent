import requests
import json
import re
import logging
import os
from typing import Dict, List

class TestCodeGeneratorService:
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.prompts_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')

    def _load_prompt(self, prompt_name: str) -> str:
        """Load prompt from file."""
        prompt_path = os.path.join(self.prompts_dir, f"{prompt_name}.txt")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logging.error(f"Prompt file not found: {prompt_path}")
            return ""

    def generate_test_code(self, test_case: Dict) -> Dict:
        """Generate test code from test case details."""
        logging.info(f"Generating test code for: {test_case.get('title', 'Unknown')}")
        
        prompt_template = self._load_prompt("generate_test_code")
        if not prompt_template:
            logging.error("Failed to load prompt template")
            return self._fallback_response(test_case)
        
        # Format test steps as a list
        test_steps = test_case.get('test_steps', [])
        test_steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(test_steps)])
        
        prompt = prompt_template.format(
            title=test_case.get('title', ''),
            url=test_case.get('url', ''),
            description=test_case.get('description', ''),
            test_type=test_case.get('test_type', ''),
            element_type=test_case.get('element_type', ''),
            test_steps=test_steps_str,
            expected_behavior=test_case.get('expected_behavior', ''),
            html_code=test_case.get('html_code', '')
        )

        logging.info(f"Prompt: {prompt}")
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
