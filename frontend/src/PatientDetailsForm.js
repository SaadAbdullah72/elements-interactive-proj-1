// PatientDetailsForm.js
// Purpose: Reusable patient details form used inside consultation flows.
// Notes:
// - Manages medication list and derived fields (BMI) for UX convenience.
// - This component is presentation-focused and lifts state up via
//   `setPatientData` so parent components remain authoritative.
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiChevronDown,
  FiChevronUp,
  FiPlus,
  FiX,
  FiActivity,
  FiUser,
  FiCalendar,
  FiDroplet,
  FiPackage,
  FiFileText
} from 'react-icons/fi';

const inputStyle = "w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-400 transition-all duration-200 hover:border-gray-300";

const labelStyle = "flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5";

const PatientDetailsForm = ({ patientData, setPatientData, onSymptomPrediction }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [medications, setMedications] = useState([]);
  const [currentMedication, setCurrentMedication] = useState('');
  const [symptomsInput, setSymptomsInput] = useState('');

  useEffect(() => {
    if (patientData.medication) {
      const meds = patientData.medication.split(',').map(m => m.trim()).filter(m => m);
      setMedications(meds);
    } else {
      setMedications([]);
    }
  }, [patientData.medication]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setPatientData(prev => ({ ...prev, [name]: value }));
  };

  const handleAddMedication = () => {
    if (currentMedication.trim()) {
      setMedications(prev => [...prev, currentMedication.trim()]);
      setCurrentMedication('');
      setPatientData(prev => ({
        ...prev,
        medication: [...(prev.medication ? prev.medication.split(',') : []), currentMedication.trim()].filter(m => m).join(', ')
      }));
    }
  };

  const handleRemoveMedication = (index) => {
    const updatedMeds = medications.filter((_, i) => i !== index);
    setMedications(updatedMeds);
    setPatientData(prev => ({ ...prev, medication: updatedMeds.join(', ') }));
  };

  const handleSymptomPrediction = () => {
    if (symptomsInput.trim()) {
      const symptoms = symptomsInput.split(',').map(s => s.trim()).filter(s => s);
      if (onSymptomPrediction) {
        onSymptomPrediction(symptoms);
      }
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex justify-between items-center px-5 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
            <FiUser className="text-white" size={18} />
          </div>
          <div className="text-left">
            <span className="text-base font-semibold block">Patient Information</span>
            <span className="text-xs text-blue-100 block">Enter patient details for analysis</span>
          </div>
        </div>
        <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center transition-transform duration-200" style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}>
          <FiChevronDown size={18} />
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-5 space-y-4 border-t border-gray-100">
              {/* Patient Name */}
              <div>
                <label htmlFor="patientName" className={labelStyle}>
                  <FiUser className="text-blue-500" size={16} />
                  Patient Name
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    id="patientName"
                    name="patientName"
                    value={patientData.patientName}
                    onChange={handleChange}
                    className={`${inputStyle} ${patientData.patientName ? 'bg-green-50 border-green-200' : ''}`}
                    placeholder="Enter patient name or scan face"
                  />
                  {patientData.patientName && (
                    <div className="flex items-center px-3 py-2 bg-green-100 text-green-700 rounded-xl text-sm font-medium whitespace-nowrap">
                      <FiUser className="mr-1" size={16} />
                      Registered
                    </div>
                  )}
                </div>
              </div>

              {/* Age and Gender Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="age" className={labelStyle}>
                    <FiCalendar className="text-indigo-500" size={16} />
                    Age
                  </label>
                  <input
                    type="number"
                    id="age"
                    name="age"
                    value={patientData.age}
                    onChange={handleChange}
                    className={inputStyle}
                    placeholder="Age"
                  />
                </div>
                <div>
                  <label htmlFor="gender" className={labelStyle}>
                    <FiDroplet className="text-purple-500" size={16} />
                    Gender
                  </label>
                  <select
                    id="gender"
                    name="gender"
                    value={patientData.gender}
                    onChange={handleChange}
                    className={inputStyle}
                  >
                    <option value="">Select gender</option>
                    <option value="Female">Female</option>
                    <option value="Male">Male</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              {/* Disease */}
              <div>
                <label htmlFor="disease" className={labelStyle}>
                  <FiFileText className="text-red-500" size={16} />
                  Disease/Condition <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="disease"
                  name="disease"
                  value={patientData.disease}
                  onChange={handleChange}
                  className={inputStyle}
                  placeholder="e.g., Migraine, Hypertension, Diabetes"
                  required
                />
              </div>

              {/* Multiple Medications */}
              <div>
                <label htmlFor="medication" className={labelStyle}>
                  <FiPackage className="text-amber-500" size={16} />
                  Medications <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2 mb-3">
                  <input
                    type="text"
                    id="medication"
                    name="medication"
                    value={currentMedication}
                    onChange={(e) => setCurrentMedication(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddMedication())}
                    className={`${inputStyle} flex-1`}
                    placeholder="Add a medication"
                  />
                  <button
                    onClick={handleAddMedication}
                    className="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors flex items-center gap-2 font-medium shadow-md hover:shadow-lg"
                  >
                    <FiPlus size={18} />
                    Add
                  </button>
                </div>
                {medications.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {medications.map((med, index) => (
                      <motion.span
                        key={index}
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.8, opacity: 0 }}
                        className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium border border-blue-200"
                      >
                        <FiPackage size={14} />
                        {med}
                        <button
                          onClick={() => handleRemoveMedication(index)}
                          className="hover:bg-blue-200 rounded p-0.5 transition-colors"
                        >
                          <FiX size={14} />
                        </button>
                      </motion.span>
                    ))}
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
                  <FiPlus size={12} />
                  Tip: Add multiple medications one at a time or use commas
                </p>
              </div>

              {/* Symptom Prediction */}
              <div className="border-t border-gray-100 pt-4">
                <label className={labelStyle}>
                  <FiActivity className="text-emerald-500" size={16} />
                  Symptom Checker
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={symptomsInput}
                    onChange={(e) => setSymptomsInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleSymptomPrediction())}
                    className={`${inputStyle} flex-1`}
                    placeholder="Enter symptoms: headache, nausea, fatigue"
                  />
                  <button
                    onClick={handleSymptomPrediction}
                    className="px-4 py-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 transition-colors flex items-center gap-2 font-medium shadow-md hover:shadow-lg whitespace-nowrap"
                  >
                    <FiActivity size={18} />
                    Analyze
                  </button>
                </div>
                <p className="text-xs text-gray-500">
                  Enter symptoms separated by commas to get AI-powered disease predictions
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PatientDetailsForm;
