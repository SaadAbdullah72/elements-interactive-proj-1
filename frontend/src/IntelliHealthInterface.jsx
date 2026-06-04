// IntelliHealthInterface.jsx
// Purpose: High-level clinician interface that composes chat, analysis
// results, file uploads, and reporting features into a unified workflow.
// Notes:
// - This component orchestrates many UI pieces; extract helpers or
//   smaller child components if complexity grows further.
import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiUpload,
  FiFileText,
  FiUser,
  FiActivity,
  FiLogOut,
  FiPlus,
  FiImage,
  FiClock,
  FiDownload,
  FiX,
  FiCheck,
  FiEye,
  FiAlertCircle,
  FiMic,
  FiMicOff
} from 'react-icons/fi';
import axios from 'axios';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { API_URL } from './apiConfig';
import AppHeader from './AppHeader';

const stripMarkdown = (text) => {
  if (!text) return '';
  return text
    .replace(/^[#\s*]+|[📋🔍⚠️💡🎯🔬🧪🧠📚💊🏥📅🔄🧬📊🚨]/g, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/^\s*[•\-\*]\s*/gm, '')
    .replace(/\n+/g, ' ')
    .trim();
};

const ChatResponseContent = ({ response, isError }) => {
  if (!response) return null;
  if (isError) {
    return (
      <div className="text-red-700 bg-red-50 p-3 rounded-lg border border-red-100">
        <div className="flex items-start gap-2">
          <FiAlertCircle className="text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm">{response}</p>
        </div>
      </div>
    );
  }
  const lines = response.split('\n');
  return (
    <div className="text-gray-700 text-sm leading-relaxed space-y-1.5">
      {lines.map((line, idx) => {
        const bulletMatch = line.match(/^\s*[•\-\*]\s*(.+)$/);
        if (bulletMatch) {
          return (
            <div key={idx} className="flex items-start gap-2 ml-1">
              <span className="text-purple-500 font-bold flex-shrink-0 mt-0.5">•</span>
              <span>{bulletMatch[1]}</span>
            </div>
          );
        }
        const headingMatch = line.match(/^#{2,3}\s*(.+)$/);
        if (headingMatch) {
          return (
            <h4 key={idx} className="font-bold text-gray-800 mt-3 mb-1 text-sm">
              {headingMatch[1].replace(/[📋🔍⚠️💡🎯🔬🧪🧠📚💊🏥📅🔄🧬📊🚨]/g, '').trim()}
            </h4>
          );
        }
        if (line.includes('**')) {
          const parts = line.split(/\*\*(.+?)\*\*/);
          return (
            <p key={idx} className="mb-1">
              {parts.map((part, i) =>
                i % 2 === 1 ? <strong key={i} className="font-bold text-gray-800">{part}</strong> : part
              )}
            </p>
          );
        }
        if (line.trim()) return <p key={idx} className="mb-1">{line}</p>;
        return null;
      })}
    </div>
  );
};

const IntelliHealthInterface = ({ patientData, onBack, onLogout }) => {
  const [editableData, setEditableData] = useState({
    caseid: patientData?.caseid || '',
    patid: patientData?.patid || '',
    pname: patientData?.pname || '',
    patient_email: patientData?.patient_email || '',
    dob: patientData?.dob || '',
    age: patientData?.age || '',
    gender: patientData?.gender || '',
    disease: patientData?.disease || '',
    medication: patientData?.medication || '',
    presenting_complaint: patientData?.presenting_complaint || '',
    bp: patientData?.bp || '',
    pulse: patientData?.pulse || '',
    bmi: patientData?.bmi || '',
    family_history: patientData?.family_history || '',
    social_history: patientData?.social_history || '',
    allergies: patientData?.allergies || ''
  });

  const [query, setQuery] = useState('');
  const [selectedOption, setSelectedOption] = useState('Explain');
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [demoCases, setDemoCases] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [aiResponse, setAiResponse] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [streamingResponseId, setStreamingResponseId] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingChatId, setSpeakingChatId] = useState(null);
  const [enableVoiceResponse, setEnableVoiceResponse] = useState(false);
  const [speechSynth, setSpeechSynth] = useState(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [patientHistory, setPatientHistory] = useState([]);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [uploadedImageName, setUploadedImageName] = useState('');
  const [uploadedPdfText, setUploadedPdfText] = useState('');
  const [uploadedPdfName, setUploadedPdfName] = useState('');
  const [pdfContent, setPdfContent] = useState('');
  const [showPdfModal, setShowPdfModal] = useState(false);

  const chatContainerRef = useRef(null);
  const speechRef = useRef(null);
  const queryInputRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) setSpeechSynth(window.speechSynthesis);
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setEditableData(prev => ({ ...prev, [name]: value }));
  };

  const streamResponse = (fullText, chatId) => {
    const words = fullText.split(' ');
    let currentIndex = 0;
    let streamedText = '';
    const streamInterval = setInterval(() => {
      if (currentIndex < words.length) {
        const nextBatch = words.slice(currentIndex, currentIndex + 4).join(' ');
        streamedText += (currentIndex > 0 ? ' ' : '') + nextBatch;
        setChatHistory(prev => prev.map(chat =>
          chat.id === chatId ? { ...chat, response: streamedText, isStreaming: true } : chat
        ));
        currentIndex += 4;
        if (chatContainerRef.current) chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
      } else {
        clearInterval(streamInterval);
        setIsStreaming(false);
        setChatHistory(prev => prev.map(chat =>
          chat.id === chatId ? { ...chat, isStreaming: false } : chat
        ));
        if (enableVoiceResponse && speechSynth) {
          const utterance = new SpeechSynthesisUtterance(stripMarkdown(fullText));
          utterance.rate = 0.95; utterance.pitch = 1; utterance.volume = 1;
          utterance.onend = () => { setIsSpeaking(false); setSpeakingChatId(null); speechRef.current = null; };
          utterance.onerror = () => { setIsSpeaking(false); setSpeakingChatId(null); speechRef.current = null; };
          speechRef.current = utterance;
          speechSynth.speak(utterance);
          setIsSpeaking(true); setSpeakingChatId(chatId); setEnableVoiceResponse(false);
        }
      }
    }, 20);
    return () => clearInterval(streamInterval);
  };

  const toggleSpeech = (text, chatId) => {
    if (!speechSynth) return;
    if (isSpeaking && speakingChatId === chatId && speechRef.current) {
      speechSynth.cancel(); setIsSpeaking(false); setSpeakingChatId(null); speechRef.current = null;
    } else {
      if (speechRef.current) speechSynth.cancel();
      const utterance = new SpeechSynthesisUtterance(stripMarkdown(text));
      utterance.rate = 0.95; utterance.pitch = 1; utterance.volume = 1;
      utterance.onend = () => { setIsSpeaking(false); setSpeakingChatId(null); speechRef.current = null; };
      utterance.onerror = () => { setIsSpeaking(false); setSpeakingChatId(null); speechRef.current = null; };
      speechRef.current = utterance;
      speechSynth.speak(utterance); setIsSpeaking(true); setSpeakingChatId(chatId);
    }
  };

  const stopVoice = () => {
    if (speechSynth) { speechSynth.cancel(); setIsSpeaking(false); setSpeakingChatId(null); speechRef.current = null; }
  };

  useEffect(() => { return () => { if (speechSynth) speechSynth.cancel(); }; }, [speechSynth]);

  const buildSessionHistory = () => chatHistory
    .filter(chat => chat.response && !chat.isLoading)
    .map(chat => ({
      query_type: chat.queryType || 'Consultation', query: chat.query,
      response: chat.response, timestamp: new Date().toISOString(),
      has_image: chat.hasImage || false, has_pdf: chat.hasPdf || false, _session_only: true
    }));

  const fetchPatientHistory = async () => {
    try {
      const token = sessionStorage.getItem('authToken');
      const response = await axios.get(`${API_URL}/api/patient-history`, {
        params: { caseid: editableData.caseid, patid: editableData.patid },
        headers: { Authorization: `Bearer ${token}` }
      });
      setPatientHistory(response.data.success ? (response.data.history || []) : buildSessionHistory());
    } catch {
      setPatientHistory(buildSessionHistory());
    }
    setShowHistoryModal(true);
  };

  const fetchDemoCases = async () => {
    try {
      setIsDemoLoading(true);
      const response = await axios.post(`${API_URL}/api/demo-cases`, {
        caseid: editableData.caseid, patid: editableData.patid, pname: editableData.pname,
        age: parseInt(editableData.age) || 30, gender: editableData.gender,
        disease: editableData.disease || 'Unknown Condition', medication: editableData.medication || 'None',
        bp: editableData.bp || '120/80', pulse: editableData.pulse || '80',
        bmi: parseFloat(editableData.bmi) || 25, presenting_complaint: editableData.presenting_complaint || 'General checkup',
        family_history: editableData.family_history || 'None', social_history: editableData.social_history || 'None',
        allergies: editableData.allergies || 'None'
      });
      if (response.data.success) { setDemoCases(response.data.cases || []); setShowDemoModal(true); }
    } catch { alert('Failed to load demo cases.'); }
    finally { setIsDemoLoading(false); }
  };

  const runDemoCase = async (demoCase) => {
    try {
      setIsDemoLoading(true); setShowDemoModal(false);
      const response = await axios.post(`${API_URL}/api/demo-case/run`, {
        patient_data: {
          caseid: editableData.caseid, patid: editableData.patid, pname: editableData.pname,
          age: parseInt(editableData.age) || 30, gender: editableData.gender,
          disease: editableData.disease || 'Unknown', medication: editableData.medication || 'None',
          bp: editableData.bp || '120/80', pulse: editableData.pulse || '80',
          bmi: parseFloat(editableData.bmi) || 25,
          presenting_complaint: editableData.presenting_complaint || 'General checkup',
          family_history: editableData.family_history || 'None',
          social_history: editableData.social_history || 'None', allergies: editableData.allergies || 'None'
        },
        query_type: demoCase.query_type
      });
      if (response.data.success) await generateDemoPDF(response.data);
    } catch { alert('Failed to run demo case.'); }
    finally { setIsDemoLoading(false); }
  };

  const generateDemoPDF = async (demoData) => {
    try {
      const doc = new jsPDF();
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      doc.setFillColor(147, 51, 234);
      doc.rect(0, 0, pageWidth, 40, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(24); doc.setFont('helvetica', 'bold');
      doc.text('DiabAssist', 20, 18);
      doc.setFontSize(11); doc.setFont('helvetica', 'normal');
      doc.text('AI-Powered Clinical Decision Support', 20, 27);
      doc.setFontSize(10); doc.text('DEMO CASE STUDY REPORT', pageWidth / 2, 35, { align: 'center' });
      let yPos = 50;
      doc.setFillColor(147, 51, 234); doc.rect(14, yPos - 5, pageWidth - 28, 8, 'F');
      doc.setTextColor(255, 255, 255); doc.setFontSize(11); doc.setFont('helvetica', 'bold');
      doc.text('PATIENT INFORMATION', 20, yPos);
      yPos += 10; doc.setTextColor(0, 0, 0); doc.setFontSize(9); doc.setFont('helvetica', 'normal');
      autoTable(doc, {
        startY: yPos,
        body: [
          [`Name: ${demoData.patient_info?.name || 'N/A'}`, `Age: ${demoData.patient_info?.age || 'N/A'} years`],
          [`Gender: ${demoData.patient_info?.gender || 'N/A'}`, `Case ID: DEMO-${new Date().toISOString().split('T')[0]}`],
          [`Condition: ${demoData.patient_info?.condition || 'N/A'}`, `Analysis: ${demoData.query_type || 'N/A'}`]
        ],
        theme: 'plain', styles: { fontSize: 9, cellPadding: 1.5 },
        columnStyles: { 0: { cellWidth: 90 }, 1: { cellWidth: 90 } }, margin: { left: 20, right: 20 }
      });
      yPos = doc.lastAutoTable.finalY + 10;
      const aiText = demoData.ai_analysis || '';
      doc.setFillColor(147, 51, 234); doc.rect(14, yPos - 5, pageWidth - 28, 8, 'F');
      doc.setTextColor(255, 255, 255); doc.setFontSize(11); doc.setFont('helvetica', 'bold');
      doc.text('AI CLINICAL ANALYSIS', 20, yPos);
      yPos += 8; doc.setTextColor(0, 0, 0); doc.setFontSize(9); doc.setFont('helvetica', 'normal');
      aiText.split('\n').forEach(line => {
        if (yPos > pageHeight - 30) { doc.addPage(); yPos = 30; }
        const clean = line.replace(/\*\*/g, '').replace(/^[#\s*]+/g, '').trim();
        if (clean) {
          const split = doc.splitTextToSize(clean, pageWidth - 40);
          doc.text(split, 20, yPos); yPos += split.length * 5 + 2;
        } else { yPos += 4; }
      });
      doc.save(`Demo_${(demoData.patient_info?.name || 'Patient').replace(/\s+/g, '_')}_Report.pdf`);
    } catch { alert('Failed to generate PDF.'); }
  };

  const generatePDFReport = async () => {
    try {
      const historyData = buildSessionHistory();
      
      const doc = new jsPDF();
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      doc.setFillColor(88, 28, 135); doc.rect(0, 0, pageWidth, 40, 'F');
      doc.setTextColor(255, 255, 255); doc.setFontSize(22); doc.setFont('helvetica', 'bold');
      doc.text('DIABASSIST', pageWidth / 2, 15, { align: 'center' });
      doc.setFontSize(11); doc.setFont('helvetica', 'normal');
      doc.text('Advanced Clinical Decision Support System', pageWidth / 2, 23, { align: 'center' });
      doc.setFontSize(10); doc.text('Comprehensive Patient Clinical Report', pageWidth / 2, 30, { align: 'center' });
      let yPos = 45;
      doc.setFontSize(12); doc.setFont('helvetica', 'bold'); doc.setTextColor(88, 28, 135);
      doc.text('PATIENT INFORMATION', 20, yPos);
      autoTable(doc, {
        startY: yPos + 2,
        body: [
          [`Case ID: ${editableData.caseid || 'N/A'}`, `Patient ID: ${editableData.patid || 'N/A'}`],
          [`Name: ${editableData.pname || 'N/A'}`, `DOB: ${editableData.dob || 'N/A'}`],
          [`Age: ${editableData.age || 'N/A'} years`, `Gender: ${editableData.gender || 'N/A'}`]
        ],
        theme: 'plain', styles: { fontSize: 9, cellPadding: 1 },
        columnStyles: { 0: { cellWidth: 85 }, 1: { cellWidth: 85 } }, margin: { left: 20, right: 20 }
      });
      yPos = doc.lastAutoTable.finalY + 12;
      doc.setFontSize(12); doc.setFont('helvetica', 'bold'); doc.setTextColor(88, 28, 135);
      doc.text('CURRENT SESSION CONSULTATION SUMMARY', 20, yPos);
      yPos += 8;
      
      if (historyData.length === 0) {
        doc.setFontSize(10); doc.setFont('helvetica', 'italic'); doc.setTextColor(150, 150, 150);
        doc.text('No consultation history available in this session.', 20, yPos); yPos += 15;
      } else {
        let combinedSummary = historyData.map((c, i) => {
          const q = c.query ? c.query.trim() : 'No query';
          const r = c.response ? stripMarkdown(c.response).trim() : 'No response';
          return `Consultation ${i + 1} - Query: ${q} Analysis: ${r}`;
        }).join(' ');

        if (combinedSummary.length > 2500) {
          combinedSummary = combinedSummary.substring(0, 2497) + '...';
        }

        doc.setFontSize(10); 
        doc.setFont('helvetica', 'normal'); 
        doc.setTextColor(0, 0, 0);
        
        doc.text(combinedSummary, 20, yPos, { maxWidth: pageWidth - 40, align: 'justify' });
      }
      doc.setFontSize(8); doc.setTextColor(150, 150, 150);
      doc.text('Generated by DiabAssist', pageWidth / 2, pageHeight - 10, { align: 'center' });
      doc.save(`Patient_Report_${editableData.patid || 'Unknown'}_${new Date().toISOString().split('T')[0]}.pdf`);
      alert('PDF report generated successfully!');
    } catch (e) { alert('Failed to generate PDF: ' + e.message); }
  };

  const handleAsk = async () => {
    if (!editableData.disease && !editableData.presenting_complaint) {
      alert('Please fill at least Disease or Presenting Complaint');
      return;
    }
    setIsLoading(true);
    const userQueryText = query.trim() || `${selectedOption} analysis`;
    const newChatId = Date.now();

    const lowerQuery = userQueryText.toLowerCase();
    const asksAboutModel = lowerQuery.includes('what model') || lowerQuery.includes('which model') || lowerQuery.includes('what ai') || lowerQuery.includes('what llm');
    
    if (selectedOption === 'Generic' && asksAboutModel) {
      setChatHistory(prev => [...prev, {
        id: newChatId, query: userQueryText, queryType: selectedOption,
        response: '', timestamp: new Date().toLocaleTimeString(),
        hasImage: !!uploadedImage, hasPdf: !!uploadedPdfText, isLoading: false, isStreaming: true
      }]);
      
      const gemmaResponse = "I am using the Gemma model for our clinical generic conversation. How can I assist you further with this patient?";
      setAiResponse(gemmaResponse);
      setStreamingResponseId(newChatId);
      streamResponse(gemmaResponse, newChatId);
      setQuery('');
      setIsLoading(false);
      return;
    }

    setChatHistory(prev => [...prev, {
      id: newChatId, query: userQueryText, queryType: selectedOption,
      response: '', timestamp: new Date().toLocaleTimeString(),
      hasImage: !!uploadedImage, hasPdf: !!uploadedPdfText, isLoading: true, isStreaming: false
    }]);
    try {
      const token = sessionStorage.getItem('authToken');
      const response = await axios.post(`${API_URL}/api/clinical-analysis`, {
        caseid: editableData.caseid, patid: editableData.patid, pname: editableData.pname,
        dob: editableData.dob, age: parseInt(editableData.age), gender: editableData.gender,
        disease: editableData.disease, medication: editableData.medication,
        query_type: selectedOption, custom_query: query,
        presenting_complaint: editableData.presenting_complaint,
        bp: editableData.bp, pulse: editableData.pulse, bmi: editableData.bmi,
        family_history: editableData.family_history, social_history: editableData.social_history,
        allergies: editableData.allergies, image_data: uploadedImage,
        image_name: uploadedImageName, pdf_text: uploadedPdfText, pdf_name: uploadedPdfName,
        patient_email: editableData.patient_email || null,
        doctor_name: sessionStorage.getItem('doctorName') || 'Your Healthcare Provider'
      }, { headers: { Authorization: `Bearer ${token}` } });

      if (response.data.success) {
        const fullResponse = response.data.content;
        setAiResponse(fullResponse); setStreamingResponseId(newChatId);
        setChatHistory(prev => prev.map(chat =>
          chat.id === newChatId ? { ...chat, response: '', isLoading: false, isStreaming: true } : chat
        ));
        streamResponse(fullResponse, newChatId);
        setQuery('');
      } else {
        const errorMsg = 'Error: ' + (response.data.error || 'Unknown error');
        setChatHistory(prev => prev.map(chat =>
          chat.id === newChatId ? { ...chat, response: errorMsg, isLoading: false, isError: true, isStreaming: false } : chat
        ));
        setQuery('');
      }
    } catch (error) {
      const errorMsg = 'Error: ' + (error.response?.data?.detail || error.message || 'Failed to get AI response');
      setChatHistory(prev => prev.map(chat =>
        chat.id === newChatId ? { ...chat, response: errorMsg, isLoading: false, isError: true, isStreaming: false } : chat
      ));
      setQuery('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    const formData = new FormData(); formData.append('file', file);
    try {
      const response = await axios.post(`${API_URL}/api/upload-image`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (response.data.success) { setUploadedImage(response.data.image_data); setUploadedImageName(file.name); alert('Image uploaded! Click ASK AI to analyze.'); }
      else alert('Failed to upload image: ' + (response.data.error || 'Unknown error'));
    } catch (error) { alert('Failed to upload image: ' + (error.response?.data?.detail || error.message)); }
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    const formData = new FormData(); formData.append('file', file);
    try {
      const response = await axios.post(`${API_URL}/api/upload-pdf`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (response.data.success) {
        const extractedText = response.data.text || response.data.pdf_text || '';
        const wordCount = response.data.word_count || extractedText.length;
        setUploadedPdfText(extractedText); setUploadedPdfName(file.name);
        setPdfContent(extractedText); setShowPdfModal(true);
        alert(`PDF uploaded (${wordCount} words extracted)! Click ASK AI to analyze.`);
      } else alert('Failed to upload PDF: ' + (response.data.error || 'Unknown error'));
    } catch (error) { alert('Failed to upload PDF: ' + (error.response?.data?.detail || error.message)); }
  };

  const clearImage = () => { setUploadedImage(null); setUploadedImageName(''); };
  const clearPdf = () => { setUploadedPdfText(''); setUploadedPdfName(''); setPdfContent(''); setShowPdfModal(false); };

  const inputClass = "w-full px-3 py-2 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all text-gray-800 text-sm shadow-sm placeholder-gray-400";
  const labelClass = "block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1";

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <AppHeader />

      {/* Subtle background */}
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage: 'radial-gradient(circle at 10% 10%, rgba(168,85,247,0.05) 0%, transparent 40%), radial-gradient(circle at 90% 90%, rgba(20,184,166,0.04) 0%, transparent 40%)'
        }} />
      </div>

      {/* Top action bar */}
      <div className="relative z-10 bg-white border-b border-gray-100 px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
            <FiActivity className="text-purple-500" size={16} />
          </div>
          <div>
            <p className="font-bold text-gray-800 text-sm">Clinical Consultation</p>
            <p className="text-xs text-gray-400">AI-powered clinical decision support</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            onClick={onLogout}
            className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl text-xs font-semibold transition-colors"
          >
            <FiLogOut size={14} /> Logout
          </button>
          <span className="text-black text-[11px] font-bold tracking-wider">Doctor ID: {sessionStorage.getItem('doctorId') || 'DR1-4567-321'}</span>
        </div>
      </div>

      <div className="relative z-10 flex-1 p-4 max-w-[1800px] mx-auto w-full space-y-4">

        {/* Patient Information Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-50 flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-purple-50 flex items-center justify-center">
              <FiUser className="text-purple-500" size={15} />
            </div>
            <p className="font-semibold text-gray-800 text-sm">Patient Information</p>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
              {[
                { label: 'Patient ID', name: 'patid', placeholder: 'Patient ID' },
                { label: 'Case ID', name: 'caseid', placeholder: 'Case ID' },
                { label: 'Patient Name', name: 'pname', placeholder: 'Name' },
                { label: 'Age', name: 'age', type: 'number', placeholder: 'Age' },
                { label: 'Patient Email', name: 'patient_email', type: 'email', placeholder: 'Email' }
              ].map(field => (
                <div key={field.name}>
                  <label className={labelClass}>{field.label}</label>
                  <input
                    type={field.type || 'text'}
                    name={field.name}
                    value={editableData[field.name]}
                    onChange={handleChange}
                    placeholder={field.placeholder}
                    className={inputClass}
                  />
                </div>
              ))}
            </div>

            {/* Upload Buttons */}
            <div className="flex justify-center gap-3 pt-2 border-t border-gray-50">
              <label className="flex items-center gap-2 px-4 py-2 bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-xl cursor-pointer text-xs font-semibold transition-colors">
                <FiUpload size={13} /> Upload PDF Report
                <input type="file" onChange={handlePdfUpload} accept=".pdf" className="hidden" />
              </label>
              <label className="flex items-center gap-2 px-4 py-2 bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-xl cursor-pointer text-xs font-semibold transition-colors">
                <FiImage size={13} /> Upload Image
                <input type="file" onChange={handleImageUpload} accept="image/*" className="hidden" />
              </label>
            </div>
          </div>
        </div>

        {/* Query Input Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">

          {/* Uploaded files indicator */}
          {(uploadedImage || uploadedPdfText) && (
            <div className="mb-4 p-3 bg-purple-50 border border-purple-100 rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <FiCheck className="text-purple-500" size={13} />
                <span className="text-purple-700 font-semibold text-xs">Files Ready for Analysis</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {uploadedImage && (
                  <div className="flex items-center gap-2 bg-white border border-purple-200 rounded-lg px-3 py-1.5">
                    <FiImage className="text-purple-500" size={13} />
                    <span className="text-gray-700 text-xs font-medium truncate max-w-[120px]">{uploadedImageName}</span>
                    <button onClick={clearImage} className="text-gray-400 hover:text-red-500 transition-colors"><FiX size={12} /></button>
                  </div>
                )}
                {uploadedPdfText && (
                  <div className="flex items-center gap-2 bg-white border border-purple-200 rounded-lg px-3 py-1.5">
                    <FiFileText className="text-purple-500" size={13} />
                    <span className="text-gray-700 text-xs font-medium truncate max-w-[120px]">{uploadedPdfName}</span>
                    <button onClick={() => setShowPdfModal(true)} className="text-gray-400 hover:text-purple-500 transition-colors"><FiEye size={12} /></button>
                    <button onClick={clearPdf} className="text-gray-400 hover:text-red-500 transition-colors"><FiX size={12} /></button>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-4 gap-4">
            {/* Query textarea */}
            <div className="col-span-3">
              <label className={labelClass + ' flex items-center gap-1'}><FiFileText size={10} /> Clinical Query</label>
              <textarea
                ref={queryInputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="E.g., What do the lab results indicate? Or leave blank for comprehensive analysis based on selected type."
                className={inputClass + ' h-24 resize-none'}
              />
              <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                <FiAlertCircle size={10} /> AI will analyze with selected type, uploaded files, and patient data.
              </p>
            </div>

            {/* Controls */}
            <div className="space-y-2">
              <label className={labelClass}>Analysis Type</label>
              <select
                value={selectedOption}
                onChange={e => {
                  const val = e.target.value;
                  setSelectedOption(val);
                  switch(val) {
                    case 'Generic':
                      setQuery('Provide a generic consultation for ');
                      break;
                    case 'Explain':
                      setQuery('Explain the current condition of ');
                      break;
                    case 'Diagnosis':
                      setQuery('Provide a diagnosis and differential for ');
                      break;
                    case 'Treatment':
                      setQuery('Suggest a treatment plan for ');
                      break;
                    case 'Side Effects':
                      setQuery('Analyze the side effects of ');
                      break;
                    default:
                      break;
                  }
                  setTimeout(() => {
                    if (queryInputRef.current) {
                      queryInputRef.current.focus();
                      const len = queryInputRef.current.value.length;
                      queryInputRef.current.setSelectionRange(len, len);
                    }
                  }, 0);
                }}
                 className="w-full px-3 py-2.5 bg-gray-800 text-white rounded-xl font-semibold border border-gray-700 text-[10px] sm:text-xs cursor-pointer transition-all shadow-sm"
              >
                <option value="Generic">📝 Generic Conversation</option>
                <option value="Explain">📋 Explain Condition</option>
                <option value="Diagnosis">🔬 Diagnosis & Differential</option>
                <option value="Treatment">💊 Treatment Plan</option>
                <option value="Side Effects">⚠️ Side Effects Analysis</option>
              </select>

              <button
                onClick={handleAsk}
                disabled={isLoading}
                 className="w-full py-2.5 rounded-xl font-bold text-white text-[11px] sm:text-sm transition-all disabled:opacity-50 flex items-center justify-center gap-1.5 shadow-md"
                style={{ background: 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)' }}
              >
                {isLoading ? (
                  <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Processing...</>
                ) : (
                  <><FiActivity size={14} /> AI assistance</>
                )}
              </button>

              <button
                onClick={() => setEnableVoiceResponse(!enableVoiceResponse)}
                 className={`w-full py-2.5 rounded-xl font-semibold text-[10px] sm:text-xs transition-all flex items-center justify-center gap-1.5 border ${enableVoiceResponse ? 'bg-purple-500 text-white border-purple-500' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
              >
                {enableVoiceResponse ? <><FiMic size={12} /> Voice: ON</> : <><FiMicOff size={12} /> Voice Response</>}
              </button>
            </div>
          </div>
        </div>

        {/* AI Response Area */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center">
                <FiActivity className="text-emerald-500" size={15} />
              </div>
              <p className="font-semibold text-gray-800 text-sm">Conversation</p>
              {isLoading && (
                <div className="flex items-center gap-1.5 bg-purple-50 px-3 py-1 rounded-lg">
                  <div className="w-3 h-3 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-purple-600 text-xs font-semibold">Analyzing...</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              {isSpeaking && (
                <button onClick={stopVoice} className="flex items-center gap-1 bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors">
                  <FiMicOff size={12} /> Stop Voice
                </button>
              )}
              <span className="text-xs text-gray-400 bg-gray-50 px-3 py-1 rounded-lg">
                {chatHistory.length} conversation{chatHistory.length !== 1 ? 's' : ''}
              </span>
              {chatHistory.length > 0 && (
                <button onClick={() => setChatHistory([])} className="flex items-center gap-1 bg-red-50 hover:bg-red-100 text-red-500 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors">
                  <FiX size={12} /> Clear
                </button>
              )}
            </div>
          </div>

          {/* Chat area */}
          <div ref={chatContainerRef} className="p-5 min-h-[300px] max-h-[340px] overflow-y-auto relative bg-gray-50/30">
            {/* Watermark */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
              <img src="/myimage.png" alt="" className="min-w-[140%] min-h-[140%] object-cover opacity-[0.04]" />
            </div>

            <div className="relative z-10">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-48 space-y-3">
                  <div className="w-12 h-12 border-3 border-gray-200 border-t-purple-500 rounded-full animate-spin" />
                  <p className="text-gray-500 text-sm font-medium">AI is analyzing your query...</p>
                </div>
              ) : chatHistory.length > 0 ? (
                <div className="space-y-4">
                  {chatHistory.map((chat, idx) => (
                    <div key={chat.id} className="space-y-3">
                      {/* User message */}
                      <div className="flex items-start gap-3">
                        <div className="w-7 h-7 rounded-full bg-purple-500 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <FiUser className="text-white" size={12} />
                        </div>
                        <div className="flex-1 bg-purple-50 border border-purple-100 rounded-2xl rounded-tl-sm px-4 py-3">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-bold text-purple-600">You</span>
                            <span className="text-xs text-gray-400">• {chat.timestamp}</span>
                            <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full">{chat.queryType}</span>
                            {chat.hasImage && <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded-full">📷 Image</span>}
                            {chat.hasPdf && <span className="text-xs bg-teal-100 text-teal-600 px-2 py-0.5 rounded-full">📄 PDF</span>}
                          </div>
                          <p className="text-gray-700 text-sm">{chat.query}</p>
                        </div>
                      </div>

                      {/* AI message */}
                      <div className="flex items-start gap-3">
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${chat.isError ? 'bg-red-500' : 'bg-emerald-500'}`}>
                          {chat.isError ? <FiAlertCircle className="text-white" size={12} /> : <FiActivity className="text-white" size={12} />}
                        </div>
                        <div className={`flex-1 rounded-2xl rounded-tl-sm px-4 py-3 border ${chat.isError ? 'bg-red-50 border-red-100' : 'bg-white border-gray-100'} shadow-sm`}>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-bold ${chat.isError ? 'text-red-600' : 'text-emerald-600'}`}>
                                {chat.isError ? 'Error' : 'AI Assistant'}
                              </span>
                              <span className="text-xs text-gray-400">• {chat.timestamp}</span>
                              {chat.isStreaming && (
                                <span className="text-xs bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full flex items-center gap-1">
                                  <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
                                  Streaming...
                                </span>
                              )}
                            </div>
                            {!chat.isError && chat.response && !chat.isLoading && (
                              <button
                                onClick={() => toggleSpeech(chat.response, chat.id)}
                                className={`p-1.5 rounded-lg transition-all ${isSpeaking && speakingChatId === chat.id ? 'bg-emerald-500 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-500'}`}
                                title={isSpeaking && speakingChatId === chat.id ? 'Stop' : 'Read aloud'}
                              >
                                {isSpeaking && speakingChatId === chat.id ? <FiMicOff size={12} /> : <FiMic size={12} />}
                              </button>
                            )}
                          </div>
                          {chat.isLoading ? (
                            <div className="flex items-center gap-2 py-2">
                              <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                              <span className="text-gray-500 text-sm">AI is thinking...</span>
                            </div>
                          ) : (
                            <ChatResponseContent response={chat.response} isError={chat.isError} />
                          )}
                        </div>
                      </div>

                      {idx < chatHistory.length - 1 && <div className="border-t border-dashed border-gray-200 my-2" />}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-center">
                  <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center mb-3">
                    <FiActivity className="text-gray-300" size={28} />
                  </div>
                  <p className="font-semibold text-gray-600 mb-1">Ready for Analysis</p>
                  <p className="text-gray-400 text-sm">Upload reports or images, then click ASK AI</p>
                </div>
              )}
            </div>
          </div>

          <div className="px-5 py-2 border-t border-gray-50 bg-amber-50/50">
            <p className="text-xs text-amber-600">💡 Each query is saved in conversation history. Scroll up to view previous analyses.</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
          {[
            { icon: <FiPlus size={14} />, label: 'Next Patient', onClick: onBack, color: 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200' },
            { icon: <FiClock size={14} />, label: 'History', onClick: fetchPatientHistory, color: 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200' },
            { icon: <FiDownload size={14} />, label: 'Export Report', onClick: generatePDFReport, color: 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200' }
          ].map((btn, i) => (
            <button key={i} onClick={btn.onClick} className={`flex items-center justify-center gap-1 sm:gap-2 py-2 sm:py-3 rounded-xl font-semibold text-xs sm:text-sm transition-colors border shadow-sm ${btn.color}`}>
              {btn.icon} {btn.label}
            </button>
          ))}
        </div>

        {/* Ad */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-3">
          <a href="#" className="block group" onClick={e => { e.preventDefault(); alert('EI Health Solutions'); }}>
            <div className="flex items-center gap-3">
              <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded font-medium flex-shrink-0">Ad</span>
              <div className="w-16 h-7 rounded overflow-hidden flex-shrink-0">
                <img src="/edited-photo.png" alt="EI Logo" className="w-full h-full object-cover" onError={e => e.target.style.display = 'none'} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-purple-600 group-hover:text-purple-800 truncate">EI Health Solutions</p>
                <p className="text-xs text-gray-400 truncate">Advanced Medical Technology for Modern Healthcare</p>
              </div>
              <span className="text-xs text-gray-400 group-hover:text-gray-600 flex-shrink-0">Learn More →</span>
            </div>
          </a>
        </div>

      </div>

      {/* PDF Modal */}
      <AnimatePresence>
        {showPdfModal && pdfContent && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowPdfModal(false)}>
            <motion.div initial={{ scale: 0.95, y: 16 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95 }} className="bg-white rounded-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
              <div className="px-6 py-4 flex items-center justify-between border-b border-gray-100">
                <p className="font-bold text-gray-800 flex items-center gap-2"><FiFileText className="text-purple-500" /> {uploadedPdfName}</p>
                <button onClick={() => setShowPdfModal(false)} className="text-gray-400 hover:text-gray-600"><FiX size={20} /></button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[65vh] bg-gray-50">
                <pre className="whitespace-pre-wrap text-gray-700 text-sm font-sans leading-relaxed">{pdfContent}</pre>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* History Modal */}
      <AnimatePresence>
        {showHistoryModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowHistoryModal(false)}>
            <motion.div initial={{ scale: 0.95, y: 16 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95 }} className="bg-white rounded-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
              <div className="px-6 py-4 flex items-center justify-between border-b border-gray-100">
                <p className="font-bold text-gray-800 flex items-center gap-2"><FiClock className="text-purple-500" /> Patient Consultation History</p>
                <button onClick={() => setShowHistoryModal(false)} className="text-gray-400 hover:text-gray-600"><FiX size={20} /></button>
              </div>
              {patientHistory.length > 0 && patientHistory[0]?._session_only && (
                <div className="bg-amber-50 border-b border-amber-100 px-6 py-2 flex items-center gap-2">
                  <FiAlertCircle className="text-amber-500" size={14} />
                  <p className="text-amber-700 text-xs">Showing current session history only.</p>
                </div>
              )}
              <div className="p-6 overflow-y-auto max-h-[65vh] bg-gray-50 space-y-3">
                {patientHistory.length > 0 ? patientHistory.map((h, idx) => (
                  <div key={idx} className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-bold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">{h.query_type || 'Consultation'}</span>
                      <span className="text-xs text-gray-400">{new Date(h.timestamp).toLocaleString()}</span>
                    </div>
                    <p className="text-xs font-bold text-gray-500 mb-1">Query:</p>
                    <p className="text-sm text-gray-700 mb-3">{h.query || 'No query'}</p>
                    <p className="text-xs font-bold text-gray-500 mb-1">AI Response:</p>
                    <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg max-h-40 overflow-auto whitespace-pre-wrap">{h.response || 'No response'}</div>
                  </div>
                )) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <FiClock className="text-gray-300 mb-3" size={32} />
                    <p className="font-semibold text-gray-500">No History Found</p>
                    <p className="text-sm text-gray-400">No previous consultations for this patient.</p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Demo Modal */}
      <AnimatePresence>
        {showDemoModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowDemoModal(false)}>
            <motion.div initial={{ scale: 0.95, y: 16 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95 }} className="bg-white rounded-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
              <div className="px-6 py-4 flex items-center justify-between border-b border-gray-100">
                <p className="font-bold text-gray-800 flex items-center gap-2"><FiActivity className="text-purple-500" /> Demo Analysis — {editableData.pname || 'Current Patient'}</p>
                <button onClick={() => setShowDemoModal(false)} className="text-gray-400 hover:text-gray-600"><FiX size={20} /></button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[65vh]">
                {demoCases.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {demoCases.map(dc => (
                      <div key={dc.id} onClick={() => runDemoCase(dc)} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md hover:border-purple-300 transition-all cursor-pointer group">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 font-bold text-lg group-hover:bg-purple-500 group-hover:text-white transition-colors">{dc.id}</div>
                          <h4 className="font-bold text-gray-800 text-sm">{dc.title}</h4>
                        </div>
                        <p className="text-sm text-gray-500 mb-3">{dc.description}</p>
                        <span className="text-xs bg-purple-50 text-purple-600 px-2 py-1 rounded-full">{dc.query_type}</span>
                        <button className="w-full mt-4 py-2.5 rounded-xl text-sm font-semibold transition-all text-white shadow-sm" style={{ background: 'linear-gradient(135deg, #a855f7, #ec4899)' }}>
                          Run This Analysis
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <FiActivity className="text-gray-300 mb-3" size={32} />
                    <p className="font-semibold text-gray-500">Loading Demo Cases...</p>
                  </div>
                )}
              </div>
              <div className="px-6 py-3 border-t border-gray-100 bg-purple-50">
                <p className="text-xs text-purple-600">💡 Select an analysis type to see how AI evaluates this patient from different clinical perspectives.</p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default IntelliHealthInterface;