import React from 'react';

const AnalysisSummary = ({ result }) => {
  return (
    <div className="summary">
      <p><strong>URL:</strong> {result.url}</p>
      <p><strong>Total Test Cases:</strong> {result.total_cases}</p>
    </div>
  );
};

export default AnalysisSummary;
