// index.js
// Application entry point — mounts React app into the DOM. Keep this
// file minimal; bootstrapping and global providers (e.g., auth, i18n)
// can be added here if needed.
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);