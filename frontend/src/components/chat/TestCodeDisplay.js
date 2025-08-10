import React, { useState } from 'react';

const TestCodeDisplay = ({ testCode, filename, status, onEdit, onRemove, index }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedCode, setEditedCode] = useState(testCode);
  
  // Clean up the test code by removing markdown code blocks
  const cleanEditedCode = editedCode.replace(/```python\n?/g, '').replace(/```\n?/g, '').trim();

  const handleEdit = () => {
    setIsEditing(true);
    setEditedCode(testCode);
  };

  const handleSave = () => {
    // Use the cleaned code (without markdown markers) when saving
    onEdit(index, cleanEditedCode);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedCode(testCode);
    setIsEditing(false);
  };

  return (
    <div className="test-code-display">
      <div className="test-code-header">
        <h4>Generated Test Code</h4>
        <div className="test-code-actions">
          <span className={`status ${status}`}>{status}</span>
          {!isEditing ? (
            <>
              <button onClick={handleEdit} className="edit-btn">
                Edit
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
        <textarea
          className="code-editor"
          value={editedCode}
          onChange={(e) => setEditedCode(e.target.value)}
          placeholder="Edit your test code here..."
        />
      ) : (
        <pre className="code-block">
          <code>{cleanEditedCode}</code>
        </pre>
      )}
    </div>
  );
};

export default TestCodeDisplay;
