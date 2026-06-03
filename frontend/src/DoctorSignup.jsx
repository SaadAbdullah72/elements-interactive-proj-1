// DoctorSignup.jsx
// Purpose: Multi-step form for doctor registration with license upload
// and validation. Important security note: uploaded license images should
// be scanned and stored securely on the server; do not keep sensitive
// files in the client or expose direct storage URLs.
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
 FiUser,
 FiMail,
 FiLock,
 FiCalendar,
 FiBriefcase,
 FiFileText,
 FiMapPin,
 FiPhone,
 FiAward,
 FiCheckCircle,
 FiAlertCircle,
 FiEye,
 FiEyeOff,
 FiArrowRight,
 FiLogIn,
 FiUpload,
 FiImage
} from 'react-icons/fi';
import axios from 'axios';
import { API_URL } from './apiConfig';
import AppHeader from './AppHeader';

const DoctorSignup = ({ onSignupSuccess, onBackToLogin }) => {
 const [isLoading, setIsLoading] = useState(false);
 const [error, setError] = useState('');
 const [success, setSuccess] = useState('');
 const [showPassword, setShowPassword] = useState(false);
 const [specialties, setSpecialties] = useState([]);
 const [step, setStep] = useState(1);
 const [licenseImage, setLicenseImage] = useState(null);
 const [licenseImageName, setLicenseImageName] = useState('');

 const [formData, setFormData] = useState({
 // Account credentials
 email: '',
 password: '',
 name: '',
 
 // Personal information
 age: '',
 date_of_birth: '',
 gender: '',
 
 // Professional information
 specialization: '',
 medical_council_registration: '',
 medical_council_country: 'Pakistan',
 
 // CNIC
 cnic: '',
 
 // Contact information
 phone: '',
 address: '',
 city: '',
 hospital_affiliation: '',
 hospital_address: '',
 
 // Experience
 years_of_experience: '',
 
 // Additional
 additional_qualifications: ''
 });

 // Fetch medical specialties on mount
 useEffect(() => {
 const fetchSpecialties = async () => {
 try {
 const response = await axios.get(`${API_URL}/api/doctor/specialties`);
 setSpecialties(response.data);
 } catch (err) {
 console.error('Failed to fetch specialties:', err);
 }
 };
 fetchSpecialties();
 }, []);

 const handleChange = (e) => {
 const { name, value } = e.target;
 setFormData(prev => ({ ...prev, [name]: value }));
 setError('');
 };

 const formatCNIC = (value) => {
 // Remove all non-digits
 let digits = value.replace(/\D/g, '');
 // Limit to 13 digits
 digits = digits.slice(0, 13);
 // Format as XXXXX-XXXXXXX-X
 if (digits.length > 10) {
 return `${digits.slice(0, 5)}-${digits.slice(5, 12)}-${digits.slice(12)}`;
 } else if (digits.length > 5) {
 return `${digits.slice(0, 5)}-${digits.slice(5)}`;
 }
 return digits;
 };

 const handleCNICChange = (e) => {
 const formatted = formatCNIC(e.target.value);
 setFormData(prev => ({ ...prev, cnic: formatted }));
 };

 const handleEmailChange = (e) => {
 const email = e.target.value;
 setFormData(prev => ({ ...prev, email: email }));
 // Clear error if email becomes valid
 if (email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
 setError('');
 }
 };

 const handlePhoneChange = (e) => {
 let phone = e.target.value.replace(/[^\d+]/g, '');
 // Format as 0300-1234567
 if (phone.startsWith('92')) {
 phone = '0' + phone.slice(1);
 }
 if (phone.length > 4) {
 phone = phone.slice(0, 4) + '-' + phone.slice(4, 11);
 }
 setFormData(prev => ({ ...prev, phone: phone }));
 };

 const handleLicenseUpload = async (e) => {
 const file = e.target.files[0];
 if (!file) return;

 // Validate file type
 if (!file.type.startsWith('image/')) {
 setError('Please upload an image file (JPG, PNG)');
 return;
 }

 // Validate file size (max 5MB)
 if (file.size > 5 * 1024 * 1024) {
 setError('File size must be less than 5MB');
 return;
 }

 const reader = new FileReader();
 reader.onloadend = () => {
 setLicenseImage(reader.result.split(',')[1]); // Get base64 without prefix
 setLicenseImageName(file.name);
 };
 reader.readAsDataURL(file);
 };

 const nextStep = () => {
 setError('');
 
 // Validate current step fields
 if (step === 1) {
 if (!formData.name.trim()) {
 setError('Please enter your full name');
 return;
 }
 if (formData.name.trim().split(' ').length < 2) {
 setError('Please enter your full name (first and last name)');
 return;
 }
 if (!formData.email.trim()) {
 setError('Please enter your email address');
 return;
 }
 // Email validation
 const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
 if (!emailPattern.test(formData.email)) {
 setError('Please enter a valid email address (e.g., doctor@example.com)');
 return;
 }
 if (!formData.password) {
 setError('Please enter a password');
 return;
 }
 if (formData.password.length < 8) {
 setError('Password must be at least 8 characters');
 return;
 }
 // Password strength validation
 if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
 setError('Password must contain at least one uppercase letter, one lowercase letter, and one number');
 return;
 }
 }
 
 if (step === 2) {
 if (!formData.age || parseInt(formData.age) < 21 || parseInt(formData.age) > 100) {
 setError('Please enter a valid age (21-100)');
 return;
 }
 if (!formData.date_of_birth) {
 setError('Please select your date of birth');
 return;
 }
 // Validate age matches DOB
 const dob = new Date(formData.date_of_birth);
 const today = new Date();
 const calculatedAge = today.getFullYear() - dob.getFullYear();
 if (calculatedAge < 21 || calculatedAge > 100) {
 setError('Age must be between 21 and 100 years');
 return;
 }
 if (!formData.gender) {
 setError('Please select your gender');
 return;
 }
 if (!formData.cnic.trim()) {
 setError('Please enter your CNIC number');
 return;
 }
 // Validate CNIC format
 const cnicPattern = /^\d{5}-\d{7}-\d{1}$/;
 if (!cnicPattern.test(formData.cnic)) {
 setError('CNIC must be in format: XXXXX-XXXXXXX-X (13 digits)');
 return;
 }
 }
 
 if (step === 3) {
 if (!formData.specialization) {
 setError('Please select your specialization');
 return;
 }
 if (!formData.medical_council_registration.trim()) {
 setError('Please enter your medical council registration number');
 return;
 }
 // Validate PMC/PMDC number format
 const pmcPattern = /^(PMC|PMDC)-\d{5,7}$|^\d{6,8}$/i;
 if (!pmcPattern.test(formData.medical_council_registration.replace(/\s/g, ''))) {
 setError('Medical council registration must be: PMC-12345, PMDC-12345, or 6-8 digits');
 return;
 }
 if (!licenseImage) {
 setError('Please upload your medical license certificate');
 return;
 }
 if (!formData.years_of_experience || parseInt(formData.years_of_experience) < 0 || parseInt(formData.years_of_experience) > 50) {
 setError('Please enter valid years of experience (0-50)');
 return;
 }
 }
 
 if (step === 4) {
 if (!formData.phone.trim()) {
 setError('Please enter your phone number');
 return;
 }
 // Validate phone number (Pakistan format)
 const phonePattern = /^03\d{9}$|^\+92\d{9}$|^03\d{2}-\d{7}$/;
 const cleanPhone = formData.phone.replace(/[\s-]/g, '');
 if (!phonePattern.test(cleanPhone)) {
 setError('Phone must be in format: 0300-1234567 or 03001234567');
 return;
 }
 if (!formData.city.trim()) {
 setError('Please enter your city');
 return;
 }
 if (formData.city.trim().length < 3) {
 setError('Please enter a valid city name');
 return;
 }
 if (!formData.address.trim()) {
 setError('Please enter your address');
 return;
 }
 if (formData.address.trim().length < 10) {
 setError('Please enter a complete address');
 return;
 }
 if (!formData.hospital_affiliation.trim()) {
 setError('Please enter your hospital affiliation');
 return;
 }
 if (formData.hospital_affiliation.trim().length < 3) {
 setError('Please enter a valid hospital name');
 return;
 }
 if (!formData.hospital_address.trim()) {
 setError('Please enter your hospital address');
 return;
 }
 if (formData.hospital_address.trim().length < 10) {
 setError('Please enter a complete hospital address');
 return;
 }
 }
 
 setStep(step + 1);
 };

 const prevStep = () => {
 setStep(step - 1);
 setError('');
 };

 const handleSignup = async (e) => {
 e.preventDefault();
 setError('');
 setSuccess('');
 setIsLoading(true);

 try {
 const payload = {
 ...formData,
 age: parseInt(formData.age),
 years_of_experience: parseInt(formData.years_of_experience) || 0,
 license_image: licenseImage // Include uploaded license image
 };

 const response = await axios.post(`${API_URL}/api/doctor/signup`, payload);

 if (response.data.success) {
 setSuccess(response.data.message);
 
 if (response.data.account_status === 'active') {
 setTimeout(() => {
 onSignupSuccess(response.data);
 }, 2000);
 }
 }
 } catch (err) {
 if (err.response?.status === 400) {
 setError(err.response.data.detail || 'Registration failed. Please check your details.');
 } else {
 setError('Registration failed. Please try again.');
 }
 console.error('Signup error:', err);
 } finally {
 setIsLoading(false);
 }
 };

 return (
 <div className="min-h-screen bg-purple-400 flex items-center justify-center p-4">
 <AppHeader />
 {/* Background decorations */}
 <div className="absolute inset-0 overflow-hidden">
 <div className="absolute top-20 left-10 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
 <div className="absolute top-40 right-10 w-72 h-72 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
 <div className="absolute bottom-20 left-1/2 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
 </div>

 {/* Main Container */}
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 className="relative w-full max-w-4xl bg-teal-100 rounded-3xl shadow-2xl overflow-hidden"
 >
 {/* Header */}
 <div className="bg-purple-400 px-8 py-6 text-white">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-4">
 <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center backdrop-blur-sm">
 <FiAward className="text-3xl" />
 </div>
 <div>
 <h1 className="text-2xl font-bold">Doctor Registration</h1>
 <p className="text-teal-100 text-sm">Join our professional medical network</p>
 </div>
 </div>
 <button
 onClick={onBackToLogin}
 className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors text-sm font-semibold backdrop-blur-sm"
 >
 <FiLogIn size={16} />
 Already have account?
 </button>
 </div>

 {/* Progress Steps */}
 <div className="mt-6 flex items-center gap-2">
 {[1, 2, 3, 4].map((s) => (
 <div key={s} className="flex items-center">
 <div
 className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
 s <= step
 ? 'bg-white text-purple-600'
 : 'bg-white/30 text-white'
 }`}
 >
 {s < step ? <FiCheckCircle size={18} /> : s}
 </div>
 {s < 4 && (
 <div
 className={`w-12 sm:w-24 h-1 rounded transition-all ${
 s < step ? 'bg-white' : 'bg-white/30'
 }`}
 />
 )}
 </div>
 ))}
 </div>
 <div className="mt-2 flex justify-between text-xs text-teal-100">
 <span>Account</span>
 <span>Personal</span>
 <span>Professional</span>
 <span>Contact</span>
 </div>
 </div>

 {/* Form Container */}
 <div className="p-8">
 {/* Error Message */}
 <AnimatePresence>
 {error && (
 <motion.div
 initial={{ opacity: 0, y: -10 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -10 }}
 className="mb-6 p-4 bg-red-50 border-2 border-red-300 rounded-xl flex items-start gap-3"
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
 className="mb-6 p-4 bg-green-50 border-2 border-green-300 rounded-xl flex items-start gap-3"
 >
 <FiCheckCircle className="text-green-600 text-lg flex-shrink-0 mt-0.5" />
 <p className="text-green-800 text-sm">{success}</p>
 </motion.div>
 )}
 </AnimatePresence>

 <form onSubmit={handleSignup}>
 {/* Step 1: Account Information */}
 {step === 1 && (
 <motion.div
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 className="space-y-4"
 >
 <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
 <FiUser className="text-purple-600" />
 Account Information
 </h3>
 
 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Full Name *
 </label>
 <input
 type="text"
 name="name"
 value={formData.name}
 onChange={handleChange}
 placeholder="Dr. Muhammad Ahmad"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Email Address *
 </label>
 <input
 type="email"
 name="email"
 value={formData.email}
 onChange={handleEmailChange}
 placeholder="doctor@example.com"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 {formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) && (
 <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
 <FiAlertCircle size={12} />
 Please enter a valid email address
 </p>
 )}
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Password *
 </label>
 <div className="relative">
 <input
 type={showPassword ? 'text' : 'password'}
 name="password"
 value={formData.password}
 onChange={handleChange}
 placeholder="Min 8 characters"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all pr-12"
 required
 />
 <button
 type="button"
 onClick={() => setShowPassword(!showPassword)}
 className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
 >
 {showPassword ? <FiEyeOff size={20} /> : <FiEye size={20} />}
 </button>
 </div>
 <p className="text-xs text-gray-500 mt-1">
 Must contain: 8+ characters, uppercase, lowercase, and number
 </p>
 </div>
 </motion.div>
 )}

 {/* Step 2: Personal Information */}
 {step === 2 && (
 <motion.div
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 className="space-y-4"
 >
 <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
 <FiUser className="text-purple-600" />
 Personal Information
 </h3>
 
 <div className="grid grid-cols-2 gap-4">
 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Age *
 </label>
 <input
 type="number"
 name="age"
 value={formData.age}
 onChange={handleChange}
 placeholder="Years"
 min="21"
 max="100"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Date of Birth *
 </label>
 <input
 type="date"
 name="date_of_birth"
 value={formData.date_of_birth}
 onChange={handleChange}
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 </div>
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Gender *
 </label>
 <select
 name="gender"
 value={formData.gender}
 onChange={handleChange}
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 >
 <option value="">Select Gender</option>
 <option value="Male">Male</option>
 <option value="Female">Female</option>
 </select>
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 CNIC (National ID) *
 </label>
 <input
 type="text"
 name="cnic"
 value={formData.cnic}
 onChange={handleCNICChange}
 placeholder="XXXXX-XXXXXXX-X"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 {formData.cnic && !/^\d{5}-\d{7}-\d{1}$/.test(formData.cnic) && formData.cnic.length > 5 && (
 <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
 <FiAlertCircle size={12} />
 Format: XXXXX-XXXXXXX-X (13 digits)
 </p>
 )}
 <p className="text-xs text-gray-500 mt-1">
 Format: 13 digits (e.g., 42101-1234567-8)
 </p>
 </div>
 </motion.div>
 )}

 {/* Step 3: Professional Information */}
 {step === 3 && (
 <motion.div
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 className="space-y-4"
 >
 <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
 <FiBriefcase className="text-purple-600" />
 Professional Information
 </h3>
 
 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Specialization *
 </label>
 <select
 name="specialization"
 value={formData.specialization}
 onChange={handleChange}
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 >
 <option value="">Select Specialization</option>
 {specialties.map((spec) => (
 <option key={spec} value={spec}>{spec}</option>
 ))}
 </select>
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Medical Council Registration (PMC/PMDC) *
 </label>
 <input
 type="text"
 name="medical_council_registration"
 value={formData.medical_council_registration}
 onChange={handleChange}
 placeholder="PMC-12345 or PMDC-12345"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 {formData.medical_council_registration && !/^(PMC|PMDC)-\d{5,7}$|^\d{6,8}$/i.test(formData.medical_council_registration.replace(/\s/g, '')) && formData.medical_council_registration.length > 3 && (
 <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
 <FiAlertCircle size={12} />
 Format: PMC-12345, PMDC-12345, or 6-8 digits
 </p>
 )}
 <p className="text-xs text-gray-500 mt-1">
 Your Pakistan Medical Commission license number
 </p>
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-2">
 Upload Medical License (PMC/PMDC Certificate) *
 </label>
 <div className="border-2 border-dashed border-purple-300 rounded-xl p-6 bg-teal-50 hover:bg-teal-100 transition-colors">
 {licenseImage ? (
 <div className="flex items-center gap-4">
 <div className="w-16 h-16 rounded-lg bg-purple-200 flex items-center justify-center">
 <FiImage className="text-purple-600 text-2xl" />
 </div>
 <div className="flex-1">
 <p className="text-sm font-semibold text-purple-900">{licenseImageName}</p>
 <p className="text-xs text-purple-600">License image uploaded successfully</p>
 </div>
 <button
 type="button"
 onClick={() => {
 setLicenseImage(null);
 setLicenseImageName('');
 }}
 className="text-red-600 hover:text-red-800 p-2"
 >
 <FiAlertCircle size={20} />
 </button>
 </div>
 ) : (
 <label className="flex flex-col items-center justify-center cursor-pointer">
 <FiUpload className="text-purple-600 text-4xl mb-3" />
 <p className="text-sm font-semibold text-purple-900 mb-1">
 Click to upload license image
 </p>
 <p className="text-xs text-purple-600 text-center">
 JPG, PNG (Max 5MB)<br/>
 Upload your PMC/PMDC license certificate
 </p>
 <input
 type="file"
 onChange={handleLicenseUpload}
 accept="image/*"
 className="hidden"
 required
 />
 </label>
 )}
 </div>
 <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
 <FiAlertCircle className="text-amber-600" />
 Your license will be verified with Pakistan Medical Commission before account activation
 </p>
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Years of Experience *
 </label>
 <input
 type="number"
 name="years_of_experience"
 value={formData.years_of_experience}
 onChange={handleChange}
 placeholder="Years"
 min="0"
 max="50"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Additional Qualifications
 </label>
 <textarea
 name="additional_qualifications"
 value={formData.additional_qualifications}
 onChange={handleChange}
 placeholder="FCPS, FRCS, PhD, etc."
 rows={2}
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all resize-none"
 />
 </div>
 </motion.div>
 )}

 {/* Step 4: Contact Information */}
 {step === 4 && (
 <motion.div
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: -20 }}
 className="space-y-4"
 >
 <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
 <FiMapPin className="text-purple-600" />
 Contact & Hospital Information
 </h3>
 
 <div className="grid grid-cols-2 gap-4">
 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Phone Number *
 </label>
 <input
 type="tel"
 name="phone"
 value={formData.phone}
 onChange={handlePhoneChange}
 placeholder="0300-1234567"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 {formData.phone && !/^03\d{2}-\d{7}$/.test(formData.phone.replace(/[\s-]/g, '').replace(/^(\d{4})(\d{7})$/, '$1-$2')) && formData.phone.length > 5 && (
 <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
 <FiAlertCircle size={12} />
 Format: 0300-1234567
 </p>
 )}
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 City *
 </label>
 <input
 type="text"
 name="city"
 value={formData.city}
 onChange={handleChange}
 placeholder="Karachi"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 </div>
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Address *
 </label>
 <input
 type="text"
 name="address"
 value={formData.address}
 onChange={handleChange}
 placeholder="Street address"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Hospital Affiliation *
 </label>
 <input
 type="text"
 name="hospital_affiliation"
 value={formData.hospital_affiliation}
 onChange={handleChange}
 placeholder="Aga Khan University Hospital"
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
 required
 />
 </div>

 <div>
 <label className="block text-sm font-semibold text-gray-700 mb-1">
 Hospital Address *
 </label>
 <textarea
 name="hospital_address"
 value={formData.hospital_address}
 onChange={handleChange}
 placeholder="Hospital complete address"
 rows={2}
 className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all resize-none"
 required
 />
 </div>
 </motion.div>
 )}

 {/* Navigation Buttons */}
 <div className="flex gap-4 mt-8">
 {step > 1 && (
 <button
 type="button"
 onClick={prevStep}
 className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-all font-semibold"
 >
 Previous
 </button>
 )}
 
 {step < 4 ? (
 <button
 type="button"
 onClick={nextStep}
 className="flex-1 px-6 py-3 bg-purple-400 text-white rounded-xl transition-all font-semibold flex items-center justify-center gap-2 shadow-lg"
 >
 Next Step
 <FiArrowRight size={18} />
 </button>
 ) : (
 <button
 type="submit"
 disabled={isLoading}
 className="flex-1 px-6 py-3 bg-purple-400 text-white rounded-xl transition-all font-semibold flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
 >
 {isLoading ? (
 <>
 <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
 Registering...
 </>
 ) : (
 <>
 <FiCheckCircle size={18} />
 Complete Registration
 </>
 )}
 </button>
 )}
 </div>

 {/* Terms Notice */}
 <p className="text-xs text-gray-500 text-center mt-6">
 By registering, you confirm that you are a licensed medical practitioner.
 Your credentials will be verified with Pakistan Medical Commission (PMC).
 </p>

 {/* Advertisement Section - Placeholder for future ads (Google Style) */}
 <div className="mt-6">
 {/* EI Logo Ad - Google Style Sponsored Content with Background */}
 <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
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
 </form>
 </div>
 </motion.div>

 <style>{`
 @keyframes blob {
 0%, 100% { transform: translate(0, 0) scale(1); }
 33% { transform: translate(30px, -50px) scale(1.1); }
 66% { transform: translate(-20px, 20px) scale(0.9); }
 }
 .animate-blob {
 animation: blob 7s infinite;
 }
 .animation-delay-2000 { animation-delay: 2s; }
 .animation-delay-4000 { animation-delay: 4s; }
 `}</style>
 </div>
 );
};

export default DoctorSignup;
