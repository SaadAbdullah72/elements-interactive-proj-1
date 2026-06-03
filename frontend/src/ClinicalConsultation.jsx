// ClinicalConsultation.jsx
// Purpose: The clinician-facing consultation UI that manages sessions,
// structured AI queries, guideline selection, and reporting.
// Notes:
// - Handles session creation and message history; delegates AI calls
//   to backend endpoints. Keep sensitive logic server-side.
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiActivity,
  FiPackage,
  FiMessageSquare,
  FiSend,
  FiCheckCircle,
  FiAlertTriangle,
  FiXCircle,
  FiUser,
  FiArrowLeft,
  FiDroplet,
  FiHeart,
  FiInfo,
  FiDownload,
  FiAlertCircle,
  FiShield,
  FiBook,
  FiMail,
  FiX
} from 'react-icons/fi';
import axios from 'axios';
import { API_URL } from './apiConfig';
import AppHeader from './AppHeader';


const ClinicalConsultation = ({ patientData, onBack, onLogout }) => {
  const [editableData, setEditableData] = useState({ ...patientData });
  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState('Generic');
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [messages, setMessages] = useState([]);
  const [conversationType, setConversationType] = useState('generic');
  
  // New: Session management
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [showSessions, setShowSessions] = useState(false);
  
  // New: Structured response & guidelines
  const [structuredResponse, setStructuredResponse] = useState(null);
  const [guidelines, setGuidelines] = useState(null);
  const [guidelinesLoading, setGuidelinesLoading] = useState(false);
  
  // New: Email notification
  const [notifyPatient, setNotifyPatient] = useState(false);
  const [reportDownloading, setReportDownloading] = useState(false);

   const token = sessionStorage.getItem('authToken');
  const createSession = async () => {
    try {
      const response = await axios.post(
        `${API_URL}/api/consultations/sessions`,
        {
          patient_id: editableData.patid || null,
          patient_name: editableData.pname || null,
          patient_email: editableData.patient_email || null,
          title: `Consultation: ${editableData.pname} - ${new Date().toLocaleDateString()}`
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSessionId(response.data.id);
      setMessages([]);
      setStructuredResponse(null);
      setAnalysisResult(null);
      return response.data.id;
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create consultation session');
      return null;
    }
  };

  // Fetch all sessions
  const fetchSessions = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/api/consultations/sessions`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSessions(response.data);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    }
  };

  // Fetch messages for a session
  const loadSession = async (id) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/consultations/sessions/${id}/messages`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSessionId(id);
      setMessages(response.data);
      setShowSessions(false);
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  // Delete a session
  const deleteSession = async (id) => {
    if (!window.confirm('Delete this session? This cannot be undone.')) return;
    try {
      await axios.delete(
        `${API_URL}/api/consultations/sessions/${id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (sessionId === id) {
        setSessionId(null);
        setMessages([]);
        setStructuredResponse(null);
      }
      fetchSessions();
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  // Fetch guidelines metadata
  const fetchGuidelines = async () => {
    setGuidelinesLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/consultations/guidelines`);
      setGuidelines(response.data);
    } catch (error) {
      console.error('Failed to fetch guidelines:', error);
    } finally {
      setGuidelinesLoading(false);
    }
  };

  // Download PDF report
  const downloadReport = async () => {
    if (!sessionId) return;
    setReportDownloading(true);
    try {
      const response = await axios.get(
        `${API_URL}/api/consultations/sessions/${sessionId}/report`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `IntelliHealth_Report_${editableData.pname}_${new Date().toISOString().split('T')[0]}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      if (error.response?.status === 422) {
        alert('No clinical analysis in this session yet. Generate an analysis first.');
      } else {
        console.error('Failed to download report:', error);
        alert('Failed to download report');
      }
    } finally {
      setReportDownloading(false);
    }
  };

  // Initialize guidelines on mount
  useEffect(() => {
    fetchGuidelines();
  }, []);

  // Initialize session on mount
  useEffect(() => {
    if (!sessionId) {
      createSession();
    }
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setEditableData(prev => ({ ...prev, [name]: value }));
  };

  const handleClinicalQuery = async () => {
    if (!query.trim()) {
      alert('Please enter a message');
      return;
    }

    if (conversationType === 'clinical' && (!editableData.disease || !editableData.medication)) {
      alert('Please ensure disease and medication fields are filled for clinical queries');
      return;
    }

    // Ensure session exists
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      currentSessionId = await createSession();
      if (!currentSessionId) return;
    }

    setIsLoading(true);
    try {
      // Add user message to UI immediately
      setMessages(prev => [...prev, { role: 'user', content: query, timestamp: new Date().toISOString() }]);

      const payload = {
        message: query,
        patient_name: editableData.pname || null,
        patient_age: editableData.age ? parseInt(editableData.age) : null,
        patient_gender: editableData.gender || null,
        patient_medical_history: editableData.disease || null,
        patient_email: editableData.patient_email || null,
        medications: editableData.medication || null,
        lab_results: editableData.presenting_complaint || null,
        bp: editableData.bp || null,
        bmi: editableData.bmi ? parseFloat(editableData.bmi) : null,
        notify_patient: notifyPatient && editableData.patient_email ? true : false
      };

      const response = await axios.post(
        `${API_URL}/api/consultations/sessions/${currentSessionId}/chat`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Parse structured response
      const structured = response.data.structured_response;
      setStructuredResponse(structured);
      setAnalysisResult(response.data);

      // Add assistant message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: structured,
        timestamp: response.data.timestamp
      }]);

      setQuery('');
      setShowAnalysis(true);

    } catch (error) {
      console.error('Error in chat query:', error);
      alert('Failed to process query. Please try again.');
      // Remove the user message if request failed
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickQuery = async (quickQuery) => {
    setQuery(quickQuery);
    
    // Ensure session exists
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      currentSessionId = await createSession();
      if (!currentSessionId) return;
    }

    setIsLoading(true);
    try {
      // Add user message
      setMessages(prev => [...prev, { role: 'user', content: quickQuery, timestamp: new Date().toISOString() }]);

      const payload = {
        message: quickQuery,
        patient_name: editableData.pname || null,
        patient_age: editableData.age ? parseInt(editableData.age) : null,
        patient_gender: editableData.gender || null,
        patient_medical_history: editableData.disease || null,
        patient_email: editableData.patient_email || null,
        medications: editableData.medication || null,
        lab_results: editableData.presenting_complaint || null,
        bp: editableData.bp || null,
        bmi: editableData.bmi ? parseFloat(editableData.bmi) : null,
        notify_patient: false  // Quick queries don't notify by default
      };

      const response = await axios.post(
        `${API_URL}/api/consultations/sessions/${currentSessionId}/chat`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const structured = response.data.structured_response;
      setStructuredResponse(structured);
      setAnalysisResult(response.data);

      // Add assistant message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: structured,
        timestamp: response.data.timestamp
      }]);

      setQuery('');
      setShowAnalysis(true);

    } catch (error) {
      console.error('Quick query error:', error);
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  // ============ NEW: Structured Response Rendering Components ============
  
  const SafetyFlagCard = ({ flags }) => {
    if (!flags || flags.length === 0) return null;
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-red-50 border-2 border-red-200 rounded-xl p-4 mb-4"
      >
        <div className="flex items-start gap-3">
          <div className="bg-red-500 text-white rounded-full p-2 flex-shrink-0 mt-0.5">
            <FiAlertCircle size={18} />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-red-700 mb-2">⚠️ CRITICAL SAFETY FLAGS</h3>
            <div className="space-y-1">
              {flags.map((flag, idx) => (
                <p key={idx} className="text-sm text-red-700">{flag}</p>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    );
  };

  const DrugInteractionCard = ({ interactions }) => {
    if (!interactions || interactions.length === 0) return null;
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-amber-50 border-2 border-amber-300 rounded-xl p-4 mb-4"
      >
        <div className="flex items-start gap-3">
          <div className="bg-amber-500 text-white rounded-full p-2 flex-shrink-0 mt-0.5">
            <FiAlertTriangle size={18} />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-amber-700 mb-2">🔄 Drug Interactions</h3>
            <div className="space-y-2">
              {interactions.map((interaction, idx) => (
                <p key={idx} className="text-sm text-amber-700">{interaction}</p>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    );
  };

  const StructuredResponseRenderer = ({ response }) => {
    if (!response) return null;

    const renderRiskLevel = (level) => {
      const config = {
        critical: { bg: 'bg-red-100', border: 'border-red-300', text: 'text-red-700', icon: '🔴' },
        high: { bg: 'bg-orange-100', border: 'border-orange-300', text: 'text-orange-700', icon: '🟠' },
        moderate: { bg: 'bg-yellow-100', border: 'border-yellow-300', text: 'text-yellow-700', icon: '🟡' },
        low: { bg: 'bg-green-100', border: 'border-green-300', text: 'text-green-700', icon: '🟢' }
      };
      const c = config[level?.toLowerCase()] || config.moderate;
      return (
        <div className={`${c.bg} border ${c.border} rounded-lg p-3 ${c.text} text-sm font-semibold`}>
          {c.icon} Risk Level: {level?.toUpperCase() || 'MODERATE'}
        </div>
      );
    };

    return (
      <div className="space-y-4">
        {/* Safety Flags - ALWAYS FIRST */}
        {response.safety_flags && <SafetyFlagCard flags={response.safety_flags} />}

        {/* Drug Interactions - SECOND */}
        {response.drug_interactions && <DrugInteractionCard interactions={response.drug_interactions} />}

        {/* Patient Card */}
        {response.show_patient_card && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-bold text-blue-900 mb-2">👤 Patient Summary</h4>
            <p className="text-sm text-blue-800">{editableData.pname}, {editableData.age} years old, {editableData.gender}</p>
            {editableData.disease && <p className="text-sm text-blue-800">Condition: {editableData.disease}</p>}
          </div>
        )}

        {/* Risk Level */}
        {response.risk_level && renderRiskLevel(response.risk_level)}

        {/* Clinical Summary */}
        {response.clinical_summary && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <h4 className="font-bold text-purple-900 mb-2">📋 Clinical Summary</h4>
            <p className="text-sm text-purple-800 leading-relaxed">{response.clinical_summary}</p>
          </div>
        )}

        {/* Assessment */}
        {response.assessment && response.assessment.length > 0 && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <h4 className="font-bold text-indigo-900 mb-2">🔍 Assessment</h4>
            <ul className="space-y-1">
              {response.assessment.map((item, idx) => (
                <li key={idx} className="text-sm text-indigo-800 flex gap-2">
                  <span className="text-indigo-500 font-bold">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {response.recommendations && response.recommendations.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h4 className="font-bold text-green-900 mb-2">💡 Recommendations</h4>
            <ul className="space-y-1">
              {response.recommendations.map((rec, idx) => (
                <li key={idx} className="text-sm text-green-800 flex gap-2">
                  <span className="text-green-500 font-bold">✓</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Medications */}
        {response.medications && response.medications.length > 0 && (
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
            <h4 className="font-bold text-teal-900 mb-2">💊 Medications</h4>
            <ul className="space-y-1">
              {response.medications.map((med, idx) => (
                <li key={idx} className="text-sm text-teal-800 flex gap-2">
                  <span className="text-teal-500 font-bold">•</span>
                  <span>{med}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Risk Details */}
        {response.risk_details && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <h4 className="font-bold text-orange-900 mb-2">📊 Risk Details</h4>
            <p className="text-sm text-orange-800">{response.risk_details}</p>
          </div>
        )}

        {/* Lab Interpretation */}
        {response.lab_interpretation && (
          <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-4">
            <h4 className="font-bold text-cyan-900 mb-2">🧪 Lab Interpretation</h4>
            <p className="text-sm text-cyan-800">{response.lab_interpretation}</p>
          </div>
        )}

        {/* Follow-up Plan */}
        {response.follow_up && (
          <div className="bg-pink-50 border border-pink-200 rounded-lg p-4">
            <h4 className="font-bold text-pink-900 mb-2">📅 Follow-up Plan</h4>
            <p className="text-sm text-pink-800">{response.follow_up}</p>
          </div>
        )}

        {/* Guideline References */}
        {response.guideline_references && response.guideline_references.length > 0 && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-bold text-gray-900 mb-2">📚 Clinical Guidelines</h4>
            <div className="flex flex-wrap gap-2">
              {response.guideline_references.map((ref, idx) => (
                <span key={idx} className="inline-block bg-white border border-gray-300 rounded-full px-3 py-1 text-xs font-medium text-gray-700">
                  {ref}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* General Response (for non-clinical) */}
        {response.general_response && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900 leading-relaxed">{response.general_response}</p>
          </div>
        )}
      </div>
    );
  };

  const getDecisionConfig = (decision) => {
    switch (decision) {
      case 'SAFE':
        return {
          icon: FiCheckCircle,
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          bgGradient: 'bg-green-500'
        };
      case 'CAUTION':
        return {
          icon: FiAlertTriangle,
          color: 'text-amber-600',
          bgColor: 'bg-amber-50',
          borderColor: 'border-amber-200',
          bgGradient: 'bg-amber-500'
        };
      case 'UNSAFE':
        return {
          icon: FiXCircle,
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          bgGradient: 'bg-red-500'
        };
      default:
        return {
          icon: FiInfo,
          color: 'text-purple-600',
          bgColor: 'bg-teal-50',
          borderColor: 'border-purple-200',
          bgGradient: 'bg-purple-400'
        };
    }
  };

  return (
    <div className="min-h-screen bg-purple-50">
      <AppHeader />
      {/* Top Bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <FiArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-purple-400 flex items-center justify-center text-white font-semibold">
              {editableData.pname.charAt(0)}
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">{editableData.pname}</h1>
              <p className="text-xs text-gray-500">{editableData.patid} • {editableData.age} yrs • {editableData.gender}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onLogout}
            className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors text-sm font-medium"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Patient Details */}
          <div className="lg:col-span-1 space-y-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden"
            >
              <div className="bg-purple-400 px-5 py-4 text-white">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <FiUser />
                  Patient Details
                </h2>
                <p className="text-xs text-teal-100 mt-1">Editable information</p>
              </div>

              <div className="p-5 space-y-4">
                {/* Case Info */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Case ID</label>
                    <input
                      type="text"
                      name="caseid"
                      value={editableData.caseid}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Patient ID</label>
                    <input
                      type="text"
                      name="patid"
                      value={editableData.patid}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>

                {/* Basic Info */}
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Name</label>
                  <input
                    type="text"
                    name="pname"
                    value={editableData.pname}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">DOB</label>
                    <input
                      type="date"
                      name="dob"
                      value={editableData.dob}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Age</label>
                    <input
                      type="number"
                      name="age"
                      value={editableData.age}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Gender</label>
                  <select
                    name="gender"
                    value={editableData.gender || ''}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="">Select</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                {/* Clinical Info */}
                <div className="border-t border-gray-200 pt-4 space-y-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center gap-1">
                      <FiActivity className="text-red-500" />
                      Disease/Condition
                    </label>
                    <input
                      type="text"
                      name="disease"
                      value={editableData.disease || ''}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="e.g., Type 2 Diabetes"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center gap-1">
                      <FiPackage className="text-purple-500" />
                      Medication
                    </label>
                    <input
                      type="text"
                      name="medication"
                      value={editableData.medication || ''}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="e.g., Metformin 1000mg"
                    />
                  </div>
                </div>

                {/* Vitals */}
                <div className="border-t border-gray-200 pt-4">
                  <h3 className="text-xs font-semibold text-gray-700 mb-3">Vital Signs</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center gap-1">
                        <FiHeart className="text-red-500" />
                        BP
                      </label>
                      <input
                        type="text"
                        name="bp"
                        value={editableData.bp || ''}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        placeholder="120/80"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">
                        Pulse
                      </label>
                      <input
                        type="text"
                        name="pulse"
                        value={editableData.pulse || ''}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        placeholder="72/min"
                      />
                    </div>
                  </div>
                  <div className="mt-3">
                    <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center gap-1">
                      <FiDroplet className="text-purple-500" />
                      BMI
                    </label>
                    <input
                      type="number"
                      name="bmi"
                      value={editableData.bmi || ''}
                      onChange={handleChange}
                      step="0.1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="25.5"
                    />
                  </div>
                </div>

                {/* History */}
                <div className="border-t border-gray-200 pt-4 space-y-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Presenting Complaint</label>
                    <textarea
                      name="presenting_complaint"
                      value={editableData.presenting_complaint || ''}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Family History</label>
                    <textarea
                      name="family_history"
                      value={editableData.family_history || ''}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Social History</label>
                    <textarea
                      name="social_history"
                      value={editableData.social_history || ''}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Allergies</label>
                    <textarea
                      name="allergies"
                      value={editableData.allergies || ''}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Column - AI Analysis & Chat */}
          <div className="lg:col-span-2 space-y-4">

            {/* NEW: Guidelines Badge */}
            {guidelines && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-indigo-200 rounded-xl p-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FiBook className="text-indigo-600" size={18} />
                  <div>
                    <p className="text-sm font-semibold text-indigo-900">Active Clinical Guidelines</p>
                    <p className="text-xs text-indigo-700">{guidelines.total_sources} sources • v{guidelines.version?.split('v')[1] || '2026'}</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowSessions(!showSessions)}
                  className="px-3 py-1 bg-indigo-600 text-white text-xs rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  Sessions ({sessions.length})
                </button>
              </div>
            )}

            {/* NEW: Sessions Panel */}
            <AnimatePresence>
              {showSessions && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="bg-white rounded-xl shadow-lg border border-gray-200 p-4"
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-bold text-gray-900">Consultation Sessions</h3>
                    <button onClick={() => setShowSessions(false)} className="p-1 hover:bg-gray-100 rounded">
                      <FiX size={18} />
                    </button>
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {sessions.length === 0 ? (
                      <p className="text-sm text-gray-500">No previous sessions</p>
                    ) : (
                      sessions.map(s => (
                        <div key={s.id} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{s.title}</p>
                            <p className="text-xs text-gray-500">{s.message_count} messages</p>
                          </div>
                          <div className="flex gap-1">
                            <button
                              onClick={() => loadSession(s.id)}
                              className="px-3 py-1 bg-purple-100 text-purple-700 text-xs rounded hover:bg-purple-200 transition-colors"
                            >
                              Load
                            </button>
                            <button
                              onClick={() => deleteSession(s.id)}
                              className="px-2 py-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                            >
                              <FiX size={14} />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <button
                    onClick={createSession}
                    className="w-full mt-3 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    + New Session
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* NEW: Structured Analysis Result */}
            <AnimatePresence>
              {showAnalysis && structuredResponse && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden"
                >
                  <div className="bg-gradient-to-r from-purple-400 to-indigo-500 px-6 py-5 text-white flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                        <FiCheckCircle className="text-xl" />
                      </div>
                      <div>
                        <h2 className="text-lg font-bold">Clinical Analysis</h2>
                        <p className="text-xs text-purple-100">
                          {structuredResponse.response_type || 'Analysis'} • {new Date(analysisResult.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={downloadReport}
                        disabled={reportDownloading}
                        className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-medium disabled:opacity-50"
                      >
                        <FiDownload size={16} />
                        {reportDownloading ? 'Downloading...' : 'PDF Report'}
                      </button>
                    </div>
                  </div>
                  <div className="p-6 max-h-96 overflow-y-auto">
                    <StructuredResponseRenderer response={structuredResponse} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* AI Query Interface */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden"
            >
              <div className="bg-purple-400 px-6 py-5 text-white">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <FiMessageSquare />
                  AI Clinical Assistant
                </h2>
                <p className="text-xs text-purple-100 mt-1">Ask questions about this patient's case</p>
              </div>

              {/* NEW: Email Notification Toggle */}
              <div className="p-4 bg-blue-50 border-b border-blue-200">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifyPatient}
                    onChange={(e) => setNotifyPatient(e.target.checked)}
                    className="w-4 h-4 accent-blue-600"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-900">Notify Patient via Email</p>
                    <p className="text-xs text-blue-700">
                      {editableData.patient_email ? `${editableData.patient_email}` : 'Add patient email above'}
                    </p>
                  </div>
                  <FiMail className="text-blue-600" size={18} />
                </label>
              </div>

              {/* Conversation Type Selector */}
              <div className="p-5 border-b border-gray-200 bg-gray-50">
                <label className="text-xs font-semibold text-gray-600 mb-2 block uppercase tracking-wide">Conversation Mode</label>
                <select
                  value={conversationType}
                  onChange={(e) => setConversationType(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                >
                  <option value="generic">📝 General Conversation (Any Topic)</option>
                  <option value="clinical">💊 Clinical Consultation (Medications & Disease)</option>
                  <option value="lifestyle">🏃 Lifestyle & Wellness</option>
                  <option value="preventive">🛡️ Preventive Health</option>
                  <option value="lab-results">🧪 Lab Results & Diagnostics</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Select the type of conversation or consultation you need</p>
              </div>

              {/* Query Type Selector */}
              <div className="p-5 border-b border-gray-200 bg-gray-50">
                <label className="text-xs font-semibold text-gray-600 mb-2 block uppercase tracking-wide">Analysis Type</label>
                <select
                  value={queryType}
                  onChange={(e) => setQueryType(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                >
                  <option value="Generic">📋 Generic Query</option>
                  <option value="Explain">📖 Explain Condition</option>
                  <option value="Diagnosis">🔍 Diagnosis Analysis</option>
                  <option value="Treatment">💊 Treatment Plan</option>
                  <option value="Side Effects">⚠️ Side Effects & Monitoring</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Select the type of analysis or query</p>
              </div>

              {/* Quick Query Buttons */}
              <div className="p-5 border-b border-gray-200">
                <h3 className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">Quick Queries</h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => handleQuickQuery("Explain the mechanism of action for this medication")}
                    className="px-4 py-2 bg-purple-50 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-100 transition-colors"
                  >
                    💊 Drug Mechanism
                  </button>
                  <button
                    onClick={() => handleQuickQuery("What are the common side effects and monitoring requirements?")}
                    className="px-4 py-2 bg-purple-50 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-100 transition-colors"
                  >
                    ⚠️ Side Effects
                  </button>
                  <button
                    onClick={() => handleQuickQuery("Are there any drug interactions to be aware of?")}
                    className="px-4 py-2 bg-amber-50 text-amber-700 rounded-lg text-sm font-medium hover:bg-amber-100 transition-colors"
                  >
                    🔄 Interactions
                  </button>
                  <button
                    onClick={() => handleQuickQuery("What lifestyle modifications should be recommended?")}
                    className="px-4 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-medium hover:bg-green-100 transition-colors"
                  >
                    🏃 Lifestyle Advice
                  </button>
                  <button
                    onClick={() => handleQuickQuery("What are the treatment goals and follow-up plan?")}
                    className="px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-medium hover:bg-indigo-100 transition-colors"
                  >
                    📋 Follow-up Plan
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="p-5 h-80 overflow-y-auto bg-gray-50">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                    <div className="text-center">
                      <FiMessageSquare className="text-4xl mx-auto mb-2 opacity-50" />
                      <p>Select a quick query or type your question below</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        {msg.role === 'user' ? (
                          <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-indigo-600 text-white">
                            <p className="text-sm leading-relaxed">{msg.content}</p>
                          </div>
                        ) : (
                          <div className="max-w-[95%] bg-white border border-gray-200 rounded-2xl p-4">
                            <StructuredResponseRenderer response={msg.content} />
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>

              {/* Query Input */}
              <div className="p-5 border-t border-gray-200">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleClinicalQuery()}
                    placeholder="Type your clinical query here..."
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  />
                  <button
                    onClick={handleClinicalQuery}
                    disabled={isLoading}
                    className="px-6 py-3 bg-purple-400 text-white rounded-xl transition-all disabled:opacity-50 flex items-center gap-2 font-medium shadow-lg"
                  >
                    {isLoading ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <FiSend />
                    )}
                    Analyze
                  </button>
                </div>
              </div>
            </motion.div>

            {/* Advertisement Section */}
            <div className="mt-4">
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
        </div>
      </div>
    </div>
  );
};

export default ClinicalConsultation;