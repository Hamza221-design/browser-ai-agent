import React, { useState } from 'react';
import TestCodeDisplay from './TestCodeDisplay';

const TestCaseItem = ({ testCase, index, generatedCode, isGenerating, onGenerateCode, executionResult, isExecuting, onExecuteTest, onEdit, onRemove, onAddToContext }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTestCase, setEditedTestCase] = useState(testCase);

  const handleGenerateCode = () => {
    onGenerateCode(testCase, index);
  };

  const handleExecuteTest = () => {
    onExecuteTest(testCase, index);
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedTestCase(testCase);
  };

  const handleSave = () => {
    onEdit(index, editedTestCase);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedTestCase(testCase);
    setIsEditing(false);
  };

  const handleRemove = () => {
    if (window.confirm('Are you sure you want to remove this test case?')) {
      onRemove(index);
    }
  };

  const handleInputChange = (field, value) => {
    setEditedTestCase(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleStepsChange = (stepIndex, value) => {
    const newSteps = [...editedTestCase.test_steps];
    newSteps[stepIndex] = value;
    setEditedTestCase(prev => ({
      ...prev,
      test_steps: newSteps
    }));
  };

  const addStep = () => {
    setEditedTestCase(prev => ({
      ...prev,
      test_steps: [...prev.test_steps, '']
    }));
  };

  const removeStep = (stepIndex) => {
    const newSteps = editedTestCase.test_steps.filter((_, i) => i !== stepIndex);
    setEditedTestCase(prev => ({
      ...prev,
      test_steps: newSteps
    }));
  };

  const handleAddToContext = () => {
    console.log('handleAddToContext called', { testCase, generatedCode, onAddToContext });
    if (onAddToContext) {
      onAddToContext(testCase, generatedCode);
    } else {
      console.error('onAddToContext prop is missing');
    }
  };

  return (
    <div className={`test-case-item ${isEditing ? 'editing' : ''}`}>
      <div className="test-case-header">
        <h4>{isEditing ? editedTestCase.title : testCase.title}</h4>
        <div className="test-case-actions">
          {!isEditing ? (
            <>
              <button 
                onClick={handleGenerateCode}
                disabled={isGenerating}
                className="generate-code-btn"
              >
                {isGenerating ? 'Generating...' : 'Generate Code'}
              </button>
              
              <button 
                onClick={handleExecuteTest}
                disabled={isExecuting}
                className="execute-test-btn"
                title={generatedCode ? 'Execute test' : 'Generate code and execute test'}
              >
                {isExecuting ? '🔄 Running...' : (generatedCode ? '▶️ Run Test' : '▶️ Generate & Run')}
              </button>

              <button onClick={handleAddToContext} className="add-to-context-btn">
                📎 Add to Context
              </button>

              <button onClick={handleEdit} className="edit-btn">
                Edit
              </button>
              
              <button onClick={handleRemove} className="remove-btn">
                Remove
              </button>
            </>
          ) : (
            <>
              <button onClick={handleSave} className="save-btn">
                Save
              </button>
              <button onClick={handleCancel} className="cancel-btn">
                Cancel
              </button>
            </>
          )}
        </div>
      </div>
      
      {isEditing ? (
        <div className="edit-form">
          <div className="form-group">
            <label><strong>Title:</strong></label>
            <input 
              type="text" 
              value={editedTestCase.title}
              onChange={(e) => handleInputChange('title', e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label><strong>Type:</strong></label>
            <input 
              type="text" 
              value={editedTestCase.test_type}
              onChange={(e) => handleInputChange('test_type', e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label><strong>Element:</strong></label>
            <input 
              type="text" 
              value={editedTestCase.element_type}
              onChange={(e) => handleInputChange('element_type', e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label><strong>Description:</strong></label>
            <textarea 
              value={editedTestCase.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label><strong>Expected Behavior:</strong></label>
            <textarea 
              value={editedTestCase.expected_behavior || ''}
              onChange={(e) => handleInputChange('expected_behavior', e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label><strong>Test Steps:</strong></label>
            {editedTestCase.test_steps && editedTestCase.test_steps.map((step, stepIndex) => (
              <div key={stepIndex} className="step-input">
                <input 
                  type="text" 
                  value={step}
                  onChange={(e) => handleStepsChange(stepIndex, e.target.value)}
                  placeholder={`Step ${stepIndex + 1}`}
                />
                <button onClick={() => removeStep(stepIndex)} className="remove-step-btn">
                  Remove
                </button>
              </div>
            ))}
            <button onClick={addStep} className="add-step-btn">
              Add Step
            </button>
          </div>
        </div>
      ) : (
        <div className="test-case-details">
          <p><strong>Type:</strong> {testCase.test_type}</p>
          <p><strong>Element:</strong> {testCase.element_type}</p>
          <p><strong>Description:</strong> {testCase.description}</p>
          
          {testCase.test_steps && (
            <div>
              <strong>Steps:</strong>
              <ol>
                {testCase.test_steps.map((step, stepIndex) => (
                  <li key={stepIndex}>{step}</li>
                ))}
              </ol>
            </div>
          )}
          
          {testCase.expected_behavior && (
            <p><strong>Expected:</strong> {testCase.expected_behavior}</p>
          )}
        </div>
      )}

      {generatedCode && (
        <div className="generated-code-section">
          <TestCodeDisplay 
            testCode={generatedCode.test_code}
            filename={generatedCode.filename}
            status={generatedCode.status}
            onEdit={() => {}}
            onRemove={() => {}}
            index={index}
          />
        </div>
      )}

      {executionResult && (
        <div className="execution-result-section">
          <h5>Test Execution Result</h5>
          <div className={`execution-status ${executionResult.status}`}>
            <strong>Status:</strong> {executionResult.status.toUpperCase()}
          </div>
          <div className="execution-time">
            <strong>Execution Time:</strong> {executionResult.execution_time}s
          </div>
          
          {executionResult.output && (
            <div className="execution-output">
              <strong>Output:</strong>
              <pre>{executionResult.output}</pre>
            </div>
          )}
          
          {executionResult.error && (
            <div className="execution-error">
              <strong>Error:</strong>
              <pre>{executionResult.error}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TestCaseItem;
