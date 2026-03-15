import React from 'react';
import ChatUI from './ChatUI';
import './App.css';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="logo-wrap">
          <span className="logo-icon" aria-hidden>◇</span>
          <h1>GitLab Handbook Chatbot</h1>
        </div>
        <p className="tagline">
          Ask questions about GitLab's handbook and direction. Answers are grounded in official documentation.
        </p>
      </header>
      <main className="app-main">
        <ChatUI />
      </main>
      <footer className="app-footer">
        <p>Powered by RAG · Sources: <a href="https://about.gitlab.com/handbook/" target="_blank" rel="noopener noreferrer">Handbook</a> & <a href="https://about.gitlab.com/direction/" target="_blank" rel="noopener noreferrer">Direction</a></p>
      </footer>
    </div>
  );
}

export default App;
