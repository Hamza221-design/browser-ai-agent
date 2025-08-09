import React from 'react';
import { Link } from 'react-router-dom';

const HomePage = () => {
  return (
    <div className="home-page">
      <div className="hero-section">
        <h1>AI Test Generator</h1>
        <p className="hero-subtitle">
          Generate comprehensive test cases and executable code using AI
        </p>
        
        <div className="features-grid">
          <div className="feature-card">
            <h3>Web Analyzer</h3>
            <p>Analyze websites by URL and generate detailed test cases for forms, links, buttons, and more.</p>
            <Link to="/analyzer" className="feature-btn">
              Start Analyzing
            </Link>
          </div>
          
          <div className="feature-card">
            <h3>AI Chat</h3>
            <p>Describe your testing needs in natural language and let AI generate relevant test cases.</p>
            <Link to="/chat" className="feature-btn">
              Start Chatting
            </Link>
          </div>
        </div>
        
        <div className="how-it-works">
          <h2>How It Works</h2>
          <div className="steps">
            <div className="step">
              <span className="step-number">1</span>
              <h4>Provide Input</h4>
              <p>Enter a URL or describe your testing requirements</p>
            </div>
            <div className="step">
              <span className="step-number">2</span>
              <h4>AI Analysis</h4>
              <p>Our AI analyzes the page and understands your needs</p>
            </div>
            <div className="step">
              <span className="step-number">3</span>
              <h4>Generate Tests</h4>
              <p>Get comprehensive test cases and executable code</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
