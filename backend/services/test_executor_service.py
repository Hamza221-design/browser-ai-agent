import subprocess
import tempfile
import os
import json
import asyncio
from typing import List, Dict
import logging
import re
import time
import requests

class TestExecutorService:
    def __init__(self, openai_api_key: str = None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def execute_tests(self, test_cases: List[Dict]) -> List[Dict]:
        """Execute multiple test cases and return results"""
        results = []
        
        logging.info(f"Executing {len(test_cases)} test cases")
        for i, test_case in enumerate(test_cases):
            logging.info(f"Executing test case {i+1}/{len(test_cases)}: {test_case.get('title', 'Unknown')}")
            result = await self._execute_single_test(test_case, i)
            results.append(result)
            
        # Log GPT analysis usage
        gpt_analyses = sum(1 for r in results if r.get('gpt_analysis'))
        if gpt_analyses > 0:
            logging.info(f"GPT analysis performed for {gpt_analyses} failed tests")
        
        logging.info(f"Test execution completed: {{'total': {len(test_cases)}, 'passed': {sum(1 for r in results if r.get('status') == 'passed')}, 'failed': {sum(1 for r in results if r.get('status') == 'failed')}, 'errors': {sum(1 for r in results if r.get('status') == 'error')}, 'total_execution_time': {sum(r.get('execution_time', 0) for r in results)}}}")
        return results

    async def _execute_single_test(self, test_case: Dict, index: int) -> Dict:
        """Execute a single test case"""
        try:
            # Get the test code from the test case
            test_code = test_case.get('test_code', '')
            
            if not test_code:
                logging.error(f"No test code provided for test case {index}")
                return {
                    'test_case_id': index,
                    'title': test_case.get('title', f'Test Case {index + 1}'),
                    'status': 'error',
                    'output': '',
                    'error': 'No test code provided',
                    'execution_time': 0
                }
            
            # Modify the test code to force headless mode
            modified_test_code = self._modify_headless_setting(test_code)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(modified_test_code)
                temp_file_path = temp_file.name
                
            # Log the generated test file content for debugging
            logging.debug(f"Generated test file content for '{test_case.get('title', 'Unknown')}':\n{modified_test_code}")
            logging.info(f"Created temporary test file: {temp_file_path}")

            try:
                # Execute test
                result = await self._run_pytest(temp_file_path)
                
                test_status = 'passed' if result['exit_code'] == 0 else 'failed'
                test_result = {
                    'test_case_id': index,
                    'title': test_case.get('title', f'Test Case {index + 1}'),
                    'status': test_status,
                    'output': result['output'],
                    'error': result['error'],
                    'execution_time': result['execution_time']
                }
                
                # Log test case result
                logging.info(f"Test case '{test_case.get('title', 'Unknown')}' completed: {test_status} (exit code: {result['exit_code']}, time: {result['execution_time']}s)")
                
                # If test failed, get GPT analysis for better explanation and fix suggestions
                if test_status == 'failed':
                    if self.api_key:
                        logging.info(f"Test failed, getting GPT analysis for better explanation")
                        gpt_analysis = await self._analyze_failed_test_with_gpt(test_case, result)
                        test_result['gpt_analysis'] = gpt_analysis
                    else:
                        logging.warning("Test failed but no OpenAI API key available for GPT analysis")
                        test_result['gpt_analysis'] = {
                            "error": "No OpenAI API key available",
                            "explanation": "Unable to analyze test failure automatically - OpenAI API key not configured",
                            "suggestions": ["Check the test output manually for debugging"],
                            "likely_causes": ["Unknown"],
                            "fix_priority": "medium"
                        }
                
                return test_result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logging.debug(f"Deleted temporary test file: {temp_file_path}")
                    
        except Exception as e:
            logging.error(f"Error executing test case {index}: {str(e)}")
            return {
                'test_case_id': index,
                'title': test_case.get('title', f'Test Case {index + 1}'),
                'status': 'error',
                'output': '',
                'error': str(e),
                'execution_time': 0
            }

    def _modify_headless_setting(self, test_code: str) -> str:
        """Modify the test code to force headless mode to True"""
        
        # First, remove markdown code block markers
        logging.debug(f"Original test code length: {len(test_code)} characters")
        if '```' in test_code:
            logging.debug("Removing markdown code block markers from test code")
        
        modified_code = test_code.replace('```python', '').replace('```', '').strip()
        
        # Pattern to find headless setting lines
        headless_patterns = [
            r'headless\s*=\s*os\.getenv\([^)]+\).*',
            r'headless_mode\s*=\s*os\.getenv\([^)]+\).*',
            r'headless\s*=\s*(True|False)',
            r'headless_mode\s*=\s*(True|False)'
        ]
        
        # Replace any headless setting with headless = True
        for pattern in headless_patterns:
            if re.search(pattern, modified_code, flags=re.IGNORECASE):
                logging.debug(f"Found headless pattern, replacing with 'headless = True'")
            modified_code = re.sub(pattern, 'headless = True', modified_code, flags=re.IGNORECASE)
        
        # Also replace in browser launch calls
        modified_code = re.sub(
            r'\.launch\([^)]*headless\s*=\s*[^,)]+([^)]*)\)',
            r'.launch(\1headless=True)',
            modified_code
        )
        
        # If no headless setting found, add it before browser launch
        if 'headless' not in modified_code.lower():
            # Find browser launch line and add headless setting before it
            lines = modified_code.split('\n')
            for i, line in enumerate(lines):
                if '.chromium.launch(' in line or '.firefox.launch(' in line or '.webkit.launch(' in line:
                    # Add headless = True before the launch line
                    indent = len(line) - len(line.lstrip())
                    lines.insert(i, ' ' * indent + 'headless = True')
                    # Modify the launch line to include headless parameter
                    if 'headless=' not in line:
                        line = line.replace('.launch(', '.launch(headless=headless, ')
                        lines[i+1] = line
                    break
            modified_code = '\n'.join(lines)
        
        return modified_code

    async def _analyze_failed_test_with_gpt(self, test_case: Dict, test_result: Dict) -> Dict:
        """Analyze failed test with GPT to get better explanation and fix suggestions."""
        try:
            # Prepare the analysis prompt
            prompt = self._create_failure_analysis_prompt(test_case, test_result)
            
            logging.info(f"Sending failed test analysis request to GPT")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert QA engineer and Playwright testing specialist. Analyze failed test cases and provide clear explanations of what went wrong and specific suggestions to fix the issues."
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
            
            # Parse the GPT response to extract structured information
            analysis = self._parse_gpt_analysis_response(content)
            
            logging.info(f"GPT analysis completed successfully")
            return analysis
            
        except Exception as e:
            logging.error(f"Error getting GPT analysis for failed test: {str(e)}")
            return {
                "error": f"Failed to get GPT analysis: {str(e)}",
                "explanation": "Unable to analyze the test failure automatically.",
                "suggestions": ["Check the test output manually for debugging"],
                "likely_causes": ["Unknown"],
                "fix_priority": "medium"
            }

    def _create_failure_analysis_prompt(self, test_case: Dict, test_result: Dict) -> str:
        """Create a focused prompt for analyzing test failures."""
        prompt = f"""
Analyze this failed Playwright test and provide a detailed explanation and fix suggestions.

TEST CODE:
{test_case.get('test_code', 'No test code available')}

ERROR LOGS:
{test_result.get('error', 'No errors')}

TEST OUTPUT:
{test_result.get('output', 'No output')}

Please provide a structured analysis with the following sections:

1. **Root Cause Analysis**: What is the most likely cause of this test failure?
2. **Error Explanation**: Explain the specific error in simple terms
3. **Fix Suggestions**: Provide 3-5 specific suggestions to fix the test
4. **Common Issues**: List any common Playwright issues this might be related to
5. **Priority**: Rate the fix priority as "low", "medium", or "high"
6. **Additional Context**: Any other relevant information for debugging

Format your response as JSON with these keys:
- "explanation": Brief explanation of what went wrong
- "likely_causes": Array of likely causes
- "suggestions": Array of specific fix suggestions
- "common_issues": Array of related common issues
- "fix_priority": "low", "medium", or "high"
- "additional_context": Any additional helpful information
"""
        return prompt

    def _parse_gpt_analysis_response(self, content: str) -> Dict:
        """Parse GPT response to extract structured analysis information."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                analysis = json.loads(json_str)
                
                # Ensure all required fields are present
                required_fields = ["explanation", "likely_causes", "suggestions", "common_issues", "fix_priority", "additional_context"]
                for field in required_fields:
                    if field not in analysis:
                        if field in ["likely_causes", "suggestions", "common_issues"]:
                            analysis[field] = []
                        elif field == "fix_priority":
                            analysis[field] = "medium"
                        else:
                            analysis[field] = "Not provided"
                
                return analysis
            else:
                # If no JSON found, create a structured response from the text
                return {
                    "explanation": content[:500] + "..." if len(content) > 500 else content,
                    "likely_causes": ["Unable to parse structured response"],
                    "suggestions": ["Review the test output manually"],
                    "common_issues": ["Response parsing issue"],
                    "fix_priority": "medium",
                    "additional_context": "GPT provided analysis but response format was not as expected"
                }
                
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse GPT analysis JSON: {str(e)}")
            return {
                "explanation": content[:500] + "..." if len(content) > 500 else content,
                "likely_causes": ["JSON parsing error"],
                "suggestions": ["Review the test output manually"],
                "common_issues": ["Response parsing issue"],
                "fix_priority": "medium",
                "additional_context": f"Failed to parse structured response: {str(e)}"
            }

    async def _run_pytest(self, test_file_path: str) -> Dict:
        """Run pytest on the test file"""
        start_time = time.time()
        
        try:
            # First try to check if pytest is available
            check_process = await asyncio.create_subprocess_exec(
                'python', '-c', 'import pytest; print("pytest available")',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            check_stdout, check_stderr = await check_process.communicate()
            
            if check_process.returncode != 0:
                return {
                    'exit_code': 1,
                    'output': '',
                    'error': 'pytest is not installed. Please install pytest: pip install pytest',
                    'execution_time': round(time.time() - start_time, 2)
                }
            
            # Run pytest command
            process = await asyncio.create_subprocess_exec(
                'python', '-m', 'pytest', test_file_path, '-v', '--tb=short',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time
            
            output_text = stdout.decode('utf-8') if stdout else ''
            error_text = stderr.decode('utf-8') if stderr else ''
            
            # Log the actual test output for debugging
            logging.info(f"Test execution completed with exit code: {process.returncode}")
            if output_text:
                logging.info(f"Test output:\n{output_text}")
            if error_text:
                logging.info(f"Test errors:\n{error_text}")
            
            return {
                'exit_code': process.returncode,
                'output': output_text,
                'error': error_text,
                'execution_time': round(execution_time, 2)
            }
            
        except Exception as e:
            return {
                'exit_code': 1,
                'output': '',
                'error': str(e),
                'execution_time': round(time.time() - start_time, 2)
            }