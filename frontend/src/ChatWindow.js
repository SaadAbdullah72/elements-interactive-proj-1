// ChatWindow.js
// Purpose: Generic chat UI used by consultation screens. Renders
// messages, typing state, file uploads, and the input box.
// Design note: Keep this component presentation-focused; send/receive
// network calls via parent props (`onSendMessage`, `onPhotoUpload`).
import React, { useState, useRef, useEffect } from 'react';
import Message from './Message';
import TypingIndicator from './TypingIndicator';
import { FiPaperclip, FiSend, FiImage } from 'react-icons/fi';

const ChatWindow = ({ messages, onSendMessage, onPhotoUpload, onDownloadPDF, isLoading, processingStatus }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages, isLoading]);

  const getStatusInfo = () => {
    if (!isLoading) return { text: 'Ready', color: 'bg-green-100 text-green-700' };
    
    switch (processingStatus) {
      case 'analyzing': return { text: 'Analyzing symptoms...', color: 'bg-blue-100 text-blue-700' };
      case 'verifying': return { text: 'Verifying medications...', color: 'bg-purple-100 text-purple-700' };
      case 'processing': return { text: 'Processing results...', color: 'bg-indigo-100 text-indigo-700' };
      default: return { text: 'Analyzing...', color: 'bg-amber-100 text-amber-700' };
    }
  };

  const statusInfo = getStatusInfo();

  const handleSend = (e) => {
    e.preventDefault();
    if (input.trim().toLowerCase() === 'check') {
      onSendMessage();
      setInput('');
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onPhotoUpload(file);
    }
  };

  const handleAttachmentClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-md">
              <FiImage className="text-white" size={20} />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">AI Consultation</h2>
              <p className="text-sm text-gray-500">Powered by Advanced AI Analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusInfo.color}`}>
              {statusInfo.text}
            </span>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-gray-50 to-white" style={{ maxHeight: 'calc(100vh - 280px)' }}>
        {messages.map((msg, index) => (
          <Message
            key={index}
            message={msg}
            onDownloadPDF={onDownloadPDF}
          />
        ))}
        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 bg-white border-t border-gray-100">
        <form onSubmit={handleSend} className="flex items-center gap-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept="image/*"
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={handleAttachmentClick}
            className="p-3 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading}
            aria-label="Upload image"
          >
            <FiPaperclip size={20} />
          </button>
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='Type "check" to analyze the prescription...'
              className="w-full px-5 py-3.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-400 transition-all disabled:opacity-50"
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            className="p-3.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium shadow-md hover:shadow-lg px-6"
            disabled={isLoading}
          >
            <FiSend size={18} />
            <span>Analyze</span>
          </button>
        </form>
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-gray-500 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
            Tip: Enter multiple medications separated by commas for comprehensive analysis
          </p>
          <p className="text-xs text-gray-400">
            AI-powered medical safety platform
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
