import React from 'react';

const UrlForm = ({ url, setUrl, extractElements, setExtractElements, testTypes, setTestTypes, onSubmit, loading }) => {
  const availableElements = ['forms', 'links', 'buttons', 'inputs', 'images', 'tables'];
  const availableTestTypes = ['functional', 'validation', 'negative', 'positive', 'error_handling', 'performance', 'security'];

  return (
    <form onSubmit={onSubmit} className="analyzer-form">
      <div className="input-group">
        <label htmlFor="url">Website URL:</label>
        <input
          type="url"
          id="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          required
        />
      </div>

      <div className="input-group">
        <label>Elements to Extract:</label>
        <div className="checkbox-group">
          {availableElements.map(element => (
            <label key={element} className="checkbox-item">
              <input
                type="checkbox"
                checked={extractElements.includes(element)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setExtractElements([...extractElements, element]);
                  } else {
                    setExtractElements(extractElements.filter(item => item !== element));
                  }
                }}
              />
              {element}
            </label>
          ))}
        </div>
      </div>

      <div className="input-group">
        <label>Test Types:</label>
        <div className="checkbox-group">
          {availableTestTypes.map(testType => (
            <label key={testType} className="checkbox-item">
              <input
                type="checkbox"
                checked={testTypes.includes(testType)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setTestTypes([...testTypes, testType]);
                  } else {
                    setTestTypes(testTypes.filter(item => item !== testType));
                  }
                }}
              />
              {testType}
            </label>
          ))}
        </div>
      </div>

      <button type="submit" disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze Website'}
      </button>
    </form>
  );
};

export default UrlForm;
