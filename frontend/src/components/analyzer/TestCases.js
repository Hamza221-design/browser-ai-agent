import React from 'react';
import TestCase from './TestCase';

const TestCases = ({ testCases, onGenerateCode, generatingCodeIndex, onEdit, onRemove, generatedCodes }) => {
  return (
    <div className="test-cases">
      {testCases.map((testCase, index) => (
        <TestCase 
          key={index} 
          testCase={testCase} 
          index={index} 
          onGenerateCode={onGenerateCode}
          generatingCode={generatingCodeIndex === index}
          onEdit={onEdit}
          onRemove={onRemove}
          generatedCode={generatedCodes[index]}
        />
      ))}
    </div>
  );
};

export default TestCases;
