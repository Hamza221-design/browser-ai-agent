import React, { useState } from 'react';
import TestCodeDisplay from './TestCodeDisplay';

const TestCase = ({ testCase, index, onGenerateCode, generatingCode, onEdit, onRemove, generatedCode }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTestCase, setEditedTestCase] = useState({ ...testCase });

  const handleEdit = () => {
    setIsEditing(true);
    setEditedTestCase({ ...testCase });
  };

  const handleSave = () => {
    onEdit(index, editedTestCase);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedTestCase({ ...testCase });
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
    const newSteps = [...(editedTestCase.test_steps || [])];
    newSteps[stepIndex] = value;
    setEditedTestCase(prev => ({
      ...prev,
      test_steps: newSteps
    }));
  };

  const addStep = () => {
    const newSteps = [...(editedTestCase.test_steps || []), ''];
    setEditedTestCase(prev => ({
      ...prev,
      test_steps: newSteps
    }));
  };

  const removeStep = (stepIndex) => {
    const newSteps = editedTestCase.test_steps.filter((_, index) => index !== stepIndex);
    setEditedTestCase(prev => ({
      ...prev,
      test_steps: newSteps
    }));
  };

  if (isEditing) {
    return (
      <div className="test-case editing">
        <div className="test-case-header">
          <h4>Editing Test Case</h4>
          <div className="test-case-actions">
            <button onClick={handleSave} className="save-btn">
              Save
            </button>
            <button onClick={handleCancel} className="cancel-btn">
              Cancel
            </button>
          </div>
        </div>
        
        <div className="edit-form">
          <div className="input-group">
            <label>Title:</label>
            <input
              type="text"
              value={editedTestCase.title || ''}
              onChange={(e) => handleInputChange('title', e.target.value)}
              placeholder="Test case title"
            />
          </div>

          <div className="input-group">
            <label>Test Type:</label>
            <select
              value={editedTestCase.test_type || ''}
              onChange={(e) => handleInputChange('test_type', e.target.value)}
            >
              <option value="functional">Functional</option>
              <option value="validation">Validation</option>
              <option value="negative">Negative</option>
              <option value="positive">Positive</option>
              <option value="error_handling">Error Handling</option>
              <option value="performance">Performance</option>
              <option value="security">Security</option>
            </select>
          </div>

          <div className="input-group">
            <label>Element Type:</label>
            <select
              value={editedTestCase.element_type || ''}
              onChange={(e) => handleInputChange('element_type', e.target.value)}
            >
              <option value="forms">Forms</option>
              <option value="links">Links</option>
              <option value="buttons">Buttons</option>
              <option value="inputs">Inputs</option>
              <option value="images">Images</option>
              <option value="tables">Tables</option>
            </select>
          </div>

          <div className="input-group">
            <label>Description:</label>
            <textarea
              value={editedTestCase.description || ''}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Test case description"
              rows="3"
            />
          </div>

          <div className="input-group">
            <label>Expected Behavior:</label>
            <textarea
              value={editedTestCase.expected_behavior || ''}
              onChange={(e) => handleInputChange('expected_behavior', e.target.value)}
              placeholder="Expected behavior when test passes"
              rows="3"
            />
          </div>

          <div className="input-group">
            <label>Test Steps:</label>
            {(editedTestCase.test_steps || []).map((step, stepIndex) => (
              <div key={stepIndex} className="step-input">
                <input
                  type="text"
                  value={step}
                  onChange={(e) => handleStepsChange(stepIndex, e.target.value)}
                  placeholder={`Step ${stepIndex + 1}`}
                />
                <button
                  type="button"
                  onClick={() => removeStep(stepIndex)}
                  className="remove-step-btn"
                >
                  Remove
                </button>
              </div>
            ))}
            <button type="button" onClick={addStep} className="add-step-btn">
              Add Step
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="test-case">
      <div className="test-case-header">
        <h4>{testCase.title || `Test Case ${index + 1}`}</h4>
        <div className="test-case-actions">
          <button onClick={handleEdit} className="edit-btn">
            Edit
          </button>
          <button onClick={handleRemove} className="remove-btn">
            Remove
          </button>
        </div>
      </div>
      
      <div className="test-case-content">
        <div className="test-case-details">
          <p><strong>Type:</strong> {testCase.test_type}</p>
          <p><strong>Element Type:</strong> {testCase.element_type}</p>
          <p><strong>Description:</strong> {testCase.description}</p>
          {testCase.test_steps && (
            <div>
              <strong>Test Steps:</strong>
              <ol>
                {testCase.test_steps.map((step, stepIndex) => (
                  <li key={stepIndex}>{step}</li>
                ))}
              </ol>
            </div>
          )}
          {testCase.expected_behavior && (
            <p><strong>Expected Behavior:</strong> {testCase.expected_behavior}</p>
          )}
          {testCase.chunk_number && (
            <div className="chunk-info">
              <strong>Chunk:</strong> {testCase.chunk_number}
            </div>
          )}
          <button 
            onClick={() => onGenerateCode(testCase, index)}
            disabled={generatingCode}
            className="generate-code-btn"
          >
            {generatingCode ? 'Generating...' : `Generate Code for "${testCase.title}"`}
          </button>
        </div>

        {generatedCode && (
          <div className="test-case-generated-code">
            <TestCodeDisplay 
              testCode={generatedCode.test_code}
              filename={generatedCode.filename}
              status={generatedCode.status}
              onEdit={(newCode) => onEdit(index, { ...testCase, generated_code: newCode })}
              onRemove={() => onRemove(index)}
              index={index}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default TestCase;
