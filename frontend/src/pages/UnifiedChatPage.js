import React, { useState, useRef, useEffect } from 'react';
import UnifiedChatInterface from '../components/unified-chat/UnifiedChatInterface';

const UnifiedChatPage = () => {
  return (
    <div className="unified-chat-page">
      <header className="page-header">
        <h1>🤖 AI Testing Assistant</h1>
        <p>Chat naturally with AI to analyze websites, generate tests, and execute them</p>
      </header>
      
      <main className="page-main">
        <UnifiedChatInterface />
      </main>
    </div>
  );
};

export default UnifiedChatPage; 