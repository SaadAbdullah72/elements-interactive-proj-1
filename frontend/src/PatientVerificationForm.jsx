// PatientVerificationForm.jsx
// Purpose: Verify or add patients prior to consultation. This form
// interacts with doctor-protected endpoints and should be used only by
// authenticated clinicians. It provides searching, adding and selection
// helpers and computes derived fields (e.g., BMI) client-side for UX.
//
// Phone number is now a second primary key alongside patid.
// Verification supports lookup by patid OR phone_number so patients
// who forgot their Patient ID can still be found quickly.

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiFileText,
  FiUser,
  FiCalendar,
  FiCheckCircle,
  FiAlertCircle,
  FiArrowRight,
  FiSearch,
  FiBook,
  FiLogOut,
  FiPlus,
  FiX,
  FiDroplet,
  FiHeart,
  FiActivity,
  FiPhone,
  FiInfo
} from 'react-icons/fi';
import axios from 'axios';
import { API_URL } from './apiConfig';
import AppHeader from './AppHeader';
import AdRotator from './AdRotator';

const CONDITION_OPTIONS = [
  "Stable",
  "Unstable",
  "Conscious",
  "Unconscious",
  "Drowsy",
  "Other"
];

const PatientVerificationForm = ({ onVerificationSuccess, onCancel, onNavigate }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showPatientList, setShowPatientList] = useState(false);
  const [showAddPatientModal, setShowAddPatientModal] = useState(false);
  const [patients, setPatients] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [heightFeet, setHeightFeet] = useState('');
  const [heightInches, setHeightInches] = useState('');
  const [showHeightInfo, setShowHeightInfo] = useState(false);
  const [showConditionDropdown, setShowConditionDropdown] = useState(false);
  const conditionDropdownRef = React.useRef(null);



  const [addPatientData, setAddPatientData] = useState({
    pname: '',
    patient_email: '',
    phone_number: '',
    dob: '',
    age: '',
    gender: '',
    disease: '',
    condition: '',
    medication: '',
    presenting_complaint: '',
    bp: '',
    pulse: '',
    bmi: '',
    weight: '',
    height: '',
    family_history: '',
    social_history: '',
    allergies: '',
    case_notes: ''
  });



  const handleAddPatientChange = (e) => {
    const { name, value } = e.target;
    setAddPatientData(prev => ({ ...prev, [name]: value }));
  };

  const selectedConditions = addPatientData.condition
    ? addPatientData.condition.split(',').map(c => c.trim()).filter(Boolean)
    : [];

  const handleToggleCondition = (cond) => {
    let newConditions;
    if (selectedConditions.includes(cond)) {
      newConditions = selectedConditions.filter(c => c !== cond);
    } else {
      newConditions = [...selectedConditions, cond];
    }
    setAddPatientData(prev => ({
      ...prev,
      condition: newConditions.join(', ')
    }));
  };

  // Auto-calculate BMI from weight + height
  useEffect(() => {
    const weight = parseFloat(addPatientData.weight);
    const height = parseFloat(addPatientData.height);
    if (weight > 0 && height > 0) {
      const heightInMeters = height / 100;
      const calculatedBmi = (weight / (heightInMeters * heightInMeters)).toFixed(1);
      setAddPatientData(prev => ({ ...prev, bmi: calculatedBmi }));
    } else {
      setAddPatientData(prev => ({ ...prev, bmi: '' }));
    }
  }, [addPatientData.weight, addPatientData.height]);

  // Auto-calculate Age from Year of Birth (dob) for Add Patient Form
  useEffect(() => {
    const dobVal = parseInt(addPatientData.dob);
    const currentYear = new Date().getFullYear();
    if (dobVal >= 1900 && dobVal <= currentYear) {
      const calculatedAge = currentYear - dobVal;
      setAddPatientData(prev => ({ ...prev, age: calculatedAge.toString() }));
    } else if (!addPatientData.dob) {
      setAddPatientData(prev => ({ ...prev, age: '' }));
    }
  }, [addPatientData.dob]);



  // Auto-calculate Height (cm) from Feet + Inches
  useEffect(() => {
    const feet = parseFloat(heightFeet) || 0;
    const inches = parseFloat(heightInches) || 0;
    if (feet > 0 || inches > 0) {
      const cmVal = ((feet * 30.48) + (inches * 2.54)).toFixed(1);
      setAddPatientData(prev => ({ ...prev, height: cmVal }));
    } else {
      setAddPatientData(prev => ({ ...prev, height: '' }));
    }
  }, [heightFeet, heightInches]);

  // Reset local height state when modal is closed
  useEffect(() => {
    if (!showAddPatientModal) {
      setHeightFeet('');
      setHeightInches('');
      setShowHeightInfo(false);
    }
  }, [showAddPatientModal]);

  // Close condition dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (conditionDropdownRef.current && !conditionDropdownRef.current.contains(event.target)) {
        setShowConditionDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadPatients = async () => {
    try {
      const token = sessionStorage.getItem('authToken');
      const response = await axios.get(`${API_URL}/api/doctor/patients`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = response.data;
      const resolvedPatients = Array.isArray(data)
        ? data
        : Array.isArray(data?.patients)
          ? data.patients
          : [];
      if (!Array.isArray(resolvedPatients)) {
        console.error('Unexpected patients response shape:', data);
      }
      setPatients(resolvedPatients);
      setShowPatientList(true);
      setSearchQuery('');
    } catch (err) {
      console.error('Failed to load patients:', err);
      setPatients([]);
    }
  };

  // Filter by name, patid, or phone
  const filteredPatients = Array.isArray(patients)
    ? patients.filter(patient => {
      const q = searchQuery.toLowerCase();
      if (!q) return true;
      return (
        (patient.pname && patient.pname.toLowerCase().includes(q)) ||
        (patient.patid && patient.patid.toLowerCase().includes(q)) ||
        (patient.phone_number && patient.phone_number.includes(q))
      );
    })
    : [];

  const selectPatient = (patient) => {
    setShowPatientList(false);
    onVerificationSuccess(patient);
  };

  // Safely parse a float field — returns null if empty or NaN
  const safeFloat = (val) => {
    if (val === '' || val === null || val === undefined) return null;
    const parsed = parseFloat(val);
    return isNaN(parsed) ? null : parsed;
  };

  // Client-side phone validation — matches backend normalize_phone logic
  const normalizePhone = (phone) => {
    const digits = phone.replace(/\D/g, '');
    if (digits.startsWith('0092')) return '0' + digits.slice(4);
    if (digits.startsWith('92') && digits.length === 12) return '0' + digits.slice(2);
    if (digits.startsWith('3') && digits.length === 10) return '0' + digits;
    return digits;
  };
  const isValidPkPhone = (phone) => /^03\d{9}$/.test(normalizePhone(phone));

  const handleAddPatient = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validate phone before hitting backend
    if (!addPatientData.phone_number.trim()) {
      setError('❌ Phone number is required.');
      return;
    }
    if (!isValidPkPhone(addPatientData.phone_number)) {
      setError('❌ Enter valid 11 digit mobile no');
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        pname: addPatientData.pname,
        patient_email: addPatientData.patient_email || null,
        phone_number: addPatientData.phone_number,   // required — second primary key
        dob: addPatientData.dob,
        age: parseInt(addPatientData.age),
        gender: addPatientData.gender || null,
        disease: addPatientData.disease || null,
        condition: addPatientData.condition || null,
        medication: addPatientData.medication || null,
        presenting_complaint: addPatientData.presenting_complaint || null,
        bp: addPatientData.bp || null,
        pulse: addPatientData.pulse || null,
        bmi: safeFloat(addPatientData.bmi),
        weight: safeFloat(addPatientData.weight),
        height: safeFloat(addPatientData.height),
        family_history: addPatientData.family_history || null,
        social_history: addPatientData.social_history || null,
        allergies: addPatientData.allergies || null,
        case_notes: addPatientData.case_notes || null
      };
      const token = sessionStorage.getItem('authToken');
      console.log('[AddPatient] Sending payload:', JSON.stringify(payload, null, 2));
      const response = await axios.post(`${API_URL}/api/doctor/patients`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      console.log('[AddPatient] Response:', response.data);
      if (response.data.success) {
        setSuccess(
          `✅ Patient added! Case ID: ${response.data.patient.caseid}, ` +
          `Patient ID: ${response.data.patient.patid}, ` +
          `Phone: ${response.data.patient.phone_number}`
        );
        const newPatient = response.data.patient;
        setTimeout(() => {
          setShowAddPatientModal(false);
          setAddPatientData({
            pname: '', patient_email: '', phone_number: '', dob: '', age: '',
            gender: '', disease: '', condition: '', medication: '', presenting_complaint: '',
            bp: '', pulse: '', bmi: '', weight: '', height: '',
            family_history: '', social_history: '', allergies: '', case_notes: ''
          });
          setHeightFeet('');
          setHeightInches('');
          setSuccess('');
          onVerificationSuccess(newPatient);
        }, 2000);
      }
    } catch (err) {
      console.error('[AddPatient] Error:', err.response?.data || err.message);
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(`❌ ${detail}`);
      } else if (typeof detail === 'object' && detail !== null) {
        setError(`❌ ${JSON.stringify(detail)}`);
      } else if (err.response?.status === 409) {
        setError('❌ A patient with this phone number already exists.');
      } else if (err.response?.status === 400) {
        setError('❌ Enter valid 11 digit mobile no');
      } else {
        setError(`❌ Failed to add patient. Status: ${err.response?.status || 'network error'}`);
      }
    } finally {
      setIsLoading(false);
    }
  };



  const inputClass = "w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all text-gray-800 placeholder-gray-400 text-sm shadow-sm";
  const labelClass = "block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5";

  return (
    <div className="min-h-[100dvh] w-full bg-gray-50 flex flex-col pb-12 md:pb-0">
      <AppHeader />

      {/* Subtle background pattern */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(168,85,247,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(20,184,166,0.05) 0%, transparent 50%)'
        }} />
      </div>

      <div className="relative z-10 flex-1 flex flex-col items-center justify-start px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-3xl"
        >
          {/* Page Title Bar */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Patient Information</h1>
              <p className="text-sm text-gray-500 mt-0.5">Enter patient details before consultation</p>
            </div>
            <button
              onClick={onCancel}
              className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl transition-colors text-sm font-semibold"
            >
              <FiLogOut size={15} />
              Logout
            </button>
          </div>

          {/* Alerts */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3"
              >
                <FiAlertCircle className="text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-red-700 text-sm">{error}</p>
              </motion.div>
            )}
          </AnimatePresence>
          <AnimatePresence>
            {success && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="mb-4 p-4 bg-green-50 border border-green-200 rounded-xl flex items-start gap-3"
              >
                <FiCheckCircle className="text-green-500 flex-shrink-0 mt-0.5" />
                <p className="text-green-700 text-sm">{success}</p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Main Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

            {/* Card Header */}
            <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-purple-50 flex items-center justify-center">
                  <FiUser className="text-purple-500 text-base" />
                </div>
                <div>
                  <p className="font-semibold text-gray-800 text-sm">Patient Details</p>
                  <p className="text-xs text-gray-400">Search by Patient ID or phone number</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={loadPatients}
                  className="flex items-center gap-1.5 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-xl text-xs font-semibold transition-colors shadow-sm"
                >
                  <FiBook size={14} /> Browse Patients
                </button>
              </div>
            </div>

            {/* Patient List */}
            <AnimatePresence>
              {showPatientList && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                  className="border-b border-gray-100 overflow-hidden"
                >
                  {/* Search Bar */}
                  <div className="px-6 pt-4 pb-3">
                    <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5">
                      <FiSearch className="text-gray-400 flex-shrink-0" size={15} />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search by Patient ID, Name, or Phone..."
                        className="flex-1 bg-transparent text-sm text-gray-700 placeholder-gray-400 focus:outline-none"
                      />
                      {searchQuery && (
                        <button onClick={() => setSearchQuery('')} className="text-gray-400 hover:text-gray-600">
                          <FiX size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Patient List */}
                  <div className="max-h-72 overflow-y-auto">
                    <div className="px-6 pb-2 flex items-center justify-between">
                      <p className="text-xs text-gray-400">
                        {filteredPatients.length} of {patients.length} patients
                      </p>
                      <button onClick={() => setShowPatientList(false)} className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1">
                        <FiX size={12} /> Close
                      </button>
                    </div>
                    {filteredPatients.length === 0 ? (
                      <div className="px-6 py-8 text-center text-gray-400 text-sm">
                        No patients match "{searchQuery}"
                      </div>
                    ) : (
                      <div className="divide-y divide-gray-50">
                        {filteredPatients.map(patient => (
                          <button
                            key={patient.patid}
                            onClick={() => selectPatient(patient)}
                            className="w-full px-6 py-3 hover:bg-purple-50 transition-colors text-left flex justify-between items-center group"
                          >
                            <div>
                              <p className="font-semibold text-gray-800 text-sm group-hover:text-purple-700">{patient.pname}</p>
                              <p className="text-xs text-gray-400 mt-0.5">
                                {patient.patid} • {patient.age} yrs • {patient.gender}
                                {patient.phone_number && (
                                  <span className="ml-2 text-blue-400">
                                    <FiPhone className="inline" size={10} /> {patient.phone_number}
                                  </span>
                                )}
                              </p>
                            </div>
                            <FiArrowRight className="text-gray-300 group-hover:text-purple-500 transition-colors" size={14} />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Add Patient Modal (inline) */}
            <AnimatePresence>
              {showAddPatientModal && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                  className="border-b border-gray-100 overflow-hidden"
                >
                  <div className="px-6 py-4 bg-emerald-50 border-b border-emerald-100 flex items-center justify-between">
                    <p className="font-semibold text-emerald-700 text-sm flex items-center gap-2"><FiPlus size={14} /> Add New Patient</p>
                    <button onClick={() => setShowAddPatientModal(false)} className="text-emerald-500 hover:text-emerald-700"><FiX size={16} /></button>
                  </div>
                  <form onSubmit={handleAddPatient} className="p-6 space-y-5 max-h-[520px] overflow-y-auto">

                    {/* Basic Info */}
                    <div>
                      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Basic Information</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className={labelClass}>Patient Name *</label>
                          <input type="text" name="pname" value={addPatientData.pname} onChange={handleAddPatientChange} placeholder="Full name" className={inputClass} required />
                        </div>
                        <div>
                          <label className={labelClass}>Patient Email</label>
                          <input type="email" name="patient_email" value={addPatientData.patient_email} onChange={handleAddPatientChange} placeholder="patient@email.com" className={inputClass} />
                        </div>

                        {/* Phone Number — second primary key */}
                        <div className="col-span-2">
                          <label className={labelClass + ' flex items-center gap-1'}>
                            <FiPhone className="text-blue-400" size={10} /> Phone Number *
                          </label>
                          <input
                            type="tel"
                            name="phone_number"
                            value={addPatientData.phone_number}
                            onChange={handleAddPatientChange}
                            placeholder="03001234567 or +923001234567"
                            className={inputClass}
                            required
                          />
                          {addPatientData.phone_number && !isValidPkPhone(addPatientData.phone_number) && (
                            <p className="text-xs text-red-500 mt-1">
                              ⚠️ Enter valid 11 digit mobile no
                            </p>
                          )}
                        </div>

                        <div>
                          <label className={labelClass}>Year of Birth *</label>
                          <input type="number" name="dob" value={addPatientData.dob} onChange={handleAddPatientChange} placeholder="e.g. 1985" min="1920" max={new Date().getFullYear()} className={inputClass} required />
                        </div>
                        <div>
                          <label className={labelClass}>Age *</label>
                          <input type="number" name="age" value={addPatientData.age} placeholder="Calculated automatically" className={`${inputClass} bg-gray-50 cursor-not-allowed`} readOnly required />
                        </div>
                        <div className="col-span-2">
                          <label className={labelClass}>Gender</label>
                          <div className="flex gap-3 mt-1.5">
                            {['Male', 'Female', 'Other'].map((option) => (
                              <label
                                key={option}
                                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-semibold cursor-pointer transition-all ${addPatientData.gender === option
                                    ? 'bg-purple-50 border-purple-500 text-purple-700 shadow-sm'
                                    : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
                                  }`}
                              >
                                <input
                                  type="radio"
                                  name="gender"
                                  value={option}
                                  checked={addPatientData.gender === option}
                                  onChange={handleAddPatientChange}
                                  className="sr-only"
                                />
                                <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center transition-all ${addPatientData.gender === option
                                    ? 'border-purple-600 bg-purple-600'
                                    : 'border-gray-300 bg-white'
                                  }`}>
                                  {addPatientData.gender === option && (
                                    <span className="w-1.5 h-1.5 rounded-full bg-white" />
                                  )}
                                </span>
                                {option}
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Vitals */}
                    <div>
                      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Vital Signs</p>
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className={labelClass + ' flex items-center gap-1'}><FiHeart className="text-red-400" size={10} /> BP</label>
                          <input type="text" name="bp" value={addPatientData.bp} onChange={handleAddPatientChange} placeholder="120/80" className={inputClass} />
                        </div>
                        <div>
                          <label className={labelClass}>Pulse</label>
                          <input type="text" name="pulse" value={addPatientData.pulse} onChange={handleAddPatientChange} placeholder="72/min" className={inputClass} />
                        </div>
                        <div>
                          <label className={labelClass + ' flex items-center gap-1'}><FiDroplet className="text-blue-400" size={10} /> BMI</label>
                          <input
                            type="text"
                            name="bmi"
                            value={addPatientData.bmi}
                            placeholder="Auto"
                            className={inputClass + ' bg-gray-50 cursor-not-allowed'}
                            readOnly
                          />
                        </div>
                        <div>
                          <label className={labelClass}>Weight (kg)</label>
                          <input type="number" name="weight" value={addPatientData.weight} onChange={handleAddPatientChange} placeholder="kg" step="0.1" className={inputClass} />
                        </div>
                        <div>
                          <label className={labelClass}>Height (Feet / Inches)</label>
                          <div className="grid grid-cols-2 gap-2">
                            <input
                              type="number"
                              placeholder="Ft"
                              value={heightFeet}
                              onChange={(e) => setHeightFeet(e.target.value)}
                              className={inputClass}
                              min="0"
                              max="8"
                            />
                            <input
                              type="number"
                              placeholder="In"
                              value={heightInches}
                              onChange={(e) => setHeightInches(e.target.value)}
                              className={inputClass}
                              min="0"
                              max="11.9"
                              step="0.1"
                            />
                          </div>
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5 mb-1.5 relative">
                            <label className={labelClass + ' mb-0'}>Height (cm)</label>
                            <button
                              type="button"
                              onClick={() => setShowHeightInfo(!showHeightInfo)}
                              className="text-blue-500 hover:text-blue-700 flex items-center justify-center p-0.5 rounded-full hover:bg-blue-50 transition-colors"
                            >
                              <FiInfo size={14} />
                            </button>

                            {/* Tooltip */}
                            <AnimatePresence>
                              {showHeightInfo && (
                                <motion.div
                                  initial={{ opacity: 0, scale: 0.95, y: 5 }}
                                  animate={{ opacity: 1, scale: 1, y: 0 }}
                                  exit={{ opacity: 0, scale: 0.95, y: 5 }}
                                  className="absolute bottom-6 left-0 bg-gray-900/95 backdrop-blur-sm text-white text-xs p-3 rounded-xl shadow-xl z-50 w-52 border border-gray-850"
                                >
                                  <div className="font-bold border-b border-gray-800 pb-1.5 mb-1.5 text-purple-300">Height Conversion Info</div>
                                  <div className="space-y-1 text-gray-200">
                                    <div>• 1 ft = <span className="font-semibold text-white">30.48 cm</span></div>
                                    <div>• 1 inch = <span className="font-semibold text-white">2.54 cm</span></div>
                                  </div>
                                  <div className="mt-2 pt-1.5 border-t border-gray-850 text-[10px] text-gray-400">
                                    Formula: <span className="text-gray-300">(Ft × 30.48) + (In × 2.54)</span>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                          <input
                            type="number"
                            name="height"
                            value={addPatientData.height}
                            placeholder="Calculated"
                            className={inputClass + ' bg-gray-50 cursor-not-allowed'}
                            readOnly
                          />
                        </div>
                      </div>
                    </div>

                    {/* Clinical Info */}
                    <div>
                      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Clinical Information</p>
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className={labelClass}>Disease</label>
                          <select name="disease" value={addPatientData.disease} onChange={handleAddPatientChange} className={inputClass}>
                            <option value="">Select Disease</option>
                            <option value="Diabetes Type 1">Diabetes Type 1</option>
                            <option value="Diabetes Type 2">Diabetes Type 2</option>
                            <option value="Pre Diabetic">Pre Diabetic</option>
                            <option value="Obesity">Obesity</option>
                            <option value="Gestational Diabetes">Gestational Diabetes</option>
                            <option value="Other">Other</option>
                          </select>
                        </div>
                        <div className="relative" ref={conditionDropdownRef}>
                          <label className={labelClass}>Condition</label>
                          <button
                            type="button"
                            onClick={() => setShowConditionDropdown(!showConditionDropdown)}
                            className={`${inputClass} flex items-center justify-between text-left min-h-[38px]`}
                          >
                            <span className={selectedConditions.length === 0 ? "text-gray-400" : "text-gray-800"}>
                              {selectedConditions.length === 0
                                ? "Select conditions"
                                : selectedConditions.join(', ')}
                            </span>
                            <svg className={`w-4 h-4 text-gray-400 transition-transform ${showConditionDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>

                          <AnimatePresence>
                            {showConditionDropdown && (
                              <motion.div
                                initial={{ opacity: 0, y: 4 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: 4 }}
                                transition={{ duration: 0.15 }}
                                className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg max-h-60 overflow-y-auto p-1.5 space-y-0.5"
                              >
                                {CONDITION_OPTIONS.map((option) => {
                                  const isSelected = selectedConditions.includes(option);
                                  return (
                                    <button
                                      key={option}
                                      type="button"
                                      onClick={() => handleToggleCondition(option)}
                                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-left transition-colors ${isSelected
                                          ? 'bg-purple-50 text-purple-700 font-semibold'
                                          : 'text-gray-600 hover:bg-gray-50'
                                        }`}
                                    >
                                      <span>{option}</span>
                                      {isSelected && (
                                        <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                                        </svg>
                                      )}
                                    </button>
                                  );
                                })}
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                        <div>
                          <label className={labelClass}>Medication</label>
                          <input type="text" name="medication" value={addPatientData.medication} onChange={handleAddPatientChange} placeholder="e.g. Metformin 500mg" className={inputClass} />
                        </div>
                        <div className="col-span-3">
                          <label className={labelClass}>Presenting Complaint</label>
                          <textarea name="presenting_complaint" value={addPatientData.presenting_complaint} onChange={handleAddPatientChange} rows={2} placeholder="Main complaint or reason for visit" className={inputClass + ' resize-none'} />
                        </div>
                      </div>
                    </div>

                    {/* History */}
                    <div>
                      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Medical History</p>
                      <div className="space-y-3">
                        <div>
                          <label className={labelClass}>Family History</label>
                          <textarea name="family_history" value={addPatientData.family_history} onChange={handleAddPatientChange} rows={2} placeholder="Family medical history" className={inputClass + ' resize-none'} />
                        </div>
                        <div>
                          <label className={labelClass}>Social History</label>
                          <textarea name="social_history" value={addPatientData.social_history} onChange={handleAddPatientChange} rows={2} placeholder="Smoking, alcohol, occupation..." className={inputClass + ' resize-none'} />
                        </div>
                        <div>
                          <label className={labelClass}>Allergies</label>
                          <textarea name="allergies" value={addPatientData.allergies} onChange={handleAddPatientChange} rows={2} placeholder="Known allergies" className={inputClass + ' resize-none'} />
                        </div>
                      </div>
                    </div>

                    <div className="pt-1">
                      <p className="text-[10px] text-gray-400 text-center mb-3">
                        By submitting you acknowledge that the patient agrees to archive his/her personal data in the DiabAssist App
                      </p>
                      <div className="flex gap-3">
                        <button type="button" onClick={() => setShowAddPatientModal(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold text-sm transition-colors">Cancel</button>
                        <button type="submit" disabled={isLoading} className="flex-1 py-3 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-md hover:shadow-lg hover:-translate-y-0.5" style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}>
                          {isLoading ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Adding...</> : <><FiCheckCircle size={15} /> Add Patient</>}
                        </button>
                      </div>
                    </div>
                  </form>
                </motion.div>
              )}
            </AnimatePresence>

            {/* -------------------------
                Patient Verification Header
            ------------------------- */}
            <div className="px-6 pt-5 pb-6 flex flex-col items-start">
              <p className="text-xs text-gray-400">
                Standard verification using Case ID and Patient ID.
              </p>
              <button
                type="button"
                onClick={() => setShowAddPatientModal(true)}
                className="flex items-center gap-1.5 px-4 py-2 text-white rounded-xl text-xs font-semibold transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5 mt-3"
                style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
              >
                <FiPlus size={14} /> Add Patient
              </button>

              {/* Guidelines & Clinical Studies Buttons */}
              <div className="flex items-center gap-3 justify-center w-full mt-6 pt-6 border-t border-gray-100">
                <button onClick={() => onNavigate?.('guidelines')} className="px-8 py-2.5 bg-white border border-gray-200 rounded-xl font-bold text-gray-800 shadow-sm hover:bg-gray-50 text-sm">
                  Guidelines
                </button>
                <button onClick={() => onNavigate?.('clinical-studies')} className="px-8 py-2.5 bg-white border border-gray-200 rounded-xl font-bold text-gray-800 shadow-sm hover:bg-gray-50 text-sm">
                  Clinical Studies
                </button>
                <button onClick={() => onNavigate?.('product-info')} className="px-8 py-2.5 bg-white border border-gray-200 rounded-xl font-bold text-gray-800 shadow-sm hover:bg-gray-50 text-sm">
                  Product Info
                </button>
              </div>
            </div>

          </div>

          {/* Ad Section */}
          <AdRotator page="verification" />

        </motion.div>
      </div>
    </div>
  );
};

export default PatientVerificationForm;