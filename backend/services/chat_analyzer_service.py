import requests
import re
import logging
import os
import asyncio
import math
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

class ChatAnalyzerService:
    def __init__(self, openai_api_key: str):
        self.api_key = openai_api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.prompts_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')

    def extract_url_and_requirements(self, user_message: str) -> Tuple[Optional[str], Optional[str], int, Dict[str, int]]:
        """Extract URL, test requirements, number of test cases, and element priorities from user message."""
        logging.info(f"Extracting URL and requirements from message: '{user_message[:100]}...'")
        
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, user_message)
        
        if not urls:
            logging.warning("No URLs found in user message")
            return None, None, 5, {}
            
        url = urls[0]
        logging.info(f"Extracted URL: {url}")
        
        # Remove URL from message to get requirements
        requirements = re.sub(url_pattern, '', user_message).strip()
        
        if not requirements:
            logging.warning(f"No requirements found after extracting URL from message")
            return url, None, 5, {}
        
        # Extract number of test cases
        num_test_cases = self._extract_test_case_count(user_message)
        logging.info(f"Extracted test case count: {num_test_cases}")
        
        # Determine element priorities based on requirements
        element_priorities = self._determine_element_priorities(requirements)
        logging.info(f"Element priorities: {element_priorities}")
        
        logging.info(f"Extracted requirements: '{requirements}'")
        return url, requirements, num_test_cases, element_priorities
    
    def _extract_test_case_count(self, message: str) -> int:
        """Extract the number of test cases requested from user message."""
        message_lower = message.lower()
        
        # Look for explicit numbers with test case keywords
        patterns = [
            r'(\d+)\s*test\s*cases?',
            r'generate\s*(\d+)\s*tests?',
            r'create\s*(\d+)\s*tests?',
            r'(\d+)\s*tests?',
            r'about\s*(\d+)\s*test',
            r'around\s*(\d+)\s*test'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                count = int(match.group(1))
                # Reasonable bounds (1-20)
                if 1 <= count <= 20:
                    logging.info(f"Found explicit test case count: {count}")
                    return count
                    
        # Look for qualitative indicators
        if any(word in message_lower for word in ['few', 'couple', 'some']):
            logging.info("Found qualitative indicator for few tests: using 3")
            return 3
        elif any(word in message_lower for word in ['many', 'lots', 'comprehensive', 'thorough', 'complete']):
            logging.info("Found qualitative indicator for many tests: using 8")
            return 8
        elif any(word in message_lower for word in ['basic', 'simple', 'quick']):
            logging.info("Found qualitative indicator for basic tests: using 3")
            return 3
        elif any(word in message_lower for word in ['detailed', 'extensive', 'full']):
            logging.info("Found qualitative indicator for detailed tests: using 7")
            return 7
            
        # Default case
        logging.info("No test case count specified, using default: 5")
        return 5
    
    def _determine_element_priorities(self, requirements: str) -> Dict[str, int]:
        """Determine element priorities based on user requirements and default hierarchy."""
        requirements_lower = requirements.lower()
        
        # Default priority hierarchy (higher number = higher priority)
        default_priorities = {
            'forms': 10,      # Highest priority - critical user interactions
            'buttons': 9,     # High priority - action elements
            'inputs': 8,      # High priority - user input elements
            'navigation': 6,  # Medium priority - site structure
            'links': 5,       # Medium-low priority - basic navigation
            'images': 3,      # Low priority - content elements
            'tables': 4       # Low-medium priority - data display
        }
        
        # Boost priorities based on explicit mentions in requirements
        priority_boosts = {}
        
        # Keywords that boost specific element priorities
        element_keywords = {
            'forms': ['form', 'login', 'signup', 'register', 'submit', 'registration', 'contact form'],
            'buttons': ['button', 'click', 'submit', 'action', 'cta', 'call to action'],
            'inputs': ['input', 'field', 'text box', 'password', 'email', 'validation', 'data entry'],
            'navigation': ['navigation', 'nav', 'menu', 'header', 'footer', 'sidebar'],
            'links': ['link', 'anchor', 'href', 'url', 'redirect'],
            'images': ['image', 'img', 'photo', 'picture', 'gallery', 'media'],
            'tables': ['table', 'data', 'grid', 'list', 'row', 'column']
        }
        
        # Calculate priority boosts
        for element_type, keywords in element_keywords.items():
            mentions = sum(1 for keyword in keywords if keyword in requirements_lower)
            if mentions > 0:
                # Boost priority by 2 points per mention (max +6)
                boost = min(mentions * 2, 6)
                priority_boosts[element_type] = boost
                logging.info(f"Boosting {element_type} priority by {boost} points ({mentions} mentions)")
        
        # Apply boosts to default priorities
        final_priorities = {}
        for element_type, base_priority in default_priorities.items():
            boost = priority_boosts.get(element_type, 0)
            final_priorities[element_type] = base_priority + boost
        
        # Sort by priority (highest first)
        sorted_priorities = dict(sorted(final_priorities.items(), key=lambda x: x[1], reverse=True))
        
        logging.info(f"Final element priorities: {sorted_priorities}")
        return sorted_priorities

    async def _fetch_rendered_html_async(self, url: str) -> str:
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
                
                html = await page.content()
                html_length = len(html)
                logging.info(f"Successfully fetched HTML for {url} - Content length: {html_length} characters")
                
                await browser.close()
                logging.debug("Browser closed successfully")
                
                return html
                
        except Exception as e:
            logging.error(f"Failed to fetch HTML for URL {url}: {str(e)}")
            logging.error(f"Error type: {type(e).__name__}")
            raise

    def _extract_elements_by_requirements(self, html_content: str, requirements: str, element_priorities: Dict[str, int] = {}) -> Dict[str, List]:
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
            
        # If no specific elements found, extract elements based on priorities
        if not elements:
            logging.warning("No specific keywords detected, extracting elements based on priority")
            # Use priorities if available, otherwise use default order
            priority_order = list(element_priorities.keys()) if element_priorities else ['forms', 'buttons', 'inputs', 'links']
            
            for element_type in priority_order:
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
        
        # Sort elements by priority for processing order
        if element_priorities:
            sorted_elements = {}
            for element_type in sorted(element_priorities.keys(), key=lambda x: element_priorities[x], reverse=True):
                if element_type in elements and elements[element_type]:
                    sorted_elements[element_type] = elements[element_type]
            # Add any remaining elements not in priorities
            for element_type, element_list in elements.items():
                if element_type not in sorted_elements and element_list:
                    sorted_elements[element_type] = element_list
            elements = sorted_elements
            
        # Log element counts
        element_counts = {k: len(v) for k, v in elements.items() if v}
        logging.info(f"Elements extracted (in priority order): {element_counts}")
        
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
    
    def _calculate_test_distribution(self, chunks: List[Dict], total_test_cases: int, element_priorities: Dict[str, int]) -> Dict[int, int]:
        """Calculate how many test cases to generate for each chunk based on priorities."""
        if not chunks:
            return {}
            
        # Calculate priority weights for each chunk
        chunk_weights = []
        for chunk in chunks:
            element_type = chunk['element_type']
            priority = element_priorities.get(element_type, 5)  # Default priority 5
            element_count = chunk.get('element_count', 1)
            
            # Weight = priority * log(element_count + 1) to balance priority and element count
            weight = priority * math.log(element_count + 1)
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
            # Sort chunks by priority (highest first) for adjustment
            priority_sorted_indices = sorted(range(len(chunks)), 
                                           key=lambda i: element_priorities.get(chunks[i]['element_type'], 5), 
                                           reverse=True)
            
            # Distribute the difference starting with highest priority chunks
            for i in priority_sorted_indices:
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

    def _generate_test_cases_from_chunks(self, chunks: List[Dict], requirements: str, url: str, num_test_cases: int = 5, element_priorities: Dict[str, int] = {}) -> List[Dict]:
        """Generate test cases from HTML chunks based on requirements."""
        logging.info(f"Starting test case generation for {len(chunks)} chunks")
        logging.info(f"Requirements: '{requirements}', URL: {url}, Requested test cases: {num_test_cases}")
        
        all_test_cases = []
        
        # Calculate test cases per chunk based on element priorities
        chunk_test_distribution = self._calculate_test_distribution(chunks, num_test_cases, element_priorities)
        logging.info(f"Test case distribution: {chunk_test_distribution}")
        
        for i, chunk in enumerate(chunks):
            chunk_num = i + 1
            chunk_test_count = chunk_test_distribution.get(i, 2)  # Default to 2 if not specified
            
            logging.info(f"Processing chunk {chunk_num}/{len(chunks)} - Element type: {chunk['element_type']}, Elements: {chunk['element_count']}, Test cases to generate: {chunk_test_count}")
            
            # Get priority information for this element type
            element_priority = element_priorities.get(chunk['element_type'], 5)
            priority_context = f"Priority level: {element_priority}/16 (higher means more important)"
            
            prompt = f"""
Based on the user requirements and HTML content, generate {chunk_test_count} comprehensive test cases.

User Requirements: {requirements}
Target URL: {url}
Element Type: {chunk['element_type']}
{priority_context}
HTML Content:
{chunk['html_content']}

**Important**
- Generate exactly {chunk_test_count} test cases
- Create well defined test cases that are necessary for the user requirements
- Focus on the most important scenarios for {chunk['element_type']} elements
- Consider the priority level when selecting test scenarios


Provide JSON response:
[
    {{
        "title": "Descriptive test case title",
        "description": "Clear description matching user requirements",
        "expected_behavior": "Expected outcome when test passes",
        "test_steps": ["Step 1", "Step 2", "Step 3"],
        "element_type": "{chunk['element_type']}",
        "test_type": "functional|validation|negative|positive",
        "html_code": "HTML code of the test case you generated based on the code and user requirements",
        "chunk_number": {chunk_num},
        "priority": {element_priority}
    }}
]
"""

            try:
                logging.debug(f"Sending GPT request for chunk {chunk_num}")
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert QA engineer who generates test cases based on user requirements."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500
                }
                
                response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
                response.raise_for_status()
                result = response.json()
                
                logging.debug(f"Received GPT response for chunk {chunk_num} - Status: {response.status_code}")
                
                content = result["choices"][0]["message"]["content"]
                logging.debug(f"GPT response length for chunk {chunk_num}: {len(content)} characters")
                
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                
                if json_match:
                    import json
                    try:
                        json_content = json_match.group()
                        # Clean up common JSON issues
                        json_content = json_content.replace('\n', ' ').replace('\r', ' ')
                        json_content = re.sub(r',\s*}', '}', json_content)  # Remove trailing commas before }
                        json_content = re.sub(r',\s*]', ']', json_content)  # Remove trailing commas before ]
                        
                        test_cases = json.loads(json_content)
                        for test_case in test_cases:
                            test_case["html_chunk"] = chunk['html_content'][:1000] + "..." if len(chunk['html_content']) > 1000 else chunk['html_content']
                        all_test_cases.extend(test_cases)
                        logging.info(f"Generated {len(test_cases)} test cases for chunk {i+1}")
                    except json.JSONDecodeError as json_error:
                        logging.error(f"JSON decode error for chunk {i+1}: {str(json_error)}")
                        logging.debug(f"Problematic JSON: {json_match.group()[:500]}...")
                        # Create fallback test case
                        fallback_case = self._create_fallback_test_case(chunk, requirements, i+1)
                        all_test_cases.append(fallback_case)
                else:
                    logging.warning(f"No JSON found in response for chunk {i+1}")
                    # Create fallback test case
                    fallback_case = self._create_fallback_test_case(chunk, requirements, i+1)
                    all_test_cases.append(fallback_case)
                    
            except Exception as e:
                logging.error(f"Error generating test cases for chunk {i+1}: {str(e)}")
                # Create fallback test case for any other errors
                fallback_case = self._create_fallback_test_case(chunk, requirements, i+1)
                all_test_cases.append(fallback_case)
                
        return all_test_cases

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

    async def process_chat_message(self, user_message: str) -> Dict:
        """Process user chat message and return test cases."""
        logging.info(f"=== Starting chat message processing ===")
        logging.info(f"User message length: {len(user_message)} characters")
        
        # Extract URL, requirements, test case count, and element priorities
        url, requirements, num_test_cases, element_priorities = self.extract_url_and_requirements(user_message)
        
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
            
            # Fetch HTML content
            html_content = await self._fetch_rendered_html_async(url)
            
            # Extract relevant elements based on requirements and priorities
            elements = self._extract_elements_by_requirements(html_content, requirements, element_priorities)
            
            if not any(elements.values()):
                logging.error("Chat processing failed: No relevant elements found on page")
                return {
                    "error": "No relevant elements found",
                    "message": "No elements matching your requirements were found on the page"
                }
                
            # Create chunks
            chunks = self._create_chunks(elements)
            
            # Generate test cases
            test_cases = self._generate_test_cases_from_chunks(chunks, requirements, url, num_test_cases, element_priorities)
            
            # Calculate element counts
            element_counts = {k: len(v) for k, v in elements.items() if v}
            
            success_result = {
                "url": url,
                "requirements": requirements,
                "test_cases": test_cases,
                "total_cases": len(test_cases),
                "element_counts": element_counts,
                "message": f"Generated {len(test_cases)} test cases based on your requirements"
            }
            
            logging.info(f"=== Chat processing completed successfully ===")
            logging.info(f"Generated {len(test_cases)} test cases for {len(chunks)} chunks")
            logging.info(f"Element counts: {element_counts}")
            
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
