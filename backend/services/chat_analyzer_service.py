import os
# Disable ChromaDB telemetry before importing
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import requests
import re
import logging
import asyncio
import math
import chromadb
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

class ChatAnalyzerService:
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

    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from file."""
        prompt_path = os.path.join(self.prompts_dir, prompt_file)
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logging.error(f"Prompt file not found: {prompt_path}")
            return ""
        except Exception as e:
            logging.error(f"Error loading prompt file {prompt_path}: {str(e)}")
            return ""

    def extract_url_and_requirements(self, user_message: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract URL, test requirements, and number of test cases from user message."""
        logging.info(f"Extracting URL and requirements from message: '{user_message[:100]}...'")
        
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, user_message)
        
        if not urls:
            logging.warning("No URLs found in user message")
            return None, None
            
        url = urls[0]
        logging.info(f"Extracted URL: {url}")
        
        # Remove URL from message to get requirements
        requirements = re.sub(url_pattern, '', user_message).strip()
        
        if not requirements:
            logging.warning(f"No requirements found after extracting URL from message")
            return url, None
        
        
        logging.info(f"Extracted requirements: '{requirements}'")
        return url, requirements
    
    def _extract_test_case_count(self, message: str) -> int:
        """Return default number of test cases - count extraction disabled."""
        # Default to 5 test cases for all requests
        default_count = 5
        logging.info(f"Using default test case count: {default_count}")
        return default_count
    


    async def _fetch_rendered_html_async(self, url: str) -> Dict:
        """Fetch fully rendered HTML using Playwright."""
        logging.info(f"Starting HTML fetch for URL: {url}")
        
        try:
            async with async_playwright() as p:
                logging.debug("Launching Playwright browser...")
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                logging.debug(f"Navigating to URL: {url}")
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                logging.debug("Waiting for page to stabilize...")
                await asyncio.sleep(2)
                
                # Get page content including JavaScript rendered content
                html = await page.content()
                
                # Get page title
                title = await page.title()
                
                # Get page metadata
                meta_description = await page.evaluate("() => document.querySelector('meta[name=\"description\"]')?.content || ''")
                meta_keywords = await page.evaluate("() => document.querySelector('meta[name=\"keywords\"]')?.content || ''")
                
                # Get all text content
                text_content = await page.evaluate("() => document.body.innerText")
                
                # Get JavaScript content
                scripts = await page.evaluate("() => Array.from(document.scripts).map(s => s.textContent).join('\\n')")
                
                # Get CSS content
                styles = await page.evaluate("() => Array.from(document.styleSheets).map(s => s.href).join('\\n')")
                
                html_length = len(html)
                logging.info(f"Successfully fetched HTML for {url} - Content length: {html_length} characters")
                
                await browser.close()
                logging.debug("Browser closed successfully")
                
                return {
                    'html': html,
                    'title': title,
                    'meta_description': meta_description,
                    'meta_keywords': meta_keywords,
                    'text_content': text_content,
                    'scripts': scripts,
                    'styles': styles
                }
                
        except Exception as e:
            logging.error(f"Failed to fetch HTML for URL {url}: {str(e)}")
            logging.error(f"Error type: {type(e).__name__}")
            raise

    def _extract_elements_by_requirements(self, html_content: str, requirements: str) -> Dict[str, List]:
        """Extract HTML elements based on user requirements."""
        logging.info(f"Extracting elements based on requirements: '{requirements}'")
        logging.debug(f"HTML content length: {len(html_content)} characters")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        elements = {}
        detected_keywords = []
        
        requirements_lower = requirements.lower()
        
        # Check for form-related requirements
        form_keywords = ['form', 'login', 'signup', 'register', 'submit', 'input']
        if any(keyword in requirements_lower for keyword in form_keywords):
            detected_keywords.extend([kw for kw in form_keywords if kw in requirements_lower])
            elements['forms'] = soup.find_all('form')
            elements['inputs'] = soup.find_all('input')
            logging.info(f"Form-related keywords detected: {[kw for kw in form_keywords if kw in requirements_lower]}")
            
        # Check for navigation requirements
        nav_keywords = ['link', 'navigation', 'menu', 'click', 'navigate']
        if any(keyword in requirements_lower for keyword in nav_keywords):
            detected_keywords.extend([kw for kw in nav_keywords if kw in requirements_lower])
            elements['links'] = soup.find_all('a', href=True)
            logging.info(f"Navigation keywords detected: {[kw for kw in nav_keywords if kw in requirements_lower]}")
            
        # Check for button requirements
        button_keywords = ['button', 'click', 'submit', 'action']
        if any(keyword in requirements_lower for keyword in button_keywords):
            detected_keywords.extend([kw for kw in button_keywords if kw in requirements_lower])
            elements['buttons'] = soup.find_all(['button', 'input[type="submit"]'])
            logging.info(f"Button keywords detected: {[kw for kw in button_keywords if kw in requirements_lower]}")
            
        # Check for image requirements
        image_keywords = ['image', 'img', 'photo', 'picture']
        if any(keyword in requirements_lower for keyword in image_keywords):
            detected_keywords.extend([kw for kw in image_keywords if kw in requirements_lower])
            elements['images'] = soup.find_all('img')
            logging.info(f"Image keywords detected: {[kw for kw in image_keywords if kw in requirements_lower]}")
            
        # Check for table requirements
        table_keywords = ['table', 'data', 'list', 'grid']
        if any(keyword in requirements_lower for keyword in table_keywords):
            detected_keywords.extend([kw for kw in table_keywords if kw in requirements_lower])
            elements['tables'] = soup.find_all('table')
            logging.info(f"Table keywords detected: {[kw for kw in table_keywords if kw in requirements_lower]}")
            
        # If no specific elements found, extract elements based on default order
        if not elements:
            logging.warning("No specific keywords detected, extracting elements based on default order")
            # Use default order for element extraction
            default_order = ['forms', 'buttons', 'inputs', 'links', 'navigation', 'images', 'tables']
            
            for element_type in default_order:
                if element_type == 'forms':
                    elements['forms'] = soup.find_all('form')
                elif element_type == 'buttons':
                    elements['buttons'] = soup.find_all(['button', 'input[type="submit"]'])
                elif element_type == 'inputs':
                    elements['inputs'] = soup.find_all('input')
                elif element_type == 'links':
                    elements['links'] = soup.find_all('a', href=True)
                elif element_type == 'navigation':
                    elements['navigation'] = soup.find_all(['nav', 'header', 'footer'])
                elif element_type == 'images':
                    elements['images'] = soup.find_all('img')
                elif element_type == 'tables':
                    elements['tables'] = soup.find_all('table')
            
        # Log element counts
        element_counts = {k: len(v) for k, v in elements.items() if v}
        logging.info(f"Elements extracted: {element_counts}")
        
        if not any(elements.values()):
            logging.warning("No elements found on the page")
        
        return elements

    def _create_chunks(self, elements: Dict[str, List], chunk_size: int = 2000) -> List[Dict]:
        """Create HTML chunks with element type information."""
        logging.info(f"Creating chunks with size limit: {chunk_size} characters")
        chunks = []
        
        for element_type, element_list in elements.items():
            if element_list:
                logging.debug(f"Processing {len(element_list)} {element_type} elements")
                current_chunk = ""
                current_elements = []
                chunk_count = 0
                
                for i, el in enumerate(element_list):
                    html_str = str(el)
                    html_length = len(html_str)
                    
                    if len(current_chunk) + html_length > chunk_size and current_chunk:
                        chunk_count += 1
                        chunk_data = {
                            'element_type': element_type,
                            'html_content': current_chunk,
                            'element_count': len(current_elements)
                        }
                        chunks.append(chunk_data)
                        logging.debug(f"Created chunk {chunk_count} for {element_type}: {len(current_elements)} elements, {len(current_chunk)} chars")
                        
                        current_chunk = html_str
                        current_elements = [el]
                    else:
                        current_chunk += html_str + "\n\n"
                        current_elements.append(el)
                        
                if current_chunk:
                    chunk_count += 1
                    chunk_data = {
                        'element_type': element_type,
                        'html_content': current_chunk,
                        'element_count': len(current_elements)
                    }
                    chunks.append(chunk_data)
                    logging.debug(f"Created final chunk {chunk_count} for {element_type}: {len(current_elements)} elements, {len(current_chunk)} chars")
                
                logging.info(f"Created {chunk_count} chunks for {element_type} elements")
        
        total_chunks = len(chunks)
        logging.info(f"Total chunks created: {total_chunks}")
        return chunks
    
   
        # Calculate weights based on element count
        chunk_weights = []
        for chunk in chunks:
            element_count = chunk.get('element_count', 1)
            # Weight = log(element_count + 1) to balance element count
            weight = math.log(element_count + 1)
            chunk_weights.append(weight)
        
        # Distribute test cases proportionally to weights
        total_weight = sum(chunk_weights)
        distribution = {}
        allocated_tests = 0
        
        for i, weight in enumerate(chunk_weights):
            if total_weight > 0:
                # Calculate proportional allocation
                proportion = weight / total_weight
                allocated = max(1, round(total_test_cases * proportion))  # At least 1 test per chunk
                distribution[i] = allocated
                allocated_tests += allocated
            else:
                distribution[i] = 1  # Fallback: 1 test per chunk
                allocated_tests += 1
        
        # Adjust if we've allocated too many or too few tests
        difference = total_test_cases - allocated_tests
        
        if difference != 0:
            # Sort chunks by element count (highest first) for adjustment
            element_count_sorted_indices = sorted(range(len(chunks)), 
                                                key=lambda i: chunks[i].get('element_count', 1), 
                                                reverse=True)
            
            # Distribute the difference starting with chunks having most elements
            for i in element_count_sorted_indices:
                if difference == 0:
                    break
                if difference > 0:
                    distribution[i] += 1
                    difference -= 1
                elif difference < 0 and distribution[i] > 1:
                    distribution[i] -= 1
                    difference += 1
        
        logging.info(f"Test distribution calculation: total={total_test_cases}, weights={chunk_weights}, allocated={distribution}")
        return distribution

   

    def _generate_test_cases_from_chunks_with_embeddings(self, requirements: str, url: str, relevant_embeddings: List[Dict] = []) -> List[Dict]:
        """Generate test cases based on requirements and embedding context."""
        logging.info(f"Starting test case generation with {len(relevant_embeddings)} relevant embeddings")
        logging.info(f"Requirements: '{requirements}', URL: {url}")
        logging.info(f"Relevant embeddings: {relevant_embeddings}")
        
        all_test_cases = []
        
        # Load prompt template
        prompt_template = self._load_prompt("generate_test_cases_with_embeddings.txt")
        if not prompt_template:
            logging.error("Failed to load prompt template, using fallback")
            return all_test_cases   # Return empty list if prompt template is not loaded
        
        prompt = prompt_template.format(
            requirements=requirements,
            url=url,
            relevant_embeddings=relevant_embeddings
        )

        try:
            logging.debug(f"Sending GPT request for test case generation")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert QA engineer who generates test cases based on user requirements and historical page context."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            logging.debug(f"Received GPT response - Status: {response.status_code}")
            
            content = result["choices"][0]["message"]["content"]
            logging.debug(f"GPT response length: {len(content)} characters")
            logging.info(f"GPT response: {content}")
            
            # Try multiple JSON extraction strategies
            test_cases = self._extract_json_from_response(content)
            
            if test_cases:
                all_test_cases.extend(test_cases)
                logging.info(f"Generated {len(test_cases)} test cases successfully")
            else:
                logging.warning(f"No valid JSON found in response, creating fallback test case")
                # Create fallback test case
                fallback_case = self._create_fallback_test_case_general(requirements, url)
                all_test_cases.append(fallback_case)
                
        except Exception as e:
            logging.error(f"Error generating test cases: {str(e)}")
            # Create fallback test case for any other errors
            fallback_case = self._create_fallback_test_case_general(requirements, url)
            all_test_cases.append(fallback_case)
                
        return all_test_cases

    def _extract_json_from_response(self, content: str) -> List[Dict]:
        """Extract and parse JSON from GPT response using multiple strategies."""
        import json
        
        logging.debug(f"Starting JSON extraction from response of length: {len(content)}")
        logging.debug(f"Response preview: {content[:200]}...")
        
        # Strategy 0: Direct JSON parsing (if content is already clean JSON)
        try:
            cleaned_content = self._clean_json_string(content)
            test_cases = json.loads(cleaned_content)
            if isinstance(test_cases, list) and test_cases:
                logging.info(f"Successfully parsed JSON directly")
                return test_cases
        except json.JSONDecodeError as e:
            logging.debug(f"Direct parsing failed: {str(e)}")
        
        # Strategy 0.5: Try to extract JSON from markdown code blocks first
        try:
            # Look for ```json ... ``` pattern
            code_block_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
            if code_block_match:
                json_content = code_block_match.group(1)
                logging.debug(f"Strategy 0.5 - Found JSON in code block: {json_content[:100]}...")
                test_cases = json.loads(json_content)
                if isinstance(test_cases, list) and test_cases:
                    logging.info(f"Successfully extracted JSON from code block")
                    return test_cases
        except Exception as e:
            logging.debug(f"Code block extraction failed: {str(e)}")
        
        # Strategy 1: Look for JSON array with regex
        json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if json_match:
            try:
                json_content = json_match.group()
                logging.debug(f"Strategy 1 - Found JSON array: {json_content[:100]}...")
                cleaned_json = self._clean_json_string(json_content)
                test_cases = json.loads(cleaned_json)
                if isinstance(test_cases, list) and test_cases:
                    logging.info(f"Successfully extracted JSON using regex strategy")
                    return test_cases
            except json.JSONDecodeError as e:
                logging.debug(f"Regex strategy failed: {str(e)}")
                logging.debug(f"Failed content: {json_content[:200]}...")
        
        # Strategy 2: Look for JSON object with regex (single test case)
        json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                json_content = json_match.group()
                cleaned_json = self._clean_json_string(json_content)
                test_case = json.loads(cleaned_json)
                if isinstance(test_case, dict) and "title" in test_case:
                    logging.info(f"Successfully extracted single test case JSON")
                    return [test_case]
            except json.JSONDecodeError as e:
                logging.debug(f"Single object strategy failed: {str(e)}")
        
        # Strategy 3: Try to find JSON between markdown code blocks
        code_block_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
        if code_block_match:
            try:
                json_content = code_block_match.group(1)
                cleaned_json = self._clean_json_string(json_content)
                test_cases = json.loads(cleaned_json)
                if isinstance(test_cases, list) and test_cases:
                    logging.info(f"Successfully extracted JSON from code block")
                    return test_cases
            except json.JSONDecodeError as e:
                logging.debug(f"Code block strategy failed: {str(e)}")
        
        # Strategy 3.5: Try to find JSON between markdown code blocks with more flexible pattern
        code_block_patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'```(.*?)```',
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```'
        ]
        
        for pattern in code_block_patterns:
            code_block_match = re.search(pattern, content, re.DOTALL)
            if code_block_match:
                logging.debug(f"Found code block match with pattern: {pattern}")
                try:
                    json_content = code_block_match.group(1)
                    logging.debug(f"Extracted content from code block: {json_content[:100]}...")
                    # Remove any language identifier at the start
                    json_content = re.sub(r'^json\s*\n', '', json_content)
                    cleaned_json = self._clean_json_string(json_content)
                    logging.debug(f"Cleaned JSON: {cleaned_json[:100]}...")
                    test_cases = json.loads(cleaned_json)
                    if isinstance(test_cases, list) and test_cases:
                        logging.info(f"Successfully extracted JSON from code block using pattern: {pattern}")
                        return test_cases
                except json.JSONDecodeError as e:
                    logging.debug(f"Code block pattern {pattern} failed: {str(e)}")
                    logging.debug(f"Failed JSON content: {json_content[:200]}...")
                    continue
        
        # Strategy 4: Try to extract multiple JSON objects
        json_objects = re.findall(r'\{[^{}]*"title"[^{}]*\}', content, re.DOTALL)
        if json_objects:
            test_cases = []
            for obj_str in json_objects:
                try:
                    cleaned_json = self._clean_json_string(obj_str)
                    test_case = json.loads(cleaned_json)
                    if isinstance(test_case, dict) and "title" in test_case:
                        test_cases.append(test_case)
                except json.JSONDecodeError:
                    continue
            
            if test_cases:
                logging.info(f"Successfully extracted {len(test_cases)} test cases from multiple objects")
                return test_cases
        
        # Strategy 5: Try to fix common JSON issues and parse
        try:
            # Remove any text before the first [ and after the last ]
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx + 1]
                cleaned_json = self._clean_json_string(json_content)
                test_cases = json.loads(cleaned_json)
                if isinstance(test_cases, list) and test_cases:
                    logging.info(f"Successfully extracted JSON using bracket strategy")
                    return test_cases
        except json.JSONDecodeError as e:
            logging.debug(f"Bracket strategy failed: {str(e)}")
        
        # Strategy 6: Last resort - try to extract JSON from the entire content
        logging.debug("Trying last resort strategy - extracting JSON from entire content")
        try:
            # Try to find any JSON-like structure
            # Look for content that starts with [ and ends with ]
            lines = content.split('\n')
            json_start = -1
            json_end = -1
            
            for i, line in enumerate(lines):
                if '[' in line and json_start == -1:
                    json_start = i
                if ']' in line and json_start != -1:
                    json_end = i
                    break
            
            if json_start != -1 and json_end != -1:
                json_lines = lines[json_start:json_end + 1]
                json_content = '\n'.join(json_lines)
                logging.debug(f"Last resort - extracted JSON content: {json_content[:200]}...")
                cleaned_json = self._clean_json_string(json_content)
                test_cases = json.loads(cleaned_json)
                if isinstance(test_cases, list) and test_cases:
                    logging.info(f"Successfully extracted JSON using last resort strategy")
                    return test_cases
        except Exception as e:
            logging.debug(f"Last resort strategy failed: {str(e)}")
        
        # Strategy 7: Try to find JSON array with more specific pattern
        try:
            # Look for content that starts with [ and contains objects with "title"
            pattern = r'\[\s*\{\s*"title"[^\]]*\]'
            json_match = re.search(pattern, content, re.DOTALL)
            if json_match:
                json_content = json_match.group()
                logging.debug(f"Strategy 7 - Found JSON with title pattern: {json_content[:200]}...")
                cleaned_json = self._clean_json_string(json_content)
                test_cases = json.loads(cleaned_json)
                if isinstance(test_cases, list) and test_cases:
                    logging.info(f"Successfully extracted JSON using title pattern strategy")
                    return test_cases
        except Exception as e:
            logging.debug(f"Title pattern strategy failed: {str(e)}")
        
        logging.warning("All JSON extraction strategies failed")
        logging.debug(f"Full content that failed to parse: {content}")
        
        # Final debug: Try to manually extract JSON from the content
        logging.debug("Attempting manual JSON extraction...")
        try:
            # Remove any markdown code blocks
            content_clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
            # Remove any leading/trailing text
            start_idx = content_clean.find('[')
            end_idx = content_clean.rfind(']')
            if start_idx != -1 and end_idx != -1:
                manual_json = content_clean[start_idx:end_idx + 1]
                logging.debug(f"Manual extraction found: {manual_json[:200]}...")
                test_cases = json.loads(manual_json)
                if isinstance(test_cases, list) and test_cases:
                    logging.info(f"Successfully extracted JSON using manual extraction")
                    return test_cases
        except Exception as e:
            logging.debug(f"Manual extraction failed: {str(e)}")
        
        # Ultimate fallback: Try to parse the entire content as JSON
        logging.debug("Attempting ultimate fallback - parse entire content as JSON")
        try:
            # This should work for the JSON you provided
            test_cases = json.loads(content)
            if isinstance(test_cases, list) and test_cases:
                logging.info(f"Successfully parsed entire content as JSON")
                return test_cases
        except Exception as e:
            logging.debug(f"Ultimate fallback failed: {str(e)}")
        
        return []

    def _clean_json_string(self, json_str: str) -> str:
        """Clean and fix common JSON formatting issues."""
        # Remove any leading/trailing whitespace
        cleaned = json_str.strip()
        
        # Remove markdown code block markers if present
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)
        
        # Keep original formatting - don't normalize newlines
        # This preserves the JSON structure better
        
        # Remove trailing commas before } and ]
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        
        # Fix common HTML entity issues in the JSON
        cleaned = cleaned.replace('&quot;', '"')
        cleaned = cleaned.replace('&amp;', '&')
        cleaned = cleaned.replace('&lt;', '<')
        cleaned = cleaned.replace('&gt;', '>')
        
        # Ensure proper JSON structure
        cleaned = cleaned.strip()
        
        logging.debug(f"Cleaned JSON string: {cleaned[:200]}...")
        
        return cleaned

    def _create_fallback_test_case_general(self, requirements: str, url: str) -> Dict:
        """Create a fallback test case when JSON parsing fails."""
        return {
            "title": f"Fallback test based on requirements",
            "description": f"Basic test case based on requirements: {requirements}",
            "expected_behavior": f"Verify functionality based on requirements",
            "test_steps": [
                f"Navigate to {url}",
                "Locate relevant elements",
                "Test functionality based on requirements"
            ],
            "element_type": "general",
            "test_type": "functional",
            "html_code": f"<!-- Test for {url} based on requirements: {requirements} -->"
        }

    def _create_fallback_test_case(self, chunk: Dict, requirements: str, chunk_num: int) -> Dict:
        """Create a fallback test case when JSON parsing fails."""
        element_type = chunk.get('element_type', 'element')
        return {
            "title": f"Fallback {element_type} test - Chunk {chunk_num}",
            "description": f"Test {element_type} elements based on: {requirements}",
            "expected_behavior": f"{element_type} elements should function correctly",
            "test_steps": [
                f"Navigate to the page",
                f"Locate {element_type} elements",
                f"Test {element_type} functionality based on requirements"
            ],
            "element_type": element_type,
            "test_type": "functional",
            "chunk_number": chunk_num,
            "html_chunk": chunk['html_content'][:1000] + "..." if len(chunk['html_content']) > 1000 else chunk['html_content']
        }

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain name from URL for collection naming."""
        parsed = urlparse(url)
        return parsed.netloc.replace('.', '_').replace('-', '_')

    def _get_url_path(self, url: str) -> str:
        """Extract URL path for metadata."""
        parsed = urlparse(url)
        return parsed.path or '/'

    def _check_embedding_exists(self, domain: str, url: str) -> bool:
        """Check if embedding already exists for the URL."""
        try:
            collection = self.chroma_client.get_collection(name=domain)
            results = collection.get(
                where={"url": url},
                limit=1
            )
            return len(results['ids']) > 0
        except:
            return False

    def _create_embeddings(self, domain: str, url: str, page_data: Dict) -> None:
        """Create and store embeddings for page content in chunks of 1000 characters."""
        try:
            # Get or create collection
            try:
                collection = self.chroma_client.get_collection(name=domain)
            except:
                collection = self.chroma_client.create_collection(name=domain)

            # Prepare content chunks
            content_chunks = []
            
            # Add title as first chunk
            if page_data.get('title'):
                content_chunks.append({
                    'content': f"Page Title: {page_data['title']}",
                    'chunk_type': 'title',
                    'chunk_index': 0
                })
            
            # Add meta description as chunk
            if page_data.get('meta_description'):
                content_chunks.append({
                    'content': f"Page Description: {page_data['meta_description']}",
                    'chunk_type': 'meta_description',
                    'chunk_index': len(content_chunks)
                })
            
            # Add meta keywords as chunk
            if page_data.get('meta_keywords'):
                content_chunks.append({
                    'content': f"Page Keywords: {page_data['meta_keywords']}",
                    'chunk_type': 'meta_keywords',
                    'chunk_index': len(content_chunks)
                })
            
            # Split text content into chunks
            if page_data.get('text_content'):
                text_content = page_data['text_content']
                text_chunks = self._split_text_into_chunks(text_content, 1000)
                for i, chunk in enumerate(text_chunks):
                    content_chunks.append({
                        'content': f"Text Content (Part {i+1}): {chunk}",
                        'chunk_type': 'text_content',
                        'chunk_index': len(content_chunks)
                    })
            
            # Split HTML content into chunks
            if page_data.get('html'):
                html_content = page_data['html']
                html_chunks = self._split_text_into_chunks(html_content, 1000)
                for i, chunk in enumerate(html_chunks):
                    content_chunks.append({
                        'content': f"HTML Structure (Part {i+1}): {chunk}",
                        'chunk_type': 'html_structure',
                        'chunk_index': len(content_chunks)
                    })
            
            # Add JavaScript content as chunks
            if page_data.get('scripts'):
                scripts_content = page_data['scripts']
                scripts_chunks = self._split_text_into_chunks(scripts_content, 1000)
                for i, chunk in enumerate(scripts_chunks):
                    content_chunks.append({
                        'content': f"JavaScript (Part {i+1}): {chunk}",
                        'chunk_type': 'javascript',
                        'chunk_index': len(content_chunks)
                    })
            
            # Add CSS content as chunks
            if page_data.get('styles'):
                styles_content = page_data['styles']
                styles_chunks = self._split_text_into_chunks(styles_content, 1000)
                for i, chunk in enumerate(styles_chunks):
                    content_chunks.append({
                        'content': f"CSS (Part {i+1}): {chunk}",
                        'chunk_type': 'css',
                        'chunk_index': len(content_chunks)
                    })

            # Prepare documents, metadatas, and ids for batch insertion
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk_data in enumerate(content_chunks):
                # Base metadata
                metadata = {
                    "url": url,
                    "domain": domain,
                    "path": self._get_url_path(url),
                    "title": page_data.get('title', ''),
                    "meta_description": page_data.get('meta_description', ''),
                    "meta_keywords": page_data.get('meta_keywords', ''),
                    "content_length": len(page_data.get('html', '')),
                    "text_length": len(page_data.get('text_content', '')),
                    "has_scripts": bool(page_data.get('scripts')),
                    "has_styles": bool(page_data.get('styles')),
                    "timestamp": str(asyncio.get_event_loop().time()),
                    "chunk_type": chunk_data['chunk_type'],
                    "chunk_index": chunk_data['chunk_index'],
                    "total_chunks": len(content_chunks),
                    "chunk_content_length": len(chunk_data['content'])
                }
                
                documents.append(chunk_data['content'])
                metadatas.append(metadata)
                ids.append(f"{domain}_{hash(url)}_chunk_{i}")

            # Add all chunks to collection in batch
            if documents:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logging.info(f"Created {len(documents)} embedding chunks for {url} in collection {domain}")
                logging.info(f"Chunk types: {[chunk['chunk_type'] for chunk in content_chunks]}")
            else:
                logging.warning(f"No content chunks created for {url}")

        except Exception as e:
            logging.error(f"Error creating embeddings for {url}: {str(e)}")

    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into chunks of specified size, trying to break at word boundaries."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this is not the last chunk, try to break at a word boundary
            if end < len(text):
                # Look for the last space or newline within the chunk
                last_space = text.rfind(' ', start, end)
                last_newline = text.rfind('\n', start, end)
                break_point = max(last_space, last_newline)
                
                if break_point > start:
                    end = break_point + 1
            
            chunks.append(text[start:end].strip())
            start = end
        
        return chunks

    def _get_relevant_embeddings(self, domain: str, requirements: str, max_distance: float = 2.0) -> List[Dict]:
        """Retrieve relevant embeddings based on requirements."""
        try:
            collection = self.chroma_client.get_collection(name=domain)
            
            # First try with requirements as query
            results = collection.query(
                query_texts=[requirements],
                n_results=4,
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
                            'metadata': all_results['metadatas'][i],
                            'distance': 3.0  # High distance to indicate it's a fallback
                        })
                    logging.info(f"Using {len(relevant_docs)} fallback embeddings from domain")
            else:
                logging.info(f"Found {len(relevant_docs)} relevant embeddings for requirements")
            
            return relevant_docs
            
        except Exception as e:
            logging.error(f"Error retrieving embeddings: {str(e)}")
            return []

    async def process_chat_message(self, user_message: str) -> Dict:
        """Process user chat message and return test cases."""
        logging.info(f"=== Starting chat message processing ===")
        logging.info(f"User message length: {len(user_message)} characters")
        
        # Extract URL, requirements, and test case count
        url, requirements = self.extract_url_and_requirements(user_message)
        
        if not url:
            logging.error("Chat processing failed: No URL found in message")
            return {
                "error": "No URL found in message",
                "message": "Please provide a valid URL in your message"
            }
            
        if not requirements:
            logging.error("Chat processing failed: No test requirements found")
            return {
                "error": "No test requirements found",
                "message": "Please specify what you want to test along with the URL"
            }
            
        try:
            logging.info(f"Starting full processing pipeline for URL: {url}")
            
            # Get domain for ChromaDB collection
            domain = self._get_domain_from_url(url)
            
            # Check if embedding already exists
            if not self._check_embedding_exists(domain, url):
                logging.info(f"Creating embeddings for {url}")
                # Fetch HTML content
                page_data = await self._fetch_rendered_html_async(url)
                
                # Create embeddings
                self._create_embeddings(domain, url, page_data)
                html_content = page_data['html']
            else:
                logging.info(f"Embeddings already exist for {url}")
                # Fetch HTML content for current processing
                page_data = await self._fetch_rendered_html_async(url)
                html_content = page_data['html']
            
            # Get relevant embeddings for requirements
            relevant_embeddings = self._get_relevant_embeddings(domain, requirements, 2.0)
            if not relevant_embeddings:
                logging.info(f"No embeddings found for domain {domain}, will use current page content only")
            else:
                embedding_types = [("Fallback" if emb['distance'] >= 3.0 else "Relevant") for emb in relevant_embeddings]
                logging.info(f"Found {len(relevant_embeddings)} embeddings for domain {domain}: {embedding_types}")
            

            
            # Generate test cases with embedding context
            test_cases = self._generate_test_cases_from_chunks_with_embeddings(
                requirements, url, relevant_embeddings
            )
            
            success_result = {
                "url": url,
                "requirements": requirements,
                "test_cases": test_cases,
                "total_cases": len(test_cases),
                "message": f"Generated {len(test_cases)} test cases based on your requirements"
            }
            
            logging.info(f"=== Chat processing completed successfully ===")
            logging.info(f"Generated {len(test_cases)} test cases based on requirements and embeddings")
            
            return success_result
            
        except Exception as e:
            logging.error(f"=== Chat processing failed with exception ===")
            logging.error(f"Error type: {type(e).__name__}")
            logging.error(f"Error message: {str(e)}")
            logging.error(f"Error occurred while processing URL: {url}")
            logging.error(f"Requirements: {requirements}")
            
            return {
                "error": "Processing error",
                "message": f"Error processing your request: {str(e)}"
            }
