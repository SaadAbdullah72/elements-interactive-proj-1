// FaceScan.jsx
// Purpose: Capture patient face via webcam and generate a unique ID.
// Security & privacy notes:
// - Faces and PII are sensitive; ensure transmission uses HTTPS and
//   server-side storage is encrypted. Obtain patient consent before
//   capturing biometric data.
// - This component performs client-side capture only; all identity
//   matching and storage should occur on the backend.
import React, { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { FiCamera, FiX, FiCheck, FiUpload, FiUser } from 'react-icons/fi';
import Webcam from 'react-webcam';
import axios from 'axios';
import { API_URL } from './apiConfig';


const FaceScan = ({ onIdGenerated }) => {
 const webcamRef = useRef(null);
 const [capturedImage, setCapturedImage] = useState(null);
 const [generatedId, setGeneratedId] = useState(null);
 const [patientName, setPatientName] = useState('');
 const [patientEmail, setPatientEmail] = useState('');
 const [isLoading, setIsLoading] = useState(false);
 const [error, setError] = useState(null);
 const [nameSubmitted, setNameSubmitted] = useState(false);

 const capture = useCallback(() => {
 const imageSrc = webcamRef.current.getScreenshot();
 setCapturedImage(imageSrc);
 }, [webcamRef]);

 const handleRetake = () => {
 setCapturedImage(null);
 setGeneratedId(null);
 setError(null);
 };

 const handleNameSubmit = () => {
 if (!patientName.trim()) {
 setError('Please enter patient name');
 return;
 }
 if (!patientEmail.trim()) {
 setError('Please enter patient email');
 return;
 }
 // Basic email validation
 const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
 if (!emailRegex.test(patientEmail)) {
 setError('Please enter a valid email address');
 return;
 }
 setNameSubmitted(true);
 setError(null);
 };

 const handleGenerateId = async () => {
 if (!capturedImage || !patientName.trim() || !patientEmail.trim()) return;

 setIsLoading(true);
 setError(null);
 try {
 // Convert base64 to blob
 const fetchRes = await fetch(capturedImage);
 const blob = await fetchRes.blob();
 const file = new File([blob], "face.jpg", { type: "image/jpeg" });

 const formData = new FormData();
 formData.append('file', file);
 formData.append('patient_name', patientName.trim());
 formData.append('patient_email', patientEmail.trim());

 const response = await axios.post(`${API_URL}/scan-face`, formData, {
 headers: { 'Content-Type': 'multipart/form-data' }
 });

 setGeneratedId(response.data.user_id);
 if(onIdGenerated) {
 onIdGenerated(response.data.user_id, patientName.trim(), patientEmail.trim());
 }

 } catch (err) {
 const errorMessage = err.response?.data?.detail?.message || 'Failed to generate ID. Please try again.';
 setError(errorMessage);
 console.error(err);
 } finally {
 setIsLoading(false);
 }
 };

 const videoConstraints = {
 width: 1280,
 height: 720,
 facingMode: "user"
 };

 return (
 <div className="h-full bg-purple-50 p-8 flex flex-col items-center justify-center">
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-gray-200 p-8 text-center"
 >
 {!generatedId ? (
 <>
 <h1 className="text-3xl font-bold text-gray-900 mb-2">Patient Registration</h1>
 <p className="text-gray-500 mb-6">Enter patient name and scan face to generate a unique patient ID.</p>

 {!nameSubmitted ? (
 <div className="py-8">
 <div className="max-w-md mx-auto">
 <label className="block text-left text-sm font-semibold text-gray-700 mb-2">
 Patient Name
 </label>
 <div className="flex gap-3 mb-4">
 <div className="relative flex-1">
 <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
 <input
 type="text"
 value={patientName}
 onChange={(e) => setPatientName(e.target.value)}
 placeholder="Enter patient name"
 className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
 onKeyPress={(e) => e.key === 'Enter' && handleNameSubmit()}
 />
 </div>
 </div>

 <label className="block text-left text-sm font-semibold text-gray-700 mb-2">
 Patient Email
 </label>
 <div className="flex gap-3">
 <div className="relative flex-1">
 <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
 <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
 <polyline points="22,6 12,13 2,6"></polyline>
 </svg>
 <input
 type="email"
 value={patientEmail}
 onChange={(e) => setPatientEmail(e.target.value)}
 placeholder="Enter patient email"
 className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
 onKeyPress={(e) => e.key === 'Enter' && handleNameSubmit()}
 />
 </div>
 <button
 onClick={handleNameSubmit}
 className="px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-colors"
 >
 Next
 </button>
 </div>
 {error && <p className="text-red-500 mt-3 text-left">{error}</p>}
 </div>
 </div>
 ) : (
 <>
 <div className="w-full aspect-video bg-gray-200 rounded-xl overflow-hidden relative shadow-inner">
 {capturedImage ? (
 <img src={capturedImage} alt="Captured face" className="w-full h-full object-cover" />
 ) : (
 <Webcam
 audio={false}
 ref={webcamRef}
 screenshotFormat="image/jpeg"
 videoConstraints={videoConstraints}
 className="w-full h-full object-cover"
 />
 )}
 </div>

 <div className="mt-4 flex items-center justify-center gap-2 text-gray-600">
 <FiUser className="text-purple-500" />
 <span className="font-medium">Patient: {patientName}</span>
 </div>

 {error && <p className="text-red-500 mt-4">{error}</p>}

 <div className="mt-6 flex justify-center gap-4">
 {capturedImage ? (
 <>
 <button onClick={handleRetake} className="px-6 py-3 bg-gray-200 text-gray-800 rounded-xl font-semibold flex items-center gap-2 hover:bg-gray-300 transition-colors">
 <FiX /> Retake
 </button>
 <button onClick={handleGenerateId} disabled={isLoading} className="px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold flex items-center gap-2 hover:bg-purple-700 transition-colors disabled:bg-purple-400">
 {isLoading ? 'Generating...' : <><FiCheck /> Generate ID</>}
 </button>
 </>
 ) : (
 <button onClick={capture} className="px-8 py-4 bg-purple-600 text-white rounded-xl font-semibold flex items-center gap-2 text-lg hover:bg-purple-700 transition-colors">
 <FiCamera /> Capture
 </button>
 )}
 </div>
 </>
 )}
 </>
 ) : (
 <div className="py-8">
 <motion.div
 initial={{ scale: 0.5, opacity: 0 }}
 animate={{ scale: 1, opacity: 1 }}
 className="w-32 h-32 bg-green-500 text-white flex items-center justify-center rounded-full mx-auto mb-6 shadow-lg"
 >
 <FiCheck size={60} />
 </motion.div>
 <h2 className="text-2xl font-bold text-gray-900 mb-2">Patient Registered Successfully!</h2>
 <p className="text-gray-500 mb-6">Patient ID generated and linked to name and email.</p>
 <div className="bg-gray-100 border-2 border-dashed border-gray-300 rounded-xl p-4 mb-4">
 <p className="text-sm text-gray-500 mb-1">Patient Name</p>
 <p className="text-xl font-bold text-gray-800">{patientName}</p>
 </div>
 <div className="bg-gray-100 border-2 border-dashed border-gray-300 rounded-xl p-4 mb-4">
 <p className="text-sm text-gray-500 mb-1">Patient Email</p>
 <p className="text-lg font-semibold text-gray-800">{patientEmail}</p>
 </div>
 <div className="bg-gray-100 border-2 border-dashed border-gray-300 rounded-xl p-4 text-sm font-mono text-gray-600 tracking-widest mb-6">
 ID: {generatedId}
 </div>
 <button
 onClick={() => {
 setPatientName('');
 setPatientEmail('');
 setNameSubmitted(false);
 setCapturedImage(null);
 setGeneratedId(null);
 setError(null);
 }}
 className="px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-colors"
 >
 Register New Patient
 </button>
 </div>
 )}
 </motion.div>

 {/* Advertisement Section - Placeholder for future ads (Google Style) */}
 <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 w-full max-w-2xl">
 {/* EI Logo Ad - Google Style Sponsored Content with Background */}
 <div className="bg-white/90 backdrop-blur-sm rounded-lg p-3 border border-gray-200 shadow-lg">
 <a
 href="#"
 className="block group"
 onClick={(e) => {
 e.preventDefault();
 alert('EI Health Solutions - Advertisement click handler (to be implemented)');
 }}
 >
 <div className="flex items-center gap-3 py-1">
 <div className="flex items-center gap-2 flex-shrink-0">
 <span className="text-[10px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded font-medium">Ad</span>
 <div className="w-20 h-8 rounded overflow-hidden flex-shrink-0">
 <img
 src="/edited-photo.png"
 alt="EI Logo"
 className="w-full h-full object-cover"
 onError={(e) => {
 e.target.style.display = 'none';
 e.target.parentElement.innerHTML = '<img src="/edited-photo.png" class="w-full h-full object-cover" />';
 }}
 />
 </div>
 </div>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-semibold text-purple-600 group-hover:text-purple-800 truncate">EI Health Solutions</p>
 <p className="text-xs text-gray-600 truncate">Advanced Medical Technology for Modern Healthcare</p>
 </div>
 <div className="flex items-center gap-2 flex-shrink-0">
 <span className="text-xs text-gray-400 group-hover:text-gray-600 transition-colors">Learn More</span>
 <svg className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
 </svg>
 </div>
 </div>
 </a>
 </div>
 </div>
 </div>
 );
};

export default FaceScan;
