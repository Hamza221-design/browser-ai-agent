import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navigation = () => {
  const location = useLocation();

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <h2>AI Test Generator</h2>
        </div>
        
        <div className="nav-links">
          <Link 
            to="/analyzer" 
            className={`nav-link ${location.pathname === '/analyzer' ? 'active' : ''}`}
          >
            Web Analyzer
          </Link>
          <Link 
            to="/chat" 
            className={`nav-link ${location.pathname === '/chat' ? 'active' : ''}`}
          >
            AI Chat
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
