// DoctorAuth.jsx
// Purpose: Combined login/signup UI for doctors and admin access.
// Notes:
// - Uses `API_URL` from `apiConfig.js`; update that config for local
//   development or staging environments.
// - Avoid storing long-lived tokens in localStorage for production.
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
 FiMail,
 FiLock,
 FiUser,
 FiAward,
 FiHome,
 FiAlertCircle,
 FiCheckCircle,
 FiEye,
 FiEyeOff,
 FiArrowRight
} from 'react-icons/fi';
import axios from 'axios';
import { API_URL } from './apiConfig';


const DoctorAuth = ({ onLoginSuccess }) => {
 const [isSignup, setIsSignup] = useState(false);
 const [isLoading, setIsLoading] = useState(false);
 const [showPassword, setShowPassword] = useState(false);
 const [error, setError] = useState('');
 const [success, setSuccess] = useState('');

 const [loginForm, setLoginForm] = useState({
 email: '',
 password: ''
 });

 const [signupForm, setSignupForm] = useState({
 name: '',
 email: '',
 password: '',
 specialization: '',
 license_number: '',
 hospital: ''
 });

 const handleLoginChange = (e) => {
 const { name, value } = e.target;
 setLoginForm(prev => ({ ...prev, [name]: value }));
 setError('');
 };

 const handleSignupChange = (e) => {
 const { name, value } = e.target;
 setSignupForm(prev => ({ ...prev, [name]: value }));
 setError('');
 };

 const handleLogin = async (e) => {
 e.preventDefault();
 setError('');
 setSuccess('');
 setIsLoading(true);

 try {
 const response = await axios.post(`${API_URL}/api/auth/login`, {
 email: loginForm.email,
 password: loginForm.password
 });

 if (response.data.user.role === 'doctor') {
 // Store auth data
 localStorage.setItem('authToken', response.data.access_token);
 localStorage.setItem('userRole', 'doctor');
 localStorage.setItem('doctorName', response.data.user.name);

 setSuccess('✅ Login successful! Redirecting to admin panel...');
 setTimeout(() => {
 onLoginSuccess(response.data.access_token);
 }, 1500);
 } else {
 setError('❌ This account is not a doctor account. Please use a doctor account to access the admin panel.');
 }
 } catch (err) {
 if (err.response?.status === 401) {
 setError('❌ Invalid email or password.');
 } else if (err.response?.status === 400) {
 setError('❌ Account does not exist. Please sign up first.');
 } else {
 setError('❌ Login failed. Please try again.');
 }
 console.error('Login error:', err);
 } finally {
 setIsLoading(false);
 }
 };

 const handleSignup = async (e) => {
 e.preventDefault();
 setError('');
 setSuccess('');

 // Validation
 if (!signupForm.name || !signupForm.email || !signupForm.password || 
 !signupForm.specialization || !signupForm.license_number) {
 setError('❌ Please fill in all required fields.');
 return;
 }

 if (signupForm.password.length < 8) {
 setError('❌ Password must be at least 8 characters long.');
 return;
 }

 setIsLoading(true);

 try {
 const response = await axios.post(`${API_URL}/api/auth/doctor-signup`, {
 name: signupForm.name,
 email: signupForm.email,
 password: signupForm.password,
 specialization: signupForm.specialization,
 license_number: signupForm.license_number,
 hospital: signupForm.hospital || ''
 });

 setSuccess('✅ Signup successful! Please check your email to verify your account, then login.');
 setTimeout(() => {
 setIsSignup(false);
 setSignupForm({
 name: '',
 email: '',
 password: '',
 specialization: '',
 license_number: '',
 hospital: ''
 });
 setSuccess('');
 }, 3000);
 } catch (err) {
 if (err.response?.status === 400) {
 setError('❌ ' + (err.response.data.detail || 'Account already exists with this email.'));
 } else {
 setError('❌ Signup failed. Please try again.');
 }
 console.error('Signup error:', err);
 } finally {
 setIsLoading(false);
 }
 };

 return (
 <div className="min-h-screen bg-purple-400 flex items-center justify-center p-4">
 {/* Background decorations */}
 <div className="absolute inset-0 overflow-hidden">
 <div className="absolute top-20 left-10 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
 <div className="absolute top-40 right-10 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
 <div className="absolute bottom-20 left-1/2 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>
 </div>

 {/* Main Container */}
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ duration: 0.5 }}
 className="relative w-full max-w-md"
 >
 {/* Card */}
 <div className="bg-teal-100 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl bg-opacity-95">
 {/* Header */}
 <div className="bg-purple-400 p-6 text-white">
 <div className="flex items-center justify-center mb-3">
 <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
 <FiHome className="text-2xl" />
 </div>
 </div>
 <h1 className="text-2xl font-bold text-center">MediSafe Pro</h1>
 <p className="text-center text-teal-100 text-sm mt-1">Doctor Admin Panel</p>
 </div>

 {/* Form Container */}
 <div className="p-8">
 {/* Toggle Buttons */}
 <div className="flex gap-2 mb-6">
 <button
 onClick={() => {
 setIsSignup(false);
 setError('');
 setSuccess('');
 }}
 className={`flex-1 py-2 rounded-lg font-semibold transition-all ${
 !isSignup
 ? 'bg-purple-600 text-white shadow-lg'
 : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
 }`}
 >
 Login
 </button>
 <button
 onClick={() => {
 setIsSignup(true);
 setError('');
 setSuccess('');
 }}
 className={`flex-1 py-2 rounded-lg font-semibold transition-all ${
 isSignup
 ? 'bg-purple-600 text-white shadow-lg'
 : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
 }`}
 >
 Sign Up
 </button>
 </div>

 {/* Error Message */}
 <AnimatePresence>
 {error && (
 <motion.div
 initial={{ opacity: 0, y: -10 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -10 }}
 className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3"
 >
 <FiAlertCircle className="text-red-600 text-lg flex-shrink-0 mt-0.5" />
 <p className="text-red-800 text-sm">{error}</p>
 </motion.div>
 )}
 </AnimatePresence>

 {/* Success Message */}
 <AnimatePresence>
 {success && (
 <motion.div
 initial={{ opacity: 0, y: -10 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -10 }}
 className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3"
 >
 <FiCheckCircle className="text-green-600 text-lg flex-shrink-0 mt-0.5" />
 <p className="text-green-800 text-sm">{success}</p>
 </motion.div>
 )}
 </AnimatePresence>

 {/* Login Form */}
 <AnimatePresence mode="wait">
 {!isSignup ? (
 <motion.form
 key="login"
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 transition={{ duration: 0.2 }}
 onSubmit={handleLogin}
 className="space-y-4"
 >
 {/* Email */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-2">
 <FiMail className="inline mr-2" />
 Email
 </label>
 <input
 type="email"
 name="email"
 value={loginForm.email}
 onChange={handleLoginChange}
 placeholder="doctor@hospital.com"
 className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
 required
 />
 </div>

 {/* Password */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-2">
 <FiLock className="inline mr-2" />
 Password
 </label>
 <div className="relative">
 <input
 type={showPassword ? 'text' : 'password'}
 name="password"
 value={loginForm.password}
 onChange={handleLoginChange}
 placeholder="••••••••"
 className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
 required
 />
 <button
 type="button"
 onClick={() => setShowPassword(!showPassword)}
 className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-700"
 >
 {showPassword ? <FiEyeOff /> : <FiEye />}
 </button>
 </div>
 </div>

 {/* Login Button */}
 <button
 type="submit"
 disabled={isLoading}
 className="w-full mt-6 bg-purple-400 text-white font-semibold py-2.5 rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
 >
 {isLoading ? (
 <>
 <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
 Logging in...
 </>
 ) : (
 <>
 Login
 <FiArrowRight />
 </>
 )}
 </button>
 </motion.form>
 ) : (
 /* Signup Form */
 <motion.form
 key="signup"
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: 20 }}
 transition={{ duration: 0.2 }}
 onSubmit={handleSignup}
 className="space-y-3"
 >
 {/* Name */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 <FiUser className="inline mr-2" size={16} />
 Full Name
 </label>
 <input
 type="text"
 name="name"
 value={signupForm.name}
 onChange={handleSignupChange}
 placeholder="Dr. John Smith"
 className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
 required
 />
 </div>

 {/* Email */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 <FiMail className="inline mr-2" size={16} />
 Email
 </label>
 <input
 type="email"
 name="email"
 value={signupForm.email}
 onChange={handleSignupChange}
 placeholder="doctor@hospital.com"
 className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
 required
 />
 </div>

 {/* Specialization */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 <FiAward className="inline mr-2" size={16} />
 Specialization
 </label>
 <input
 type="text"
 name="specialization"
 value={signupForm.specialization}
 onChange={handleSignupChange}
 placeholder="e.g., Cardiology, Neurology"
 className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
 required
 />
 </div>

 {/* License Number */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 License Number
 </label>
 <input
 type="text"
 name="license_number"
 value={signupForm.license_number}
 onChange={handleSignupChange}
 placeholder="e.g., MD123456"
 className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
 required
 />
 </div>

 {/* Hospital */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 <FiHome className="inline mr-2" size={16} />
 Hospital/Clinic (Optional)
 </label>
 <input
 type="text"
 name="hospital"
 value={signupForm.hospital}
 onChange={handleSignupChange}
 placeholder="Hospital name"
 className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
 />
 </div>

 {/* Password */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 <FiLock className="inline mr-2" size={16} />
 Password (min 8 chars)
 </label>
 <div className="relative">
 <input
 type={showPassword ? 'text' : 'password'}
 name="password"
 value={signupForm.password}
 onChange={handleSignupChange}
 placeholder="••••••••"
 className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
 required
 />
 <button
 type="button"
 onClick={() => setShowPassword(!showPassword)}
 className="absolute right-3 top-2 text-gray-500 hover:text-gray-700"
 >
 {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
 </button>
 </div>
 </div>

 {/* Signup Button */}
 <button
 type="submit"
 disabled={isLoading}
 className="w-full mt-4 bg-purple-400 text-white font-semibold py-2.5 rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
 >
 {isLoading ? (
 <>
 <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
 Creating account...
 </>
 ) : (
 <>
 Create Account
 <FiArrowRight />
 </>
 )}
 </button>

 {/* Password Requirements */}
 <p className="text-xs text-gray-600 mt-2">
 Password must contain: uppercase, lowercase, number, and be at least 8 characters
 </p>
 </motion.form>
 )}
 </AnimatePresence>

 {/* Footer */}
 <p className="text-center text-gray-600 text-xs mt-6">
 For patients, use the main{' '}
 <span className="font-semibold">Consultation</span> section
 </p>
 </div>
 </div>
 </motion.div>

 {/* Advertisement Section - Placeholder for future ads (Google Style) */}
 <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 w-full max-w-md">
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

 <style>{`
 @keyframes blob {
 0%, 100% {
 transform: translate(0, 0) scale(1);
 }
 33% {
 transform: translate(30px, -50px) scale(1.1);
 }
 66% {
 transform: translate(-20px, 20px) scale(0.9);
 }
 }
 .animate-blob {
 animation: blob 7s infinite;
 }
 .animation-delay-2000 {
 animation-delay: 2s;
 }
 .animation-delay-4000 {
 animation-delay: 4s;
 }
 `}</style>
 </div>
 );
};

export default DoctorAuth;
