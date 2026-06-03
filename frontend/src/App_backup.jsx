// App_backup.jsx
// Legacy/app snapshot of the main application layout used for
// reference or fallback. Contains patient/doctor navigation samples
// and demo state. Prefer `App.jsx` for the active application entry.
import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ChatWindow from './ChatWindow';
import PatientDetailsForm from './PatientDetailsForm';
import Analytics from './Analytics';
import FaceScan from './FaceScan';
import AIChatbot from './AIChatbot';
import Admin from './Admin';
import DoctorAuth from './DoctorAuth';
import axios from 'axios';
import {
 FiActivity,
 FiBarChart2,
 FiMenu,
 FiX,
 FiHome,
 FiUser,
 FiSettings,
 FiLogOut,
 FiBell,
 FiSearch,
 FiPlus,
 FiCalendar,
 FiTrendingUp,
 FiUserPlus,
 FiMessageCircle,
 FiChevronLeft,
 FiChevronRight,
 FiLayers,
 FiClock,
 FiCheckCircle,
 FiAlertCircle
} from 'react-icons/fi';
import { API_URL } from './apiConfig';

const getPatientNavItems = () => {
 return [
 { id: 'consultation', label: 'Consultation', icon: FiHome },
 { id: 'facescan', label: 'Patient ID', icon: FiUserPlus },
 { id: 'analytics', label: 'Analytics', icon: FiBarChart2 },
 ];
};

const getDoctorNavItems = () => {
 return [
 { id: 'admin', label: 'Admin', icon: FiSettings },
 ];
};

