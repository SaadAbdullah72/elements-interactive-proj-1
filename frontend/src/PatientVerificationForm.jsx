// PatientVerificationForm.jsx
// Purpose: Verify or add patients prior to consultation. This form
// interacts with doctor-protected endpoints and should be used only by
// authenticated clinicians. It provides searching, adding and selection
// helpers and computes derived fields (e.g., BMI) client-side for UX.
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
  FiActivity
} from 'react-icons/fi';
import axios from 'axios';
import { API_URL } from './apiConfig';
import AppHeader from './AppHeader';

const PatientVerificationForm = ({ onVerificationSuccess, onCancel }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showPatientList, setShowPatientList] = useState(false);
  const [showAddPatientModal, setShowAddPatientModal] = useState(false);
  const [patients, setPatients] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  const [formData, setFormData] = useState({
    caseid: '',
    patid: '',
    pname: '',
    dob: '',
    age: ''
  });

  const [addPatientData, setAddPatientData] = useState({
    pname: '',
    patient_email: '',
    dob: '',
    age: '',
    gender: '',
    disease: '',
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

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
  };

  const handleAddPatientChange = (e) => {
    const { name, value } = e.target;
    setAddPatientData(prev => ({ ...prev, [name]: value }));
  };

  useEffect(() => {
    const weight = parseFloat(addPatientData.weight);
    const height = parseFloat(addPatientData.height);
    if (weight > 0 && height > 0) {
      const heightInMeters = height / 100;
      const calculatedBmi = (weight / (heightInMeters * heightInMeters)).toFixed(1);
      setAddPatientData(prev => ({ ...prev, bmi: calculatedBmi }));
    } else {
      // Reset BMI if weight or height is cleared
      setAddPatientData(prev => ({ ...prev, bmi: '' }));
    }
  }, [addPatientData.weight, addPatientData.height]);

  const loadPatients = async () => {
    try {
      const token = sessionStorage.getItem('authToken');
      const response = await axios.get(`${API_URL}/api/doctor/patients`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPatients(response.data);
      setShowPatientList(true);
      setSearchQuery('');
    } catch (err) {
      console.error('Failed to load patients:', err);
    }
  };

  const filteredPatients = patients.filter(patient => {
    const q = searchQuery.toLowerCase();
    if (!q) return true;
    return (
      (patient.pname && patient.pname.toLowerCase().includes(q)) ||
      (patient.patid && patient.patid.toLowerCase().includes(q))
    );
  });

  const selectPatient = (patient) => {
    setFormData({
      caseid: patient.caseid,
      patid: patient.patid,
      pname: patient.pname,
      dob: patient.dob,
      age: patient.age.toString(),
      patient_email: patient.patient_email || ''
    });
    setShowPatientList(false);
  };

  // Helper: safely parse a float field — returns null if empty or NaN
  const safeFloat = (val) => {
    if (val === '' || val === null || val === undefined) return null;
    const parsed = parseFloat(val);
    return isNaN(parsed) ? null : parsed;
  };

  const handleAddPatient = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);
    try {
      const payload = {
        pname: addPatientData.pname,
        patient_email: addPatientData.patient_email || null,
        dob: addPatientData.dob,
        age: parseInt(addPatientData.age),
        gender: addPatientData.gender || null,
        disease: addPatientData.disease || null,
        medication: addPatientData.medication || null,
        presenting_complaint: addPatientData.presenting_complaint || null,
        bp: addPatientData.bp || null,
        pulse: addPatientData.pulse || null,
        // FIX: use safeFloat so empty strings become null, not NaN or ""
        bmi: safeFloat(addPatientData.bmi),
        weight: safeFloat(addPatientData.weight),
        height: safeFloat(addPatientData.height),
        family_history: addPatientData.family_history || null,
        social_history: addPatientData.social_history || null,
        allergies: addPatientData.allergies || null,
        case_notes: addPatientData.case_notes || null
      };
      const token = sessionStorage.getItem('authToken');
      const response = await axios.post(`${API_URL}/api/doctor/patient/add`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.success) {
        setSuccess(`✅ Patient added! Case ID: ${response.data.patient.caseid}, Patient ID: ${response.data.patient.patid}`);
        setTimeout(() => {
          setShowAddPatientModal(false);
          setAddPatientData({
            pname: '', patient_email: '', dob: '', age: '', gender: '',
            disease: '', medication: '', presenting_complaint: '', bp: '',
            pulse: '', bmi: '', weight: '', height: '', family_history: '',
            social_history: '', allergies: '', case_notes: ''
          });
          setSuccess('');
        }, 2000);
      }
    } catch (err) {
      setError('❌ Failed to add patient. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);
    try {
      const token = sessionStorage.getItem('authToken');
      const response = await axios.post(`${API_URL}/api/doctor/verify-patient`, {
        caseid: formData.caseid,
        patid: formData.patid,
        pname: formData.pname,
        dob: formData.dob,
        age: parseInt(formData.age)
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.verified) {
        setSuccess('✅ Patient verified successfully!');
        setTimeout(() => { onVerificationSuccess(response.data.patient); }, 1000);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError('❌ Patient not found. Please check the details and try again.');
      } else if (err.response?.status === 400) {
        const detail = err.response.data.detail;
        if (detail.mismatched_fields) {
          setError(`❌ Details don't match. Mismatched: ${detail.mismatched_fields.join(', ')}`);
        } else {
          setError('❌ Patient verification failed.');
        }
      } else {
        setError('❌ Verification failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all text-gray-800 placeholder-gray-400 text-sm shadow-sm";
  const labelClass = "block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5";

  return (
    <div className="min-h-screen w-full bg-gray-50 flex flex-col">
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
              <h1 className="text-2xl font-bold text-gray-800">Patient Verification</h1>
              <p className="text-sm text-gray-500 mt-0.5">Verify patient identity before consultation</p>
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
                  <p className="text-xs text-gray-400">All fields must match exactly as registered</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowAddPatientModal(true)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-xs font-semibold transition-colors shadow-sm"
                >
                  <FiPlus size={14} /> Add Patient
                </button>
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
                        placeholder="Search by Patient ID or Name..."
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
                              <p className="text-xs text-gray-400 mt-0.5">{patient.patid} • {patient.age} yrs • {patient.gender}</p>
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
                          <label className={labelClass}>Patient Email *</label>
                          <input type="email" name="patient_email" value={addPatientData.patient_email} onChange={handleAddPatientChange} placeholder="patient@email.com" className={inputClass} required />
                        </div>
                        <div>
                          <label className={labelClass}>Date of Birth *</label>
                          <input type="date" name="dob" value={addPatientData.dob} onChange={handleAddPatientChange} className={inputClass} required />
                        </div>
                        <div>
                          <label className={labelClass}>Age *</label>
                          <input type="number" name="age" value={addPatientData.age} onChange={handleAddPatientChange} placeholder="Years" className={inputClass} required />
                        </div>
                        <div className="col-span-2">
                          <label className={labelClass}>Gender</label>
                          <select name="gender" value={addPatientData.gender} onChange={handleAddPatientChange} className={inputClass}>
                            <option value="">Select</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Other">Other</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    {/* Clinical Info */}
                    <div>
                      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Clinical Information</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className={labelClass}>Disease/Condition</label>
                          <input type="text" name="disease" value={addPatientData.disease} onChange={handleAddPatientChange} placeholder="e.g. Diabetes Type 2" className={inputClass} />
                        </div>
                        <div>
                          <label className={labelClass}>Medication</label>
                          <input type="text" name="medication" value={addPatientData.medication} onChange={handleAddPatientChange} placeholder="e.g. Metformin 500mg" className={inputClass} />
                        </div>
                        <div className="col-span-2">
                          <label className={labelClass}>Presenting Complaint</label>
                          <textarea name="presenting_complaint" value={addPatientData.presenting_complaint} onChange={handleAddPatientChange} rows={2} placeholder="Main complaint or reason for visit" className={inputClass + ' resize-none'} />
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
                          <label className={labelClass}>Height (cm)</label>
                          <input type="number" name="height" value={addPatientData.height} onChange={handleAddPatientChange} placeholder="cm" step="0.1" className={inputClass} />
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

                    <div className="flex gap-3 pt-1">
                      <button type="button" onClick={() => setShowAddPatientModal(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold text-sm transition-colors">Cancel</button>
                      <button type="submit" disabled={isLoading} className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-semibold text-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2 shadow-sm">
                        {isLoading ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Adding...</> : <><FiCheckCircle size={15} /> Add Patient</>}
                      </button>
                    </div>
                  </form>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Verification Form */}
            <form onSubmit={handleVerify} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}><FiFileText className="inline mr-1" size={10} />Case ID *</label>
                  <input type="text" name="caseid" value={formData.caseid} onChange={handleChange} placeholder="CASE-2024-00001" className={inputClass} required />
                </div>
                <div>
                  <label className={labelClass}><FiUser className="inline mr-1" size={10} />Patient ID *</label>
                  <input type="text" name="patid" value={formData.patid} onChange={handleChange} placeholder="PAT-000001" className={inputClass} required />
                </div>
              </div>

              <div>
                <label className={labelClass}><FiUser className="inline mr-1" size={10} />Patient Name *</label>
                <input type="text" name="pname" value={formData.pname} onChange={handleChange} placeholder="Full name as registered" className={inputClass} required />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}><FiCalendar className="inline mr-1" size={10} />Date of Birth *</label>
                  <input type="date" name="dob" value={formData.dob} onChange={handleChange} className={inputClass} required />
                </div>
                <div>
                  <label className={labelClass}><FiCalendar className="inline mr-1" size={10} />Age *</label>
                  <input type="number" name="age" value={formData.age} onChange={handleChange} placeholder="Years" className={inputClass} required />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-3.5 rounded-xl font-bold text-white text-sm transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-md"
                style={{ background: 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)' }}
              >
                {isLoading ? (
                  <><div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> Verifying Patient...</>
                ) : (
                  <><FiSearch size={16} /> Verify Patient Details</>
                )}
              </button>
            </form>

            {/* Footer note */}
            <div className="px-6 pb-5">
              <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
                <p className="text-xs text-amber-700">
                  <strong>Note:</strong> All fields must match exactly as registered. Use Browse Patients if unsure about details.
                </p>
              </div>
            </div>
          </div>

          {/* Ad Section */}
          <div className="mt-4 bg-white rounded-2xl border border-gray-100 shadow-sm p-3">
            <a href="#" className="block group" onClick={e => { e.preventDefault(); alert('EI Health Solutions - Advertisement'); }}>
              <div className="flex items-center gap-3">
                <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded font-medium flex-shrink-0">Ad</span>
                <div className="w-16 h-7 rounded overflow-hidden flex-shrink-0">
                  <img src="/edited-photo.png" alt="EI Logo" className="w-full h-full object-cover" onError={e => e.target.style.display = 'none'} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-purple-600 group-hover:text-purple-800 truncate">EI Health Solutions</p>
                  <p className="text-xs text-gray-500 truncate">Advanced Medical Technology for Modern Healthcare</p>
                </div>
                <span className="text-xs text-gray-400 group-hover:text-gray-600 flex-shrink-0">Learn More →</span>
              </div>
            </a>
          </div>

        </motion.div>
      </div>
    </div>
  );
};

export default PatientVerificationForm;