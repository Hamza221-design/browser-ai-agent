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