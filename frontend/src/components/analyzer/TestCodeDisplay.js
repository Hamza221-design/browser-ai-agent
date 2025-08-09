import React, { useState } from 'react';

const TestCodeDisplay = ({ testCode, filename, status, onEdit, onRemove, index }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedCode, setEditedCode] = useState(testCode);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);
  
  // Clean up the test code by removing markdown code blocks
  const cleanEditedCode = editedCode.replace(/```python\n?/g, '').replace(/```\n?/g, '').trim();

  const handleDownload = () => {
    const blob = new Blob([cleanEditedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedCode(testCode);
  };

  const handleSave = () => {
    onEdit(index, editedCode);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedCode(testCode);
    setIsEditing(false);
  };

  const handleRemove = () => {
    if (window.confirm('Are you sure you want to remove this test code?')) {
      onRemove(index);
    }
  };

  const handleRunTest = async (headless = false) => {
    setIsRunning(true);
    setRunResult(null);
    
    try {
      // For now, we'll show instructions since we can't directly execute Python in the browser
      const instructions = `
To run this test:

1. Save the code to a file named "${filename}"
2. Install dependencies: pip install playwright pytest
3. Install browsers: playwright install
4. Run the test: ${headless ? 'python ' + filename : 'python ' + filename + ' (browser mode)'}

${headless ? 'Note: Running in headless mode (no visible browser)' : 'Note: Running in browser mode (visible browser window)'}
      `;
      
      setRunResult({
        success: true,
        message: instructions,
        headless: headless
      });
    } catch (error) {
      setRunResult({
        success: false,
        message: `Error: ${error.message}`,
        headless: headless
      });
    } finally {
      setIsRunning(false);
    }
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
              <button onClick={handleRemove} className="remove-btn">
                Remove
              </button>
              <button onClick={() => handleRunTest(false)} className="run-test-btn" disabled={isRunning}>
                {isRunning ? 'Running...' : 'Run Test (Browser)'}
              </button>
              <button onClick={() => handleRunTest(true)} className="run-test-headless-btn" disabled={isRunning}>
                {isRunning ? 'Running...' : 'Run Test (Headless)'}
              </button>
              <button onClick={handleDownload} className="download-btn">
                Download {filename}
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
      
      {runResult && (
        <div className={`run-result ${runResult.success ? 'success' : 'error'}`}>
          <h5>Test Execution Instructions:</h5>
          <pre>{runResult.message}</pre>
        </div>
      )}
    </div>
  );
};

export default TestCodeDisplay;
