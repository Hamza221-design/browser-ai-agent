import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Navigation from './components/Navigation';
import HomePage from './pages/HomePage';
import AnalyzerPage from './pages/AnalyzerPage';
import ChatPage from './pages/ChatPage';
import UnifiedChatPage from './pages/UnifiedChatPage';
import StreamingChatPage from './pages/StreamingChatPage';

function App() {
  return (
    <Router>
      <div className="App">
        <Navigation />
        
        <main className="App-main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/analyzer" element={<AnalyzerPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/unified-chat" element={<UnifiedChatPage />} />
            <Route path="/streaming-chat" element={<StreamingChatPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
