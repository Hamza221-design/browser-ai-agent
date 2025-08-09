import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Optional
import time
import asyncio
import logging
import os
from playwright.async_api import async_playwright

class WebAnalyzerService:
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

    async def _fetch_rendered_html_async(self, url: str) -> str:
        """Fetch fully rendered HTML using Playwright Async API."""
        logging.info(f"Fetching rendered HTML for URL: {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)
            html = await page.content()
            await browser.close()
        logging.info(f"Successfully fetched HTML for URL: {url}")
        return html

    async def analyze_url_with_config(
        self, 
        url: str, 
        extract_elements: List[str] = ["forms", "links"],
        test_types: List[str] = ["functional", "validation", "negative", "positive", "error_handling"],
        chunk_size: int = 2000
    ) -> Dict:
        """Analyze URL with configurable element extraction and test types."""
        logging.info(f"Starting analysis with config: elements={extract_elements}, test_types={test_types}")
        
        html_content = await self._fetch_rendered_html_async(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        elements = {}
        element_counts = {}
        
        if "forms" in extract_elements:
            elements["forms"] = soup.find_all('form')
            element_counts["forms"] = len(elements["forms"])
            logging.info(f"Found {len(elements['forms'])} forms")
            
        if "buttons" in extract_elements:
            elements["buttons"] = soup.find_all(['button', 'input[type="submit"]'])
            element_counts["buttons"] = len(elements["buttons"])
            logging.info(f"Found {len(elements['buttons'])} buttons")
            
        if "links" in extract_elements:
            elements["links"] = soup.find_all('a', href=True)
            element_counts["links"] = len(elements["links"])
            logging.info(f"Found {len(elements['links'])} links")
            
        if "inputs" in extract_elements:
            elements["inputs"] = soup.find_all('input')
            element_counts["inputs"] = len(elements["inputs"])
            logging.info(f"Found {len(elements['inputs'])} inputs")

        all_test_cases = []
        for element_type, element_list in elements.items():
            if element_list:
                chunks = self._create_chunks(element_list, chunk_size)
                logging.info(f"Created {len(chunks)} chunks for {element_type}")
                for i, chunk in enumerate(chunks):
                    test_cases = self._analyze_chunk_with_config(
                        chunk, element_type, i+1, test_types
                    )
                    all_test_cases.extend(test_cases)
                    time.sleep(0.5)

        logging.info(f"Analysis completed. Total test cases: {len(all_test_cases)}")
        return {
            "url": url,
            "test_cases": all_test_cases,
            "total_cases": len(all_test_cases),
            "element_counts": element_counts
        }

    def _create_chunks(self, elements: List, chunk_size: int) -> List[str]:
        chunks = []
        current_chunk = ""
        for el in elements:
            html_str = str(el)
            if len(current_chunk) + len(html_str) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = html_str
            else:
                current_chunk += html_str + "\n\n"
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def _analyze_chunk_with_config(
        self, 
        html_chunk: str, 
        element_type: str, 
        chunk_num: int,
        test_types: List[str]
    ) -> List[Dict]:
        """Analyze chunk with configurable test types."""
        logging.info(f"Analyzing {element_type} chunk {chunk_num} with test types: {test_types}")
        
        prompt_template = self._load_prompt("analyze_chunk")
        if not prompt_template:
            logging.error("Failed to load prompt template")
            return [self._fallback_case(element_type, chunk_num, test_types[0] if test_types else "functional", html_chunk)]
        
        test_types_str = ", ".join(test_types)
        prompt = prompt_template.format(
            element_type=element_type,
            test_types=test_types_str,
            html_chunk=html_chunk,
            chunk_num=chunk_num
        )

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert QA engineer."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1500
            }
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            content = result["choices"][0]["message"]["content"]
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                test_cases = json.loads(json_match.group())
                for test_case in test_cases:
                    # Truncate HTML chunk if it's too large (keep first 1000 characters)
                    truncated_html = html_chunk[:1000] + "..." if len(html_chunk) > 1000 else html_chunk
                    test_case["html_chunk"] = truncated_html
                logging.info(f"Generated {len(test_cases)} test cases for {element_type} chunk {chunk_num}")
                logging.debug(f"First test case keys: {list(test_cases[0].keys()) if test_cases else 'No test cases'}")
                return test_cases
            else:
                logging.warning(f"No JSON found in response for {element_type} chunk {chunk_num}, using fallback")
                return [self._fallback_case(element_type, chunk_num, test_types[0] if test_types else "functional", html_chunk)]
        except Exception as e:
            logging.error(f"Error analyzing {element_type} chunk {chunk_num}: {str(e)}")
            return [self._fallback_case(element_type, chunk_num, test_types[0] if test_types else "functional", html_chunk)]

    def _fallback_case(self, element_type: str, chunk_num: int, test_type: str, html_chunk: str = "") -> Dict:
        # Truncate HTML chunk if it's too large
        truncated_html = html_chunk[:1000] + "..." if len(html_chunk) > 1000 else html_chunk
        return {
            "title": f"Fallback {element_type} test - Chunk {chunk_num}",
            "description": f"Basic {test_type} test for {element_type} elements in chunk {chunk_num}",
            "expected_behavior": f"{element_type} elements should be functional",
            "test_steps": [
                f"Check {element_type} elements are present",
                f"Verify {element_type} elements are interactive"
            ],
            "element_type": element_type,
            "test_type": test_type,
            "chunk_number": chunk_num,
            "html_chunk": truncated_html
        }
