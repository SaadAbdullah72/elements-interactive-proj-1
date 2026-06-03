// AIChatbot.jsx
// Purpose: In-app conversational assistant to gather symptoms and return
// AI-generated analyses. This component is a UI wrapper — the actual
// analysis happens via API calls to `chatbot-analyze` endpoint.
// Security: do not send sensitive identifiers in free text; prefer
// structured fields when available.
import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FiSend, FiX, FiMessageCircle, FiActivity, FiAlertCircle, FiCheckCircle, FiHeart, FiClock, FiAlertTriangle } from 'react-icons/fi';
import axios from 'axios';
import { API_URL } from './apiConfig';


const AIChatbot = ({ isOpen, onClose, patientName }) => {
 const [messages, setMessages] = useState([
 {
 role: 'assistant',
 content: "Hello! I'm your AI Health Assistant. I can help you understand your symptoms and provide health recommendations. What symptoms are you experiencing today?",
 timestamp: new Date().toISOString()
 }
 ]);
 const [input, setInput] = useState('');
 const [isLoading, setIsLoading] = useState(false);
 const messagesEndRef = useRef(null);

 const scrollToBottom = () => {
 messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
 };

 useEffect(() => {
 scrollToBottom();
 }, [messages]);

 const analyzeSymptoms = async (symptoms) => {
 try {
 const response = await axios.post(`${API_URL}/chatbot-analyze`, {
 symptoms,
 patient_name: patientName
 });
 return response.data;
 } catch (error) {
 console.error('Chatbot analysis error:', error);
 throw error;
 }
 };

 const handleSend = async () => {
 if (!input.trim() || isLoading) return;

 const userMessage = {
 role: 'user',
 content: input,
 timestamp: new Date().toISOString()
 };

 setMessages(prev => [...prev, userMessage]);
 setInput('');
 setIsLoading(true);

 try {
 const result = await analyzeSymptoms(input);

 const assistantMessage = {
 role: 'assistant',
 content: result.response,
 severity: result.severity,
 recommendations: result.recommendations,
 explanation: result.explanation,
 body_explanation: result.body_explanation,
 next_steps: result.next_steps,
 red_flags: result.red_flags,
 possible_causes: result.possible_causes,
 timestamp: new Date().toISOString()
 };

 setMessages(prev => [...prev, assistantMessage]);
 } catch (error) {
 const errorMessage = {
 role: 'assistant',
 content: "I'm sorry, I encountered an error analyzing your symptoms. Please try again or consult a healthcare professional.",
 timestamp: new Date().toISOString()
 };
 setMessages(prev => [...prev, errorMessage]);
 } finally {
 setIsLoading(false);
 }
 };

 const handleKeyPress = (e) => {
 if (e.key === 'Enter' && !e.shiftKey) {
 e.preventDefault();
 handleSend();
 }
 };

 const getSeverityColor = (severity) => {
 switch (severity?.toLowerCase()) {
 case 'low': return 'bg-emerald-100 border-emerald-200 text-emerald-700';
 case 'medium': return 'bg-amber-100 border-amber-200 text-amber-700';
 case 'high': return 'bg-red-100 border-red-200 text-red-700';
 case 'critical': return 'bg-rose-100 border-rose-200 text-rose-700';
 default: return 'bg-gray-100 border-gray-200 text-gray-700';
 }
 };

 const getSeverityIcon = (severity) => {
 switch (severity?.toLowerCase()) {
 case 'low': return <FiCheckCircle className="text-emerald-500" size={20} />;
 case 'medium': return <FiAlertCircle className="text-amber-500" size={20} />;
 case 'high': return <FiAlertCircle className="text-red-500" size={20} />;
 case 'critical': return <FiAlertTriangle className="text-rose-500" size={20} />;
 default: return <FiActivity className="text-gray-500" size={20} />;
 }
 };

 if (!isOpen) return null;

 return (
 <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
 <motion.div
 initial={{ opacity: 0, y: 100 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: 100 }}
 className="bg-white w-full sm:max-w-3xl h-[90vh] sm:h-[650px] rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden"
 >
 {/* Header */}
 <div className="bg-purple-400 p-4 flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
 <FiMessageCircle className="text-white" size={20} />
 </div>
 <div>
 <h3 className="text-white font-bold">AI Health Assistant</h3>
 <p className="text-teal-100 text-xs">Powered by Advanced AI</p>
 </div>
 </div>
 <button
 onClick={onClose}
 className="text-white/80 hover:text-white transition-colors p-2"
 >
 <FiX size={24} />
 </button>
 </div>

 {/* Messages */}
 <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
 {messages.map((message, index) => (
 <motion.div
 key={index}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
 >
 <div
 className={`max-w-[85%] rounded-2xl p-4 ${
 message.role === 'user'
 ? 'bg-purple-600 text-white'
 : 'bg-white border border-gray-200 shadow-sm'
 }`}
 >
 <p className="text-sm">{message.content}</p>

 {/* Severity Badge */}
 {message.severity && (
 <div className={`mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${getSeverityColor(message.severity)}`}>
 {getSeverityIcon(message.severity)}
 <span>{message.severity} Risk</span>
 </div>
 )}

 {/* Possible Causes Section */}
 {message.possible_causes && message.possible_causes.length > 0 && (
 <div className="mt-4 bg-purple-50 border border-purple-200 rounded-xl p-3">
 <div className="flex items-center gap-2 mb-2">
 <FiActivity className="text-purple-600" size={18} />
 <p className="text-sm font-bold text-purple-800 uppercase">Possible Causes</p>
 </div>
 <ul className="space-y-2">
 {message.possible_causes.map((cause, i) => (
 <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
 <span className="text-purple-500 mt-0.5">•</span>
 <span>{cause}</span>
 </li>
 ))}
 </ul>
 </div>
 )}

 {/* Body Explanation Section */}
 {message.body_explanation && (
 <div className="mt-4 bg-purple-50 border border-purple-200 rounded-xl p-3">
 <div className="flex items-center gap-2 mb-2">
 <FiHeart className="text-purple-600" size={18} />
 <p className="text-sm font-bold text-purple-800 uppercase">What's Happening in Your Body</p>
 </div>
 <p className="text-sm text-gray-700 leading-relaxed">{message.body_explanation}</p>
 </div>
 )}

 {/* Recommendations Section */}
 {message.recommendations && message.recommendations.length > 0 && (
 <div className="mt-4 bg-green-500 border border-emerald-200 rounded-xl p-3">
 <div className="flex items-center gap-2 mb-2">
 <FiCheckCircle className="text-emerald-600" size={18} />
 <p className="text-sm font-bold text-emerald-800 uppercase">Recommendations</p>
 </div>
 <ul className="space-y-2">
 {message.recommendations.map((rec, i) => (
 <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
 <span className="text-emerald-500 mt-0.5">•</span>
 <span>{rec}</span>
 </li>
 ))}
 </ul>
 </div>
 )}

 {/* Red Flags Section */}
 {message.red_flags && message.red_flags.length > 0 && (
 <div className="mt-4 bg-red-500 border border-red-200 rounded-xl p-3">
 <div className="flex items-center gap-2 mb-2">
 <FiAlertTriangle className="text-red-600" size={18} />
 <p className="text-sm font-bold text-red-800 uppercase">⚠️ Warning Signs - Seek Immediate Care If:</p>
 </div>
 <ul className="space-y-2">
 {message.red_flags.map((flag, i) => (
 <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
 <span className="text-red-500 mt-0.5">⚠️</span>
 <span>{flag}</span>
 </li>
 ))}
 </ul>
 </div>
 )}

 {/* Next Steps Section */}
 {message.next_steps && (
 <div className="mt-4 bg-amber-500 border border-amber-200 rounded-xl p-3">
 <div className="flex items-center gap-2 mb-2">
 <FiClock className="text-amber-600" size={18} />
 <p className="text-sm font-bold text-amber-800 uppercase">Next Steps</p>
 </div>
 <p className="text-sm text-gray-700 leading-relaxed">{message.next_steps}</p>
 </div>
 )}

 <p className={`text-xs mt-3 ${message.role === 'user' ? 'text-purple-100' : 'text-gray-400'}`}>
 {new Date(message.timestamp).toLocaleTimeString()}
 </p>
 </div>
 </motion.div>
 ))}
 {isLoading && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="flex justify-start"
 >
 <div className="bg-white border border-gray-200 rounded-2xl p-4">
 <div className="flex items-center gap-3">
 <div className="flex gap-2">
 <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
 <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
 <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
 </div>
 <span className="text-sm text-gray-500">AI is analyzing your symptoms...</span>
 </div>
 </div>
 </motion.div>
 )}
 <div ref={messagesEndRef} />
 </div>

 {/* Input */}
 <div className="p-4 bg-white border-t border-gray-200">
 <div className="flex gap-3">
 <input
 type="text"
 value={input}
 onChange={(e) => setInput(e.target.value)}
 onKeyPress={handleKeyPress}
 placeholder="Describe your symptoms in detail..."
 className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
 disabled={isLoading}
 />
 <button
 onClick={handleSend}
 disabled={isLoading || !input.trim()}
 className="px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-colors disabled:bg-purple-400 flex items-center gap-2"
 >
 <FiSend size={18} />
 Send
 </button>
 </div>
 <p className="text-xs text-gray-400 mt-2 text-center">
 This AI assistant provides information and guidance but does not replace professional medical advice
 </p>
 </div>
 </motion.div>
 </div>
 );
};

export default AIChatbot;
