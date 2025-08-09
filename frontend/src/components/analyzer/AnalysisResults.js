import React, { useState } from 'react';
import AnalysisSummary from './AnalysisSummary';
import ElementCounts from './ElementCounts';
import TestCases from './TestCases';
import apiService from '../../services/apiService';

const AnalysisResults = ({ result, onResultUpdate }) => {
  const [generatedCodes, setGeneratedCodes] = useState({});
  const [generatingCodeIndex, setGeneratingCodeIndex] = useState(null);
  const [testCases, setTestCases] = useState(result.test_cases || []);

  // Calculate total cases from test_cases array if total_cases is not provided
  const totalCases = testCases.length;
  
  // Create element counts from test cases if element_counts is not provided
  const elementCounts = result.element_counts || (() => {
    const counts = {};
    if (testCases) {
      testCases.forEach(testCase => {
        const elementType = testCase.element_type;
        counts[elementType] = (counts[elementType] || 0) + 1;
      });
    }
    return counts;
  })();

  const handleGenerateCode = async (testCase, index) => {
    setGeneratingCodeIndex(index);
    try {
      console.log('Generating code for test case:', testCase);
      // Add URL to test case data
      const testCaseWithUrl = {
        ...testCase,
        url: result.url
      };
      const response = await apiService.generateTestCode(testCaseWithUrl);
      console.log('Generated code response:', response);
      setGeneratedCodes(prev => ({
        ...prev,
        [index]: response
      }));
    } catch (error) {
      console.error('Error generating test code:', error);
    } finally {
      setGeneratingCodeIndex(null);
    }
  };

  const handleGenerateAllCodes = async () => {
    if (!testCases || testCases.length === 0) return;
    
    setGeneratingCodeIndex('all');
    try {
      // Add URL to all test cases
      const testCasesWithUrl = testCases.map(testCase => ({
        ...testCase,
        url: result.url
      }));
      const responses = await apiService.generateMultipleTestCodes(testCasesWithUrl);
      const newGeneratedCodes = {};
      responses.forEach((response, index) => {
        newGeneratedCodes[index] = response;
      });
      setGeneratedCodes(newGeneratedCodes);
    } catch (error) {
      console.error('Error generating all test codes:', error);
    } finally {
      setGeneratingCodeIndex(null);
    }
  };

  const handleEditCode = (index, newCode) => {
    setGeneratedCodes(prev => ({
      ...prev,
      [index]: {
        ...prev[index],
        test_code: newCode
      }
    }));
  };

  const handleRemoveCode = (index) => {
    setGeneratedCodes(prev => {
      const newCodes = { ...prev };
      delete newCodes[index];
      return newCodes;
    });
  };

  const handleEditTestCase = (index, updatedTestCase) => {
    const newTestCases = [...testCases];
    newTestCases[index] = updatedTestCase;
    setTestCases(newTestCases);
    
    // Update the result object if onResultUpdate is provided
    if (onResultUpdate) {
      onResultUpdate({
        ...result,
        test_cases: newTestCases,
        total_cases: newTestCases.length
      });
    }
  };

  const handleRemoveTestCase = (index) => {
    const newTestCases = testCases.filter((_, i) => i !== index);
    setTestCases(newTestCases);
    
    // Remove any generated code for this test case
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
    
    // Update the result object if onResultUpdate is provided
    if (onResultUpdate) {
      onResultUpdate({
        ...result,
        test_cases: newTestCases,
        total_cases: newTestCases.length
      });
    }
  };

  return (
    <div className="results">
      <h2>Analysis Results</h2>
      <AnalysisSummary result={{ ...result, total_cases: totalCases }} />
      <ElementCounts elementCounts={elementCounts} />
      <div className="test-cases-header">
        <h3>Test Cases:</h3>
        <button 
          onClick={handleGenerateAllCodes}
          disabled={generatingCodeIndex === 'all'}
          className="generate-all-btn"
        >
          {generatingCodeIndex === 'all' ? 'Generating All Codes...' : 'Generate All Codes'}
        </button>
      </div>
      <TestCases 
        testCases={testCases} 
        onGenerateCode={handleGenerateCode}
        generatingCodeIndex={generatingCodeIndex}
        onEdit={handleEditTestCase}
        onRemove={handleRemoveTestCase}
        generatedCodes={generatedCodes}
      />
    </div>
  );
};

export default AnalysisResults;