function App() {
 const [currentPage, setCurrentPage] = useState('consultation');
 const [sidebarOpen, setSidebarOpen] = useState(true);
 const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
 const [isDoctor, setIsDoctor] = useState(false);
 const [authToken, setAuthToken] = useState(localStorage.getItem('authToken') || null);
 const [navItems, setNavItems] = useState(getPatientNavItems());
 const [messages, setMessages] = useState([
 {
 role: 'assistant',
 content: 'Welcome to MediSafe Pro! I\'m your AI-powered prescription safety assistant.\n\nI can help you:\n• Check prescription safety\n• Detect drug interactions\n• Predict diseases from symptoms\n• Generate professional PDF reports\n\nPlease fill in the patient details and type "check" to begin.',
 hasPdf: false
 }
 ]);
 
 // Load patient data from localStorage on mount
 const [patientData, setPatientData] = useState(() => {
 const saved = localStorage.getItem('patientData');
 return saved ? JSON.parse(saved) : {
 description: '',
 disease: '',
 medication: '',
 age: '',
 gender: '',
 patientName: '',
 patientEmail: ''
 };
 });
 
 const [isLoading, setIsLoading] = useState(false);
 const [processingStatus, setProcessingStatus] = useState('idle'); // idle, analyzing, verifying, calculating, generating
 const [showTimeline, setShowTimeline] = useState(false);
 const [timelineData, setTimelineData] = useState([]);
 const [showChatbot, setShowChatbot] = useState(false);
 const [showDoctorAuthModal, setShowDoctorAuthModal] = useState(false);
 
 // Session management state
 const [currentSessionId, setCurrentSessionId] = useState(null);
 const [showSessionModal, setShowSessionModal] = useState(false);
 const [sessionNotes, setSessionNotes] = useState('');
 const [patientSessions, setPatientSessions] = useState([]);
 const [showSessionHistory, setShowSessionHistory] = useState(false);

 // Check user role on mount
 useEffect(() => {
 const userRole = localStorage.getItem('userRole');
 const token = localStorage.getItem('authToken');
 if (userRole === 'doctor' && token) {
 setIsDoctor(true);
 setAuthToken(token);
 setNavItems(getDoctorNavItems());
 setCurrentPage('admin'); // Default to admin page for doctors
 } else {
 setIsDoctor(false);
 setNavItems(getPatientNavItems());
 setCurrentPage('consultation'); // Default to consultation for patients
 }
 }, []);

 // Load active session when patient data changes
 // eslint-disable-next-line react-hooks/exhaustive-deps
 useEffect(() => {
 if (patientData.patientName && patientData.patientName.trim()) {
 loadActiveSession();
 loadPatientSessions();
 }
 }, [patientData.patientName]);

 // Save patient data to localStorage whenever it changes
 useEffect(() => {
 localStorage.setItem('patientData', JSON.stringify(patientData));
 }, [patientData]);

 // Session management functions
 const loadActiveSession = useCallback(async () => {
 try {
 const response = await axios.get(`${API_URL}/active-session/${patientData.patientName}`);
 if (response.data.session_id) {
 setCurrentSessionId(response.data.session_id);
 }
 } catch (error) {
 console.error('Failed to load active session:', error);
 }
 }, [patientData.patientName]);

 const loadPatientSessions = useCallback(async () => {
 try {
 const response = await axios.get(`${API_URL}/patient-sessions/${patientData.patientName}`);
 setPatientSessions(response.data.sessions || []);
 } catch (error) {
 console.error('Failed to load patient sessions:', error);
 }
 }, [patientData.patientName]);

 const handleCreateNewSession = async () => {
 if (!patientData.patientName) {
 alert('Please register a patient first');
 setCurrentPage('facescan');
 return;
 }
 setShowSessionModal(true);
 };

 const confirmCreateSession = async () => {
 try {
 const response = await axios.post(`${API_URL}/create-session`, {
 patient_name: patientData.patientName,
 patient_email: patientData.patientEmail,
 session_notes: sessionNotes
 });
 
 setCurrentSessionId(response.data.session_id);
 setSessionNotes('');
 setShowSessionModal(false);
 loadPatientSessions();
 
 setMessages(prev => [
 ...prev,
 {
 role: 'assistant',
 content: `## 📋 New Session Created\n\nA new consultation session has been started. Previous analytics remain accessible and will continue to accumulate.`,
 hasPdf: false
 }
 ]);
 } catch (error) {
 console.error('Failed to create session:', error);
 alert('Failed to create session. Please try again.');
 }
 };

 const handleSwitchSession = async (sessionId) => {
 setCurrentSessionId(sessionId);
 setShowSessionHistory(false);
 
 // Load timeline for selected session
 try {
 const response = await axios.get(`${API_URL}/patient-timeline/${patientData.patientName}?session_id=${sessionId}`);
 setTimelineData(response.data.analyses || []);
 setShowTimeline(true);
 } catch (error) {
 console.error('Failed to load session timeline:', error);
 }
 };

 const handleViewAllSessions = () => {
 // Load all analyses (no session filter)
 handleLoadTimeline();
 setShowSessionHistory(false);
 };

 const handleSendMessage = async () => {
 if (!patientData.disease || !patientData.medication) {
 alert('Please fill in Disease and Medication fields');
 return;
 }

 setIsLoading(true);
 setProcessingStatus('analyzing');
 try {
 console.log('Sending patient data:', patientData);

 setProcessingStatus('verifying');
 const response = await axios.post(`${API_URL}/check-prescription`, patientData);
 console.log('API Response:', response.data);

 setProcessingStatus('processing');
 const result = response.data;

 setMessages(prev => [
 ...prev,
 { role: 'user', content: 'Check prescription', hasPdf: false },
 {
 role: 'assistant',
 content: '',
 hasPdf: true,
 analysisData: result
 }
 ]);

 try {
 const payload = {
 user_email: patientData.patientName || 'anonymous',
 disease: patientData.disease,
 medication: patientData.medication,
 final_decision: result.final_decision,
 risk_level: result.risk_level,
 risk_score: result.risk_score,
 explanation: result.explanation,
 drug_interactions: result.drug_interactions,
 session_id: currentSessionId || '' // Include session_id
 };
 console.log('Saving analysis with payload:', payload);

 await axios.post(`${API_URL}/save-analysis`, payload);
 console.log('Analysis saved successfully');
 } catch (saveError) {
 console.error('Failed to save analysis:', saveError);
 console.error('Response data:', saveError.response?.data);
 }

 } catch (error) {
 console.error('API Error:', error);
 const errorMessage = error.response?.data?.detail || error.message || 'Failed to check prescription. Please try again.';
 setMessages(prev => [
 ...prev,
 { role: 'user', content: 'Check prescription', hasPdf: false },
 {
 role: 'assistant',
 content: `## ❌ Error\n\n${String(errorMessage)}`,
 hasPdf: false
 }
 ]);
 } finally {
 setIsLoading(false);
 setProcessingStatus('idle');
 }
 };

 const handlePhotoUpload = async (file) => {
 setIsLoading(true);
 const formData = new FormData();
 formData.append('file', file);

 try {
 const response = await axios.post(`${API_URL}/upload-photo`, formData, {
 headers: { 'Content-Type': 'multipart/form-data' }
 });

 const description = response.data.description;

 setMessages(prev => [
 ...prev,
 { role: 'user', content: 'Uploaded image for analysis', hasPdf: false },
 {
 role: 'assistant',
 content: `## 📸 Image Analysis Result\n\n${String(description)}\n\n**Next Steps:** Please review the description above and fill in the disease/condition and medication fields to proceed with the safety check.`,
 hasPdf: false
 }
 ]);

 setPatientData(prev => ({ ...prev, description }));
 } catch (error) {
 setMessages(prev => [
 ...prev,
 { role: 'user', content: 'Uploaded image', hasPdf: false },
 { role: 'assistant', content: '❌ Failed to analyze image. Please try again.', hasPdf: false }
 ]);
 } finally {
 setIsLoading(false);
 }
 };

 const handleSymptomPrediction = async (symptoms) => {
 setIsLoading(true);
 try {
 const response = await axios.post(`${API_URL}/predict-disease`, symptoms);
 const predictions = response.data.predictions;

 let contentText = '## 🔍 Disease Prediction Results\n\n';
 predictions.forEach((pred, index) => {
 contentText += `### ${index + 1}. ${pred.disease}\n`;
 contentText += `**Confidence:** ${pred.confidence}\n`;
 contentText += `**Matched Symptoms:** ${pred.matched_symptoms.join(', ')}\n\n`;
 });

 setMessages(prev => [
 ...prev,
 {
 role: 'assistant',
 content: contentText,
 hasPdf: false
 }
 ]);
 } catch (error) {
 setMessages(prev => [
 ...prev,
 { role: 'assistant', content: 'Failed to predict diseases. Please try again.', hasPdf: false }
 ]);
 } finally {
 setIsLoading(false);
 }
 };

 const handleDownloadPDF = async (analysisData) => {
 try {
 const response = await axios.post(`${API_URL}/generate-pdf`, {
 user_email: patientData.patientName || 'anonymous',
 patient_name: patientData.patientName || 'Anonymous Patient',
 age: patientData.age ? parseInt(patientData.age) : null,
 gender: patientData.gender,
 disease: patientData.disease,
 medications: analysisData.medications || [patientData.medication],
 final_decision: analysisData.final_decision,
 risk_level: analysisData.risk_level,
 risk_score: analysisData.risk_score,
 explanation: analysisData.explanation,
 drug_interactions: analysisData.drug_interactions,
 possible_reactions: analysisData.possible_reactions
 }, {
 responseType: 'blob'
 });

 const url = window.URL.createObjectURL(new Blob([response.data]));
 const link = document.createElement('a');
 link.href = url;
 link.setAttribute('download', `medical_report_${patientData.patientName || 'patient'}_${new Date().toISOString().split('T')[0]}.pdf`);
 document.body.appendChild(link);
 link.click();
 link.remove();
 } catch (error) {
 console.error('PDF Error:', error);
 alert('Failed to generate PDF report.');
 }
 };

 const handleLoadTimeline = async () => {
 if (!patientData.patientName) {
 alert('Please enter patient name first');
 return;
 }

 setIsLoading(true);
 try {
 const response = await axios.get(`${API_URL}/patient-timeline/${patientData.patientName}`);
 setTimelineData(response.data.analyses);
 setShowTimeline(true);
 } catch (error) {
 console.error('Timeline Error:', error);
 setMessages(prev => [
 ...prev,
 { role: 'assistant', content: 'Failed to load patient timeline.', hasPdf: false }
 ]);
 } finally {
 setIsLoading(false);
 }
 };

 const handleLogout = () => {
 // Clear localStorage
 localStorage.removeItem('patientData');
 localStorage.removeItem('authToken');
 localStorage.removeItem('userRole');
 // Reset states
 setAuthToken(null);
 setIsDoctor(false);
 setNavItems(getPatientNavItems());
 // Reset patient data
 setPatientData({
 description: '',
 disease: '',
 medication: '',
 age: '',
 gender: '',
 patientName: '',
 patientEmail: ''
 });
 // Reset messages
 setMessages([
 {
 role: 'assistant',
 content: 'Welcome to MediSafe Pro! I\'m your AI-powered prescription safety assistant.\n\nI can help you:\n• Check prescription safety\n• Detect drug interactions\n• Predict diseases from symptoms\n• Generate professional PDF reports\n\nPlease fill in the patient details and type "check" to begin.',
 hasPdf: false
 }
 ]);
 // Go to consultation page
 setCurrentPage('consultation');
 // Close mobile menu if open
 setMobileMenuOpen(false);
 };

 // TEST FUNCTION: Login with a real doctor account to get valid JWT


 // Handle login success from DoctorAuth
 const handleLoginSuccess = (token) => {
 setAuthToken(token);
 setIsDoctor(true);
 setNavItems(getDoctorNavItems());
 setCurrentPage('admin');
 setShowDoctorAuthModal(false);
 };

 return (
 <div className="h-screen bg-gray-50 flex overflow-hidden">
 {/* Mobile Menu Overlay */}
 {mobileMenuOpen && (
 <div 
 className="fixed inset-0 bg-black/50 z-30 lg:hidden"
 onClick={() => setMobileMenuOpen(false)}
 />
 )}

 {/* Sidebar */}
 <motion.aside
 initial={false}
 animate={{
 width: sidebarOpen ? 220 : 80,
 x: mobileMenuOpen ? 0 : (typeof window !== 'undefined' && window.innerWidth < 1024 ? -220 : 0)
 }}
 className={`bg-white border-r border-gray-200 flex flex-col shadow-lg z-40 fixed lg:relative h-full ${
 mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
 } transition-transform duration-300`}
 >
 {/* Logo */}
 <div className="p-4 border-b border-gray-100">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <img src="/myimage.png" alt="Logo" className="w-14 h-14 object-cover shadow-md" />
 {sidebarOpen && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="overflow-hidden"
 >
 <h1 className="text-base font-bold text-gray-900 whitespace-nowrap">MediSafe Pro</h1>
 <p className="text-xs text-gray-500">AI Medical Assistant</p>
 </motion.div>
 )}
 </div>
 {/* Mobile close button */}
 <button 
 onClick={() => setMobileMenuOpen(false)}
 className="lg:hidden p-2 hover:bg-gray-100 rounded-lg"
 >
 <FiX size={20} />
 </button>
 </div>
 </div>

 {/* Navigation */}
 <nav className="flex-1 p-3 space-y-2 overflow-y-auto">
 {navItems.map((item) => {
 const Icon = item.icon;
 const isActive = currentPage === item.id;
 return (
 <button
 key={item.id}
 onClick={() => {
 setCurrentPage(item.id);
 setMobileMenuOpen(false);
 }}
 className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
 isActive
 ? 'bg-teal-50 text-purple-600 shadow-sm'
 : 'text-gray-600 hover:bg-gray-50'
 }`}
 >
 <Icon className={`text-lg ${isActive ? 'text-purple-600' : 'text-gray-500'}`} />
 {sidebarOpen && (
 <motion.span
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="font-medium whitespace-nowrap text-sm"
 >
 {item.label}
 </motion.span>
 )}
 {isActive && sidebarOpen && (
 <motion.div
 layoutId="activeIndicator"
 className="ml-auto w-1.5 h-1.5 rounded-full bg-purple-600"
 />
 )}
 </button>
 );
 })}
 </nav>

 {/* User Section */}
 <div className="p-3 border-t border-gray-100">
 <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-gray-50 mb-2">
 <div className="w-7 h-7 rounded-full bg-purple-400 flex items-center justify-center">
 <FiUser className="text-white text-xs" />
 </div>
 {sidebarOpen && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="overflow-hidden flex-1 text-left"
 >
 <p className="text-xs font-medium text-gray-900 truncate">{isDoctor ? '👨‍⚕️ Doctor' : '👤 Patient'}</p>
 <p className="text-xs text-gray-500 truncate">{isDoctor ? 'Admin Access' : 'Patient Portal'}</p>
 </motion.div>
 )}
 </div>

 {/* Doctor Login Button - Only show for non-doctors */}
 {!isDoctor && (
 <button
 onClick={() => setShowDoctorAuthModal(true)}
 className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-purple-600 hover:bg-purple-50 transition-all mt-2"
 >
 <FiUserPlus className="text-lg" />
 {sidebarOpen && (
 <motion.span
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="font-medium text-sm"
 >
 Doctor Login
 </motion.span>
 )}
 </button>
 )}

 {/* Logout Button */}
 <button
 onClick={handleLogout}
 className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-red-600 hover:bg-red-50 transition-all mt-2"
 >
 <FiLogOut className="text-lg" />
 {sidebarOpen && (
 <motion.span
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="font-medium text-sm"
 >
 Logout
 </motion.span>
 )}
 </button>
 </div>

 {/* Toggle Sidebar - Desktop Only */}
 <button
 onClick={() => setSidebarOpen(!sidebarOpen)}
 className="hidden lg:flex absolute -right-3 top-8 w-6 h-6 rounded-full bg-white border border-gray-200 shadow-md items-center justify-center text-gray-500 hover:text-purple-600 transition-colors z-50"
 >
 {sidebarOpen ? <FiChevronLeft size={14} /> : <FiChevronRight size={14} />}
 </button>
 </motion.aside>

 {/* Main Content */}
 <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
 {/* Top Bar */}
 <header className="bg-white border-b border-gray-200 px-4 lg:px-6 py-4 flex items-center justify-between shadow-sm">
 <div className="flex items-center gap-4">
 {/* Mobile menu toggle */}
 <button
 onClick={() => setMobileMenuOpen(true)}
 className="lg:hidden p-2 hover:bg-gray-100 rounded-lg"
 >
 <FiMenu size={20} />
 </button>
 <div className="relative hidden md:block">
 <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
 <input
 type="text"
 placeholder="Search..."
 className="pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 w-48 lg:w-64"
 />
 </div>
 </div>
 <div className="flex items-center gap-2 lg:gap-4">
 {/* AI Chatbot - Only for patients */}
 {!isDoctor && (
 <button
 onClick={() => {
 if (!patientData.patientName) {
 alert('Please register a patient first to use the AI chatbot');
 setCurrentPage('facescan');
 } else {
 setShowChatbot(true);
 }
 }}
 className="flex items-center gap-1 lg:gap-2 px-3 lg:px-4 py-2 bg-purple-400 text-white rounded-xl transition-colors shadow-md text-sm lg:text-base"
 >
 <FiMessageCircle size={18} />
 <span className="hidden sm:inline font-medium">AI Chatbot</span>
 </button>
 )}
 <button className="relative p-2 text-gray-500 hover:bg-gray-100 rounded-xl transition-colors">
 <FiBell size={20} />
 <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
 </button>
 {/* New Patient Button - Only for patients */}
 {!isDoctor && (
 <button
 onClick={() => setCurrentPage('facescan')}
 className="flex items-center gap-1 lg:gap-2 px-3 lg:px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors shadow-md text-sm lg:text-base"
 >
 <FiPlus size={18} />
 <span className="hidden sm:inline font-medium">New Patient</span>
 </button>
 )}
 </div>
 </header>

 {/* Page Content */}
 <main className="flex-1 overflow-y-auto">
 <AnimatePresence mode="wait">
 {currentPage === 'consultation' ? (
 <motion.div
 key="consultation"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 transition={{ duration: 0.2 }}
 className="h-full flex flex-col lg:flex-row"
 >
 {/* Left Panel - Patient Form - Hidden on mobile, shown on lg */}
 <div className="w-full lg:w-96 shrink-0 p-4 overflow-y-auto border-b lg:border-r border-gray-200 bg-white lg:block">
 <PatientDetailsForm
 patientData={patientData}
 setPatientData={setPatientData}
 onSymptomPrediction={handleSymptomPrediction}
 />

 {/* Quick Actions */}
 <div className="mt-6 space-y-3">
 <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Quick Actions</h3>
 
 {/* Session Management */}
 {patientData.patientName && (
 <div className="mb-4 p-3 bg-purple-50 rounded-xl border border-indigo-100">
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <FiLayers className="text-indigo-600" />
 <span className="text-xs font-semibold text-gray-700">Current Session</span>
 </div>
 {currentSessionId && (
 <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
 )}
 </div>
 <div className="flex gap-2">
 <button
 onClick={handleCreateNewSession}
 className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors"
 >
 <FiPlus size={14} />
 New Session
 </button>
 <button
 onClick={() => setShowSessionHistory(true)}
 className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-white text-indigo-600 text-xs font-medium rounded-lg border border-indigo-200 hover:bg-indigo-50 transition-colors"
 >
 <FiClock size={14} />
 History
 </button>
 </div>
 {currentSessionId && (
 <p className="text-xs text-gray-500 mt-2 truncate">
 ID: {currentSessionId.slice(-8)}
 </p>
 )}
 </div>
 )}
 
 <button
 onClick={handleLoadTimeline}
 className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors text-gray-700"
 >
 <FiCalendar className="text-purple-500" />
 <span className="font-medium">View Patient Timeline</span>
 </button>
 <button
 onClick={() => {
 if (!patientData.patientName) {
 alert('Please register a patient first by going to Patient ID page');
 setCurrentPage('facescan');
 } else {
 setCurrentPage('analytics');
 }
 }}
 className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors text-gray-700"
 >
 <FiBarChart2 className="text-purple-500" />
 <span className="font-medium">View Analytics</span>
 </button>
 </div>
 </div>

 {/* Right Panel - Chat */}
 <div className="flex-1 p-4 min-w-0">
 <ChatWindow
 messages={messages}
 onSendMessage={handleSendMessage}
 onPhotoUpload={handlePhotoUpload}
 onDownloadPDF={handleDownloadPDF}
 isLoading={isLoading}
 processingStatus={processingStatus}
 />
 </div>
 </motion.div>
 ) : currentPage === 'facescan' && !isDoctor ? (
 <motion.div
 key="facescan"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 transition={{ duration: 0.2 }}
 className="h-full"
 >
 <FaceScan onIdGenerated={(id, name, email) => {
 setPatientData(prev => ({...prev, patientName: name, patientEmail: email}));
 setCurrentPage('consultation');
 }} />
 </motion.div>
 ) : currentPage === 'admin' && isDoctor ? (
 <motion.div
 key="admin"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 transition={{ duration: 0.2 }}
 className="h-full"
 >
 <Admin authToken={authToken} />
 </motion.div>
 ) : currentPage === 'analytics' && !isDoctor ? (
 <motion.div
 key="analytics"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 transition={{ duration: 0.2 }}
 className="h-full"
 >
 <Analytics userEmail={patientData.patientEmail} patientName={patientData.patientName} />
 </motion.div>
 ) : (
 // Fallback: redirect to appropriate default page
 <motion.div
 key="consultation"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 transition={{ duration: 0.2 }}
 className="h-full"
 >
 <div className="flex items-center justify-center h-full">
 <p className="text-gray-500">Access denied. Redirecting...</p>
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 </main>
 </div>

 {/* Timeline Modal */}
 {showTimeline && (
 <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden"
 >
 <div className="p-6 border-b flex justify-between items-center bg-purple-400">
 <div>
 <h2 className="text-2xl font-bold text-white">Patient Health Timeline</h2>
 <p className="text-yellow-100 text-sm mt-1">Historical analysis records</p>
 </div>
 <button
 onClick={() => setShowTimeline(false)}
 className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
 >
 <FiX size={24} />
 </button>
 </div>
 <div className="p-6 overflow-y-auto max-h-[60vh] bg-gray-50">
 {timelineData.length === 0 ? (
 <div className="text-center py-12">
 <FiCalendar className="w-16 h-16 mx-auto mb-4 text-gray-300" />
 <p className="text-gray-500 text-lg">No analyses found for this patient.</p>
 </div>
 ) : (
 <div className="space-y-4">
 {timelineData.map((analysis) => {
 const decisionColor = analysis.final_decision === 'SAFE' ? 'bg-green-100 text-green-700 border-green-200' :
 (analysis.final_decision === 'CAUTION' ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-red-100 text-red-700 border-red-200');
 const decisionDot = analysis.final_decision === 'SAFE' ? 'bg-green-500' :
 (analysis.final_decision === 'CAUTION' ? 'bg-amber-500' : 'bg-red-500');
 return (
 <motion.div
 key={analysis.id}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-all"
 >
 <div className="flex justify-between items-start mb-3">
 <div className="flex items-center gap-3">
 <div className={`w-3 h-3 rounded-full ${decisionDot}`}></div>
 <div>
 <h3 className="font-semibold text-lg text-gray-900">{analysis.disease}</h3>
 <p className="text-sm text-gray-500">Medication: {analysis.medication}</p>
 </div>
 </div>
 <span className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${decisionColor}`}>
 {analysis.final_decision}
 </span>
 </div>
 <div className="flex gap-6 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
 <div>
 <span className="text-gray-400">Date:</span>{' '}
 <span className="font-medium">{new Date(analysis.date).toLocaleDateString()}</span>
 </div>
 <div>
 <span className="text-gray-400">Risk Level:</span>{' '}
 <span className="font-medium">{analysis.risk_level}</span>
 </div>
 {analysis.risk_score && (
 <div>
 <span className="text-gray-400">Risk Score:</span>{' '}
 <span className="font-medium">{analysis.risk_score.score}/100</span>
 </div>
 )}
 </div>
 </motion.div>
 );
 })}
 </div>
 )}
 </div>
 </motion.div>
 </div>
 )}

 {/* Create New Session Modal */}
 {showSessionModal && (
 <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
 >
 <div className="p-6 border-b bg-purple-400">
 <div className="flex items-center justify-between">
 <div>
 <h2 className="text-xl font-bold text-white">Create New Session</h2>
 <p className="text-indigo-100 text-sm mt-1">Start a fresh consultation session</p>
 </div>
 <button
 onClick={() => setShowSessionModal(false)}
 className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
 >
 <FiX size={20} />
 </button>
 </div>
 </div>
 <div className="p-6 space-y-4">
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-2">
 Session Notes (Optional)
 </label>
 <textarea
 value={sessionNotes}
 onChange={(e) => setSessionNotes(e.target.value)}
 placeholder="Add any notes about this session (e.g., 'Follow-up visit', 'Initial consultation')..."
 className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
 rows={3}
 />
 </div>
 <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
 <div className="flex items-start gap-2">
 <FiAlertCircle className="text-amber-600 mt-0.5" />
 <p className="text-sm text-amber-800">
 <strong>Note:</strong> Previous analytics will remain accessible and will continue to accumulate. This creates a new grouping for consultations.
 </p>
 </div>
 </div>
 <div className="flex gap-3 pt-4">
 <button
 onClick={() => setShowSessionModal(false)}
 className="flex-1 px-4 py-2.5 border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-medium"
 >
 Cancel
 </button>
 <button
 onClick={confirmCreateSession}
 className="flex-1 px-4 py-2.5 bg-purple-400 text-white rounded-xl transition-colors font-medium shadow-md"
 >
 Create Session
 </button>
 </div>
 </div>
 </motion.div>
 </div>
 )}

 {/* Session History Modal */}
 {showSessionHistory && (
 <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[70vh] overflow-hidden"
 >
 <div className="p-6 border-b bg-purple-400">
 <div className="flex items-center justify-between">
 <div>
 <h2 className="text-xl font-bold text-white">Session History</h2>
 <p className="text-indigo-100 text-sm mt-1">All consultation sessions</p>
 </div>
 <button
 onClick={() => setShowSessionHistory(false)}
 className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
 >
 <FiX size={20} />
 </button>
 </div>
 </div>
 <div className="p-6 overflow-y-auto max-h-[50vh] bg-gray-50">
 {patientSessions.length === 0 ? (
 <div className="text-center py-12">
 <FiLayers className="w-16 h-16 mx-auto mb-4 text-gray-300" />
 <p className="text-gray-500 text-lg">No sessions found.</p>
 </div>
 ) : (
 <div className="space-y-3">
 {/* All Sessions Option */}
 <motion.button
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 onClick={handleViewAllSessions}
 className="w-full flex items-center gap-4 p-4 bg-purple-50 border-2 border-purple-200 rounded-xl hover:shadow-md transition-all"
 >
 <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center">
 <FiLayers className="text-white" />
 </div>
 <div className="flex-1 text-left">
 <h3 className="font-semibold text-gray-900">All Sessions Combined</h3>
 <p className="text-sm text-gray-600">View complete analytics across all sessions</p>
 </div>
 <FiChevronRight className="text-gray-400" />
 </motion.button>
 
 {/* Individual Sessions */}
 {patientSessions.map((session, index) => (
 <motion.button
 key={session.session_id}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: index * 0.05 }}
 onClick={() => handleSwitchSession(session.session_id)}
 className="w-full flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-xl hover:shadow-md transition-all"
 >
 <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
 <FiClock className="text-indigo-600" />
 </div>
 <div className="flex-1 text-left">
 <div className="flex items-center gap-2">
 <h3 className="font-medium text-gray-900">Session {patientSessions.length - index}</h3>
 {session.session_id === currentSessionId && (
 <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">
 Active
 </span>
 )}
 </div>
 <p className="text-sm text-gray-600">
 {new Date(session.created_at).toLocaleDateString()} • {session.consultation_count} consultation(s)
 </p>
 {session.session_notes && (
 <p className="text-xs text-gray-500 mt-1 truncate">{session.session_notes}</p>
 )}
 </div>
 <FiChevronRight className="text-gray-400" />
 </motion.button>
 ))}
 </div>
 )}
 </div>
 </motion.div>
 </div>
 )}

 {/* AI Chatbot */}
 <AIChatbot
 isOpen={showChatbot}
 onClose={() => setShowChatbot(false)}
 patientName={patientData.patientName}
 />

 {/* Doctor Auth Modal */}
 <AnimatePresence>
 {showDoctorAuthModal && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 exit={{ opacity: 0 }}
 onClick={() => setShowDoctorAuthModal(false)}
 className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
 >
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 exit={{ opacity: 0, scale: 0.95 }}
 onClick={(e) => e.stopPropagation()}
 className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4"
 >
 <button
 onClick={() => setShowDoctorAuthModal(false)}
 className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 z-10"
 >
 <FiX size={24} />
 </button>
 <DoctorAuth onLoginSuccess={handleLoginSuccess} />
 </motion.div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 );
}

export default App;
