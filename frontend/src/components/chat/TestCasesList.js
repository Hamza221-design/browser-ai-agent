import React, { useState } from 'react';
import TestCaseItem from './TestCaseItem';
import apiService from '../../services/apiService';

const TestCasesList = ({ testCases, onGenerateCode, onGenerateAllCodes, currentUrl, onEditTestCase, onRemoveTestCase, onAddToContext }) => {
  const [generatedCodes, setGeneratedCodes] = useState({});
  const [generatingIndex, setGeneratingIndex] = useState(null);
  const [executionResults, setExecutionResults] = useState({});
  const [executingIndex, setExecutingIndex] = useState(null);

  const handleGenerateCode = async (testCase, index) => {
    setGeneratingIndex(index);
    try {
      const response = await onGenerateCode(testCase);
      setGeneratedCodes(prev => ({
        ...prev,
        [index]: response
      }));
    } catch (error) {
      console.error('Error generating code:', error);
    } finally {
      setGeneratingIndex(null);
    }
  };

  const handleGenerateAllCodes = async () => {
    setGeneratingIndex('all');
    try {
      const responses = await onGenerateAllCodes();
      const newGeneratedCodes = {};
      responses.forEach((response, index) => {
        newGeneratedCodes[index] = response;
      });
      setGeneratedCodes(newGeneratedCodes);
    } catch (error) {
      console.error('Error generating all codes:', error);
    } finally {
      setGeneratingIndex(null);
    }
  };

  const handleDownloadAllTestCases = () => {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    const filename = `test_cases_${timestamp}.md`;
    
    let content = `# Test Cases Report\n\n`;
    content += `**Generated on:** ${new Date().toLocaleString()}\n`;
    content += `**Total Test Cases:** ${testCases.length}\n\n`;
    
    testCases.forEach((testCase, index) => {
      content += `## Test Case ${index + 1}: ${testCase.title}\n\n`;
      content += `**Description:** ${testCase.description}\n\n`;
      content += `**Element Type:** ${testCase.element_type}\n\n`;
      content += `**Test Type:** ${testCase.test_type}\n\n`;
      
      if (testCase.priority) {
        content += `**Priority:** ${testCase.priority}/16\n\n`;
      }
      
      content += `**Expected Behavior:** ${testCase.expected_behavior}\n\n`;
      
      if (testCase.test_steps && testCase.test_steps.length > 0) {
        content += `**Test Steps:**\n`;
        testCase.test_steps.forEach((step, stepIndex) => {
          content += `${stepIndex + 1}. ${step}\n`;
        });
        content += `\n`;
      }
      
      if (testCase.html_code) {
        content += `**Related HTML:**\n`;
        content += `\`\`\`html\n${testCase.html_code}\n\`\`\`\n\n`;
      }
      
      // Include generated code if available
      const generatedCode = generatedCodes[index];
      if (generatedCode && generatedCode.test_code) {
        content += `**Generated Test Code:**\n`;
        content += `\`\`\`python\n${generatedCode.test_code}\n\`\`\`\n\n`;
      }
      
      content += `---\n\n`;
    });
    
    // Create and download file
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExecuteTest = async (testCase, index) => {
    setExecutingIndex(index);
    
    try {
      let generatedCode = generatedCodes[index];
      
      // If test code is not generated, generate it first
      if (!generatedCode || !generatedCode.test_code) {
        console.log('Test code not found, generating first...');
        
        try {
          const testCaseWithUrl = { ...testCase, url: currentUrl };
          generatedCode = await apiService.generateTestCode(testCaseWithUrl);
          
          // Update the generated codes state
          setGeneratedCodes(prev => ({
            ...prev,
            [index]: generatedCode
          }));
          
          console.log('Test code generated successfully');
        } catch (codeGenError) {
          console.error('Error generating test code:', codeGenError);
          setExecutionResults(prev => ({
            ...prev,
            [index]: {
              status: 'error',
              error: `Failed to generate test code: ${codeGenError.message}`,
              output: '',
              execution_time: 0
            }
          }));
          return;
        }
      }

      // Now execute the test with the generated code
      const testExecutionData = [{
        test_code: generatedCode.test_code,
        title: testCase.title,
        description: testCase.description,
        url: currentUrl
      }];

      console.log('Executing test:', testCase.title);
      const response = await apiService.executeTests(testExecutionData);
      
      setExecutionResults(prev => ({
        ...prev,
        [index]: response.results[0]
      }));
      
    } catch (error) {
      console.error('Error executing test:', error);
      setExecutionResults(prev => ({
        ...prev,
        [index]: {
          status: 'error',
          error: error.message,
          output: '',
          execution_time: 0
        }
      }));
    } finally {
      setExecutingIndex(null);
    }
  };

  const handleExecuteAllTests = async () => {
    setExecutingIndex('all');
    
    try {
      const testsToExecute = [];
      const validIndices = [];
      const newGeneratedCodes = { ...generatedCodes };

      // Process each test case
      for (let index = 0; index < testCases.length; index++) {
        const testCase = testCases[index];
        let generatedCode = generatedCodes[index];

        // Generate code if not already generated
        if (!generatedCode || !generatedCode.test_code) {
          console.log(`Generating code for test case ${index + 1}: ${testCase.title}`);
          
          try {
            const testCaseWithUrl = { ...testCase, url: currentUrl };
            generatedCode = await apiService.generateTestCode(testCaseWithUrl);
            newGeneratedCodes[index] = generatedCode;
          } catch (codeGenError) {
            console.error(`Error generating code for test case ${index + 1}:`, codeGenError);
            setExecutionResults(prev => ({
              ...prev,
              [index]: {
                status: 'error',
                error: `Failed to generate test code: ${codeGenError.message}`,
                output: '',
                execution_time: 0
              }
            }));
            continue;
          }
        }

        // Add to execution list
        testsToExecute.push({
          test_code: generatedCode.test_code,
          title: testCase.title,
          description: testCase.description,
          url: currentUrl
        });
        validIndices.push(index);
      }

      // Update generated codes state
      setGeneratedCodes(newGeneratedCodes);

      if (testsToExecute.length === 0) {
        alert('Failed to generate test codes for all test cases');
        return;
      }

      console.log(`Executing ${testsToExecute.length} tests`);
      const response = await apiService.executeTests(testsToExecute);
      
      const newResults = {};
      response.results.forEach((result, i) => {
        newResults[validIndices[i]] = result;
      });
      setExecutionResults(prev => ({ ...prev, ...newResults }));
      
    } catch (error) {
      console.error('Error executing tests:', error);
    } finally {
      setExecutingIndex(null);
    }
  };

  const handleDownloadAllCodes = () => {
    const hasGeneratedCodes = Object.keys(generatedCodes).length > 0;
    
    if (!hasGeneratedCodes) {
      alert('Please generate test codes first before downloading.');
      return;
    }
    
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    const filename = `test_codes_${timestamp}.py`;
    
    let content = `"""
Test Code Suite - Generated on ${new Date().toLocaleString()}
Total Test Cases: ${Object.keys(generatedCodes).length}
"""

import pytest
from playwright.sync_api import sync_playwright, expect
import os
import time

class TestSuite:
    def setup_class(self):
        """Setup for the entire test suite"""
        self.playwright = sync_playwright().start()
        # Set headless mode based on environment variable
        headless_mode = os.getenv('PLAYWRIGHT_HEADLESS', 'false').lower() == 'true'
        self.browser = self.playwright.chromium.launch(headless=headless_mode)
        self.context = self.browser.new_context(ignore_https_errors=True)
        
    def teardown_class(self):
        """Cleanup after all tests"""
        self.context.close()
        self.browser.close()
        self.playwright.stop()

`;

    Object.entries(generatedCodes).forEach(([index, codeData]) => {
      if (codeData && codeData.test_code) {
        const testCase = testCases[parseInt(index)];
        content += `    # Test Case ${parseInt(index) + 1}: ${testCase.title}\n`;
        content += `    # Description: ${testCase.description}\n`;
        content += `    # Element Type: ${testCase.element_type}\n`;
        content += `    # Test Type: ${testCase.test_type}\n\n`;
        
        // Clean up the generated code and add proper indentation
        let cleanCode = codeData.test_code;
        
        // Remove markdown code block markers
        cleanCode = cleanCode.replace(/^```python\s*/gm, '');
        cleanCode = cleanCode.replace(/^```\s*/gm, '');
        cleanCode = cleanCode.replace(/```$/gm, '');
        
        // Remove import statements 
        cleanCode = cleanCode.replace(/^import.*$/gm, '');
        cleanCode = cleanCode.replace(/^from.*$/gm, '');
        
        // Update function names and add proper indentation
        cleanCode = cleanCode.replace(/^def test_.*?\(.*?\):/gm, '    def test_' + (parseInt(index) + 1) + '_' + testCase.title.toLowerCase().replace(/[^a-z0-9]/g, '_') + '(self):');
        // Add proper indentation for lines that don't start with 4 spaces
        const fourSpaces = '    ';
        cleanCode = cleanCode.replace(/^(?!\s{4})/gm, fourSpaces);
        
        content += cleanCode + '\n\n';
      }
    });
    
    content += `
if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
`;
    
    // Create and download file
    const blob = new Blob([content], { type: 'text/python' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleEditTestCase = (index, editedTestCase) => {
    if (onEditTestCase) {
      onEditTestCase(index, editedTestCase);
    }
  };

  const handleRemoveTestCase = (index) => {
    if (onRemoveTestCase) {
      // Remove generated code and execution results for this test case
      setGeneratedCodes(prev => {
        const newCodes = { ...prev };
        delete newCodes[index];
        // Shift down all codes after the removed index
        const shiftedCodes = {};
        Object.keys(newCodes).forEach(key => {
          const keyNum = parseInt(key);
          if (keyNum > index) {
            shiftedCodes[keyNum - 1] = newCodes[key];
          } else {
            shiftedCodes[keyNum] = newCodes[key];
          }
        });
        return shiftedCodes;
      });

      setExecutionResults(prev => {
        const newResults = { ...prev };
        delete newResults[index];
        // Shift down all results after the removed index
        const shiftedResults = {};
        Object.keys(newResults).forEach(key => {
          const keyNum = parseInt(key);
          if (keyNum > index) {
            shiftedResults[keyNum - 1] = newResults[key];
          } else {
            shiftedResults[keyNum] = newResults[key];
          }
        });
        return shiftedResults;
      });

      onRemoveTestCase(index);
    }
  };

  return (
    <div className="test-cases-list">
      <div className="test-cases-header">
        <h3>Generated Test Cases ({testCases.length})</h3>
        <div className="header-actions">
          <button 
            onClick={handleGenerateAllCodes}
            disabled={generatingIndex === 'all'}
            className="generate-all-btn"
          >
            {generatingIndex === 'all' ? 'Generating All...' : 'Generate All Codes'}
          </button>
          
          <button 
            onClick={handleDownloadAllTestCases}
            className="download-btn primary"
            title="Download all test cases as Markdown file"
          >
            📄 Download Test Cases
          </button>
          
          <button 
            onClick={handleDownloadAllCodes}
            className="download-btn secondary"
            title="Download executable Python test code"
            disabled={Object.keys(generatedCodes).length === 0}
          >
            🐍 Download Python Code
          </button>
          
          <button 
            onClick={handleExecuteAllTests}
            className="execute-btn"
            title="Generate code (if needed) and execute all tests"
            disabled={executingIndex === 'all'}
          >
            {executingIndex === 'all' ? '🔄 Processing All...' : '▶️ Generate & Run All'}
          </button>
        </div>
      </div>
      
      <div className="test-cases-items">
        {testCases.map((testCase, index) => (
          <TestCaseItem
            key={index}
            testCase={testCase}
            index={index}
            generatedCode={generatedCodes[index]}
            isGenerating={generatingIndex === index}
            onGenerateCode={handleGenerateCode}
            executionResult={executionResults[index]}
            isExecuting={executingIndex === index}
            onExecuteTest={handleExecuteTest}
            onEdit={handleEditTestCase}
            onRemove={handleRemoveTestCase}
            onAddToContext={onAddToContext}
          />
        ))}
      </div>
    </div>
  );
};

export default TestCasesList;
