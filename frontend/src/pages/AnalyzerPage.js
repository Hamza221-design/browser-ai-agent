import React, { useState } from 'react';
import UrlForm from '../components/analyzer/UrlForm';
import ErrorDisplay from '../components/analyzer/ErrorDisplay';
import AnalysisResults from '../components/analyzer/AnalysisResults';
import apiService from '../services/apiService';

const AnalyzerPage = () => {
  const [url, setUrl] = useState('');
  const [extractElements, setExtractElements] = useState(['forms', 'links']);
  const [testTypes, setTestTypes] = useState(['functional', 'validation', 'negative', 'positive', 'error_handling']);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await apiService.analyzeWebsite(url, {
        extract_elements: extractElements,
        test_types: testTypes
      });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResultUpdate = (updatedResult) => {
    setResult(updatedResult);
  };

  return (
    <div className="analyzer-page">
      <header className="page-header">
        <h1>Web Analyzer</h1>
        <p>Analyze websites and generate comprehensive test cases</p>
      </header>
      
      <main className="page-main">
        <UrlForm 
          url={url} 
          setUrl={setUrl} 
          extractElements={extractElements}
          setExtractElements={setExtractElements}
          testTypes={testTypes}
          setTestTypes={setTestTypes}
          onSubmit={handleSubmit} 
          loading={loading} 
        />
        <ErrorDisplay error={error} />
        {result && <AnalysisResults result={result} onResultUpdate={handleResultUpdate} />}
      </main>
    </div>
  );
};

export default AnalyzerPage;
