// Message.js
// Purpose: Renders individual chat messages and AI analysis cards.
// Notes:
// - Interprets `analysisData` to show risk/decision visuals for doctors.
// - Keep heavy data processing server-side; this component focuses on
//   presenting structured data cleanly and accessibly.
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FaRobot, FaUser, FaCheckCircle, FaExclamationTriangle, FaTimesCircle, FaPills, FaNotesMedical, FaFlask, FaShieldAlt, FaInfoCircle, FaStethoscope, FaClipboardCheck, FaImage, FaHeartbeat, FaArrowRight, FaStar } from 'react-icons/fa';
import { FiDownload, FiCheck, FiX, FiAlertCircle, FiShield, FiActivity, FiMessageSquare, FiShare2 } from 'react-icons/fi';
import KnowledgeGraph from './KnowledgeGraph';

const Message = ({ message, onDownloadPDF }) => {
  const role = message?.role || 'assistant';
  const hasPdf = message?.hasPdf || false;
  const analysisData = message?.analysisData || null;
  const content = message?.content;
  const isContentObject = typeof content === 'object' && content !== null && !Array.isArray(content);
  const [showGraph, setShowGraph] = useState(false);

  const variants = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: "easeOut" } },
  };

  // Enhanced card styles based on risk score (Prescription Accuracy/Safety)
  const getCardStyle = () => {
    const riskScore = analysisData?.risk_score?.score || 0;

    // CLINICAL SCORING SYSTEM - Doctor-Level Prescription Accuracy
    // 🏆 GOLD STANDARD (85-100): Best-in-class, first-line medication
    // ✅ EXCELLENT (70-84): Appropriate, well-established medication
    // ✓ GOOD (55-69): Works but not ideal (second-line, off-label)
    // ⚠️ ACCEPTABLE (40-54): Needs monitoring, suboptimal choice
    // 🚨 CONCERNING (25-39): Wrong drug or significant concerns
    // ❌ UNSAFE (0-24): Harmful, contraindicated, or dangerous
    const getScoreBasedStyle = () => {
      if (riskScore >= 85) {
        // GOLD STANDARD - Best-in-class prescription
        return {
          bg: 'bg-gradient-to-br from-emerald-50 via-green-50 to-teal-50',
          border: 'border-emerald-600',
          header: 'bg-gradient-to-r from-emerald-600 via-green-600 to-teal-600',
          headerGlow: 'shadow-emerald-500/50',
          text: 'text-emerald-900',
          icon: 'text-emerald-700',
          badge: 'bg-gradient-to-r from-emerald-200 to-green-200 text-emerald-900',
          accent: 'from-emerald-600 to-teal-600',
          ring: 'ring-emerald-500',
          scoreLabel: '🏆 GOLD STANDARD - Best-in-Class Prescription',
          scoreColor: 'text-emerald-700',
        };
      } else if (riskScore >= 70) {
        // EXCELLENT - Appropriate, well-established
        return {
          bg: 'bg-gradient-to-br from-green-50 via-lime-50 to-emerald-50',
          border: 'border-green-500',
          header: 'bg-gradient-to-r from-green-500 via-lime-500 to-emerald-500',
          headerGlow: 'shadow-green-500/50',
          text: 'text-green-900',
          icon: 'text-green-700',
          badge: 'bg-gradient-to-r from-green-200 to-lime-200 text-green-900',
          accent: 'from-green-500 to-emerald-500',
          ring: 'ring-green-400',
          scoreLabel: '✅ EXCELLENT - Appropriate Prescription',
          scoreColor: 'text-green-700',
        };
      } else if (riskScore >= 55) {
        // GOOD - Works but not ideal
        return {
          bg: 'bg-gradient-to-br from-teal-50 via-teal-50 to-teal-50',
          border: 'border-teal-500',
          header: 'bg-gradient-to-r from-teal-500 via-teal-500 to-teal-500',
          headerGlow: 'shadow-teal-500/50',
          text: 'text-teal-900',
          icon: 'text-teal-700',
          badge: 'bg-gradient-to-r from-teal-200 to-teal-200 text-teal-900',
          accent: 'from-teal-500 to-teal-500',
          ring: 'ring-teal-400',
          scoreLabel: '✓ GOOD - Works But Not First-Line',
          scoreColor: 'text-teal-700',
        };
      } else if (riskScore >= 40) {
        // ACCEPTABLE - Needs monitoring
        return {
          bg: 'bg-gradient-to-br from-teal-50 via-teal-50 to-teal-50',
          border: 'border-teal-500',
          header: 'bg-gradient-to-r from-teal-500 via-teal-500 to-teal-500',
          headerGlow: 'shadow-teal-500/50',
          text: 'text-teal-900',
          icon: 'text-teal-700',
          badge: 'bg-gradient-to-r from-teal-200 to-teal-200 text-teal-900',
          accent: 'from-teal-500 to-teal-500',
          ring: 'ring-teal-400',
          scoreLabel: '⚠️ ACCEPTABLE - Monitor Closely',
          scoreColor: 'text-teal-700',
        };
      } else if (riskScore >= 25) {
        // CONCERNING - Wrong drug or significant concerns
        return {
          bg: 'bg-gradient-to-br from-orange-50 via-red-50 to-rose-50',
          border: 'border-orange-600',
          header: 'bg-gradient-to-r from-orange-600 via-red-500 to-rose-500',
          headerGlow: 'shadow-orange-500/50',
          text: 'text-red-900',
          icon: 'text-red-700',
          badge: 'bg-gradient-to-r from-orange-200 to-red-200 text-red-900',
          accent: 'from-orange-600 to-red-600',
          ring: 'ring-orange-500',
          scoreLabel: '🚨 CONCERNING - Review Required',
          scoreColor: 'text-red-700',
        };
      } else {
        // UNSAFE - Harmful or dangerous
        return {
          bg: 'bg-gradient-to-br from-red-600 via-rose-600 to-pink-600',
          border: 'border-rose-700',
          header: 'bg-gradient-to-r from-red-700 via-rose-700 to-pink-700',
          headerGlow: 'shadow-red-600/50',
          text: 'text-white',
          icon: 'text-white',
          badge: 'bg-gradient-to-r from-red-300 to-rose-300 text-red-900',
          accent: 'from-red-700 to-pink-700',
          ring: 'ring-red-600',
          scoreLabel: '❌ UNSAFE - Do Not Prescribe',
          scoreColor: 'text-rose-800',
        };
      }
    };

    if (!analysisData) return {
      bg: 'bg-gradient-to-br from-slate-50 via-gray-50 to-zinc-50',
      border: 'border-gray-300',
      header: 'bg-gradient-to-r from-slate-600 via-gray-600 to-zinc-600',
      headerGlow: 'shadow-gray-500/50',
      text: 'text-gray-800',
      icon: 'text-gray-600',
      badge: 'bg-gradient-to-r from-gray-200 to-slate-200 text-gray-800',
      accent: 'from-slate-500 to-gray-600',
      ring: 'ring-gray-400',
      scoreLabel: 'Analysis Complete',
      scoreColor: 'text-gray-700',
    };

    // Use risk score based styling for prescription accuracy feedback
    return getScoreBasedStyle();
  };

  const cardStyle = getCardStyle();

  // User message with enhanced styling
  if (role === 'user') {
    return (
      <motion.div variants={variants} initial="hidden" animate="visible" className="flex justify-end mb-4">
        <div className="flex items-center gap-3 max-w-2xl">
          <div className="bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 text-white p-4 rounded-2xl shadow-lg border border-purple-300/30 backdrop-blur-sm">
            <p className="text-sm leading-relaxed">{content}</p>
          </div>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center shadow-lg"
          >
            <FaUser className="text-white" />
          </motion.div>
        </div>
      </motion.div>
    );
  }

  const isAnalysisResponse = !!(analysisData && analysisData.final_decision);

  const getDecisionInfo = () => {
    if (!analysisData) return { icon: FaCheckCircle, text: 'Response', color: 'text-gray-600', gradient: 'from-gray-500 to-gray-600' };

    switch(analysisData.final_decision) {
      case 'SAFE': return { icon: FaCheckCircle, text: 'SAFE TO PROCEED', color: 'text-emerald-600', gradient: 'from-emerald-500 to-teal-500' };
      case 'CAUTION': return { icon: FaExclamationTriangle, text: 'CAUTION ADVISED', color: 'text-amber-600', gradient: 'from-amber-500 to-orange-500' };
      case 'UNSAFE': return { icon: FaTimesCircle, text: 'UNSAFE - REVIEW REQUIRED', color: 'text-red-600', gradient: 'from-red-500 to-pink-500' };
      default: return { icon: FaCheckCircle, text: 'Response', color: 'text-gray-600', gradient: 'from-gray-500 to-gray-600' };
    }
  };

  const decisionInfo = getDecisionInfo();
  const DecisionIcon = decisionInfo.icon;

  // Analysis response card - takes priority over other assistant messages
  if (isAnalysisResponse) {
    return (
      <motion.div variants={variants} initial="hidden" animate="visible" className="flex justify-start mb-6">
        <div className="flex items-start gap-4 max-w-6xl w-full">
          {/* Avatar */}
          <motion.div 
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
            className={`w-14 h-14 rounded-2xl ${cardStyle.header} flex items-center justify-center shadow-lg ${cardStyle.headerGlow}`}
          >
            <FaRobot className="text-white text-3xl" />
          </motion.div>

          {/* Main Card */}
          <div className={`flex-1 rounded-3xl shadow-2xl border-2 ${cardStyle.border} ${cardStyle.bg} overflow-hidden backdrop-blur-sm ring-4 ${cardStyle.ring}/20`}>
            {/* Header Section */}
            <div className={`${cardStyle.header} p-6 text-white relative overflow-hidden`}>
              {/* Background Pattern */}
              <div className="absolute inset-0 opacity-10">
                <div className="absolute top-0 right-0 w-32 h-32 bg-white rounded-full blur-3xl"></div>
                <div className="absolute bottom-0 left-0 w-24 h-24 bg-white rounded-full blur-2xl"></div>
              </div>
              
              <div className="relative z-10">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2, type: "spring" }}
                      className={`w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center`}
                    >
                      <DecisionIcon className="text-3xl" />
                    </motion.div>
                    <div>
                      <motion.h3 
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                        className="text-3xl font-bold tracking-tight"
                      >
                        {decisionInfo.text}
                      </motion.h3>
                      <p className="text-sm opacity-90 font-medium">Prescription Analysis Result</p>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap items-center gap-3">
                    <motion.span
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.4 }}
                      className={`px-5 py-2.5 rounded-full font-bold text-sm ${cardStyle.badge} shadow-lg backdrop-blur-sm`}
                    >
                      <FiShield className="inline mr-2" />
                      Risk: {analysisData.risk_level}
                    </motion.span>
                    {analysisData.risk_score && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.5 }}
                        className={`px-5 py-2.5 rounded-full font-bold text-sm ${cardStyle.badge} shadow-lg backdrop-blur-sm`}
                      >
                        <FiActivity className="inline mr-2" />
                        Accuracy: {analysisData.risk_score.score}/100
                      </motion.span>
                    )}
                    {analysisData.risk_score?.safety_category && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.6 }}
                        className={`px-5 py-2.5 rounded-full font-bold text-xs ${cardStyle.badge} shadow-lg backdrop-blur-sm hidden md:inline-flex`}
                      >
                        <FaCheckCircle className="inline mr-1" />
                        {analysisData.risk_score.safety_category}
                      </motion.span>
                    )}
                  </div>
                </div>

                {/* Risk Level Indicator Bar */}
                <div className="mt-4 bg-white/20 backdrop-blur-sm rounded-full h-3 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: analysisData.risk_score ? `${analysisData.risk_score.score}%` : '0%' }}
                    transition={{ delay: 0.6, duration: 1, ease: "easeOut" }}
                    className={`h-full bg-gradient-to-r ${decisionInfo.gradient} rounded-full`}
                  />
                </div>
              </div>
            </div>

            {/* Content Section */}
            <div className="p-6 space-y-5">
              {/* Patient Info Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                  className="bg-white/70 backdrop-blur-md rounded-2xl p-4 border border-white/50 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cardStyle.accent} flex items-center justify-center shadow-md`}>
                      <FaNotesMedical className="text-white text-lg" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wider opacity-70">Condition</span>
                  </div>
                  <p className={`font-bold text-lg ${cardStyle.text}`}>
                    {analysisData.knowledge_graph?.disease?.name || analysisData.medications?.[0] || 'N/A'}
                  </p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 }}
                  className="bg-white/70 backdrop-blur-md rounded-2xl p-4 border border-white/50 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cardStyle.accent} flex items-center justify-center shadow-md`}>
                      <FaPills className="text-white text-lg" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wider opacity-70">Medications</span>
                  </div>
                  <p className={`font-bold text-lg ${cardStyle.text}`}>{analysisData.medications?.join(', ') || 'N/A'}</p>
                </motion.div>

                {/* Per-Medication Verification Status */}
                {analysisData.verification_details && analysisData.verification_details.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.85 }}
                    className="bg-white/70 backdrop-blur-md rounded-2xl p-4 border border-white/50 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cardStyle.accent} flex items-center justify-center shadow-md`}>
                        <FaClipboardCheck className="text-white text-lg" />
                      </div>
                      <span className="text-xs font-bold uppercase tracking-wider opacity-70">Medication Verification</span>
                    </div>
                    <div className="space-y-3">
                      {analysisData.verification_details.map((detail, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.9 + idx * 0.05 }}
                          className={`flex items-center justify-between p-3 rounded-xl border-l-4 ${
                            detail.status === 'SAFE'
                              ? 'bg-emerald-50 border-emerald-500'
                              : detail.status === 'WARNING'
                              ? 'bg-amber-50 border-amber-500'
                              : 'bg-red-50 border-red-500'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                              detail.status === 'SAFE'
                                ? 'bg-emerald-500'
                                : detail.status === 'WARNING'
                                ? 'bg-amber-500'
                                : 'bg-red-500'
                            }`}>
                              {detail.status === 'SAFE' ? (
                                <FiCheck className="text-white text-sm" />
                              ) : detail.status === 'WARNING' ? (
                                <FiAlertCircle className="text-white text-sm" />
                              ) : (
                                <FiX className="text-white text-sm" />
                              )}
                            </div>
                            <div>
                              <span className="font-semibold text-gray-800">{detail.medication}</span>
                              {detail.error && (
                                <p className="text-xs text-red-600 mt-1">{detail.error}</p>
                              )}
                            </div>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                            detail.status === 'SAFE'
                              ? 'bg-emerald-200 text-emerald-800'
                              : detail.status === 'WARNING'
                              ? 'bg-amber-200 text-amber-800'
                              : 'bg-red-200 text-red-800'
                          }`}>
                            {detail.status}
                          </span>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Symptoms Card */}
              {analysisData.knowledge_graph?.disease?.symptoms && analysisData.knowledge_graph.disease.symptoms.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.9 }}
                  className="bg-white/70 backdrop-blur-md rounded-2xl p-4 border border-white/50 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cardStyle.accent} flex items-center justify-center shadow-md`}>
                      <FaClipboardCheck className="text-white text-lg" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wider opacity-70">Common Symptoms</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {analysisData.knowledge_graph.disease.symptoms.map((symptom, idx) => (
                      <motion.span
                        key={idx}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 1.0 + idx * 0.05 }}
                        className="px-3 py-1.5 bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 rounded-full text-sm font-semibold shadow-sm border border-blue-200"
                      >
                        {symptom}
                      </motion.span>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* AI Analysis */}
              {analysisData.explanation && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.9 }}
                  className={`rounded-2xl p-5 shadow-lg border-2 ${
                    analysisData.final_decision === 'UNSAFE' || analysisData.final_decision === 'CAUTION'
                      ? 'bg-gradient-to-br from-red-50 via-rose-50 to-pink-50 border-red-300'
                      : 'bg-white/70 backdrop-blur-md border-white/50'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${
                      analysisData.final_decision === 'UNSAFE' || analysisData.final_decision === 'CAUTION'
                        ? 'from-red-500 to-rose-500'
                        : cardStyle.accent
                    } flex items-center justify-center shadow-md`}>
                      <FaFlask className="text-white text-lg" />
                    </div>
                    <span className={`text-sm font-bold uppercase tracking-wider ${
                      analysisData.final_decision === 'UNSAFE' || analysisData.final_decision === 'CAUTION'
                        ? 'text-red-800'
                        : 'opacity-70'
                    }`}>AI Clinical Analysis</span>
                  </div>
                  
                  {/* Parse and display structured analysis */}
                  <div className="space-y-3">
                    {analysisData.explanation.includes('**GOOD FOR:**') ? (
                      <>
                        <div className="bg-gradient-to-br from-emerald-50 to-green-50 border-l-4 border-emerald-500 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <FaCheckCircle className="text-emerald-600 text-sm" />
                            <span className="font-bold text-emerald-800 text-sm">GOOD FOR</span>
                          </div>
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {analysisData.explanation.split('**GOOD FOR:**')[1]?.split('**NOT GOOD FOR:**')[0]?.trim() || 
                             analysisData.explanation.split('**GOOD FOR:**')[1]?.split('**OVERALL')[0]?.trim()}
                          </p>
                        </div>
                        
                        <div className="bg-gradient-to-br from-red-50 to-rose-50 border-l-4 border-red-500 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <FaTimesCircle className="text-red-600 text-sm" />
                            <span className="font-bold text-red-800 text-sm">NOT GOOD FOR</span>
                          </div>
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {analysisData.explanation.split('**NOT GOOD FOR:**')[1]?.split('**OVERALL')[0]?.trim() ||
                             analysisData.explanation.split('**NOT GOOD FOR:**')[1]?.split('**ASSESSMENT:**')[0]?.trim()}
                          </p>
                        </div>
                        
                        <div className={`bg-gradient-to-br rounded-lg p-4 border-2 ${
                          analysisData.final_decision === 'SAFE'
                            ? 'from-emerald-50 to-green-50 border-emerald-300'
                            : analysisData.final_decision === 'CAUTION'
                            ? 'from-amber-50 to-orange-50 border-amber-300'
                            : 'from-red-50 to-rose-50 border-red-300'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            <FaClipboardCheck className={`text-lg ${
                              analysisData.final_decision === 'SAFE' ? 'text-emerald-600' :
                              analysisData.final_decision === 'CAUTION' ? 'text-amber-600' : 'text-red-600'
                            }`} />
                            <span className={`font-bold text-sm ${
                              analysisData.final_decision === 'SAFE' ? 'text-emerald-800' :
                              analysisData.final_decision === 'CAUTION' ? 'text-amber-800' : 'text-red-800'
                            }`}>OVERALL ASSESSMENT</span>
                          </div>
                          <p className={`text-sm leading-relaxed ${
                            analysisData.final_decision === 'SAFE' ? 'text-emerald-900' :
                            analysisData.final_decision === 'CAUTION' ? 'text-amber-900' : 'text-red-900'
                          }`}>
                            {analysisData.explanation.split('**OVERALL ASSESSMENT:**')[1]?.trim() ||
                             analysisData.explanation.split('**OVERALL')[1]?.trim()}
                          </p>
                        </div>
                      </>
                    ) : (
                      <p className={`text-sm leading-relaxed ${
                        analysisData.final_decision === 'UNSAFE' || analysisData.final_decision === 'CAUTION'
                          ? 'text-red-900 font-medium'
                          : cardStyle.text
                      }`}>{analysisData.explanation}</p>
                    )}
                  </div>
                </motion.div>
              )}

              {/* Alternative Medications Suggestion */}
              {(analysisData.final_decision === 'CAUTION' || analysisData.final_decision === 'UNSAFE') && 
               analysisData.knowledge_graph?.alternative_medications && analysisData.knowledge_graph?.alternative_medications.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.1 }}
                  className="bg-gradient-to-br from-emerald-50 via-green-50 to-lime-50 border-2 border-emerald-300 rounded-2xl p-5 shadow-xl"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-green-500 flex items-center justify-center shadow-lg">
                      <FaArrowRight className="text-white text-xl" />
                    </div>
                    <div>
                      <span className="text-base font-bold text-emerald-800 uppercase tracking-wide">
                        Suggested Alternative Medications
                      </span>
                      <p className="text-xs text-emerald-700 mt-0.5">
                        Consider discussing these with your healthcare provider
                      </p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {analysisData.knowledge_graph.alternative_medications.map((alt_med, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 1.2 + idx * 0.1 }}
                          className="flex items-center justify-between gap-3 px-4 py-3 bg-white/80 backdrop-blur-sm rounded-xl border border-emerald-200 shadow-sm"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-green-400 flex items-center justify-center">
                              <FaCheckCircle className="text-white text-sm" />
                            </div>
                            <span className="font-semibold text-gray-800">{alt_med.name}</span>
                          </div>
                          <div className="flex items-center gap-1 text-xs text-emerald-700 font-bold">
                            {[...Array(5)].map((_, i) => (
                                <FaStar key={i} className={i < alt_med.suggestion_score ? 'text-teal-400' : 'text-gray-300'} />
                            ))}
                          </div>
                        </motion.div>
                      ))}
                  </div>
                  <p className="text-xs text-emerald-600 mt-4 italic">
                    ⚠️ Always consult with a healthcare professional before changing medications
                  </p>
                </motion.div>
              )}

              {/* Risk Factors Breakdown */}
              {analysisData.risk_score?.factors && analysisData.risk_score.factors.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.15 }}
                  className={`rounded-2xl p-5 shadow-lg border-2 ${
                    analysisData.risk_score.score >= 70
                      ? 'bg-gradient-to-br from-emerald-50 to-green-50 border-emerald-300'
                      : analysisData.risk_score.score >= 55
                      ? 'bg-gradient-to-br from-amber-50 to-orange-50 border-amber-300'
                      : 'bg-gradient-to-br from-red-50 to-rose-50 border-red-300'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-md ${
                      analysisData.risk_score.score >= 70
                        ? 'bg-gradient-to-br from-emerald-500 to-green-500'
                        : analysisData.risk_score.score >= 55
                        ? 'bg-gradient-to-br from-amber-500 to-orange-500'
                        : 'bg-gradient-to-br from-red-500 to-rose-500'
                    }`}>
                      <FaClipboardCheck className="text-white text-xl" />
                    </div>
                    <div>
                      <span className={`text-sm font-bold uppercase tracking-wide ${
                        analysisData.risk_score.score >= 70
                          ? 'text-emerald-800'
                          : analysisData.risk_score.score >= 55
                          ? 'text-amber-800'
                          : 'text-red-800'
                      }`}>
                        Clinical Scoring Analysis
                      </span>
                      <p className={`text-xs ${
                        analysisData.risk_score.score >= 70
                          ? 'text-emerald-700'
                          : analysisData.risk_score.score >= 55
                          ? 'text-amber-700'
                          : 'text-red-700'
                      }`}>
                        {analysisData.risk_score.factors.length} clinical factors considered
                      </p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {analysisData.risk_score.factors.map((factor, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 1.2 + idx * 0.05 }}
                        className={`flex items-start gap-2 p-2 rounded-lg ${
                          factor.includes('⚠️')
                            ? 'bg-red-100 border-l-3 border-red-500'
                            : factor.toLowerCase().includes('safe') || factor.toLowerCase().includes('appropriate') || factor.toLowerCase().includes('no high-risk')
                            ? 'bg-emerald-100 border-l-3 border-emerald-500'
                            : 'bg-white/70 border-l-3 border-gray-300'
                        }`}
                      >
                        <span className="text-xs mt-0.5">
                          {factor.includes('⚠️') ? '⚠️' : factor.toLowerCase().includes('safe') || factor.toLowerCase().includes('appropriate') || factor.toLowerCase().includes('no high-risk') ? '✓' : '•'}
                        </span>
                        <span className="text-sm text-gray-700">{factor}</span>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Risk Score Breakdown Details */}
              {analysisData.risk_score?.breakdown && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.18 }}
                  className="bg-gradient-to-br from-slate-50 to-gray-50 border-2 border-slate-300 rounded-2xl p-4 shadow-lg"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-slate-500 to-gray-500 flex items-center justify-center shadow-md">
                      <FiActivity className="text-white text-sm" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Score Components</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(analysisData.risk_score.breakdown).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center bg-white/70 rounded-lg px-3 py-2">
                        <span className="text-slate-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                        <span className="font-bold text-slate-800">{value}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Side Effects */}
              {analysisData.possible_reactions && analysisData.possible_reactions.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.2 }}
                  className="bg-white/70 backdrop-blur-md rounded-2xl p-5 border border-white/50 shadow-lg"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cardStyle.accent} flex items-center justify-center shadow-md`}>
                      <FaShieldAlt className="text-white text-lg" />
                    </div>
                    <span className="text-sm font-bold uppercase tracking-wider opacity-70">Possible Side Effects</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {analysisData.possible_reactions.slice(0, 8).map((reaction, idx) => (
                      <motion.span
                        key={idx}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 1.3 + idx * 0.05 }}
                        className={`px-4 py-2 rounded-full text-xs font-bold ${cardStyle.badge} shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5 cursor-default`}
                      >
                        {reaction}
                      </motion.span>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Knowledge Graph Visualization */}
              {analysisData.knowledge_graph && (analysisData.knowledge_graph.disease || analysisData.knowledge_graph.medications?.length > 0) && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 1.3 }}
                  className="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 border-2 border-purple-300 rounded-2xl p-5 shadow-xl"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg">
                        <FiShare2 className="text-white text-2xl" />
                      </div>
                      <div>
                        <span className="text-base font-bold text-purple-800 uppercase tracking-wide">
                          Medical Knowledge Graph
                        </span>
                        <p className="text-xs text-purple-600 mt-0.5">
                          Visualize disease-symptom-medication relationships
                        </p>
                      </div>
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => setShowGraph(true)}
                      className="px-5 py-2.5 bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white rounded-xl shadow-lg font-bold text-sm transition-all"
                    >
                      View Graph
                    </motion.button>
                  </div>
                  {/* Mini Graph Preview */}
                  <div className="bg-white/70 backdrop-blur-sm rounded-xl p-4 border border-purple-200">
                    <div className="flex items-center justify-center gap-8 py-6">
                      {/* Disease Node */}
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 1.5, type: "spring" }}
                        className="text-center"
                      >
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg mx-auto mb-2">
                          <FaNotesMedical className="text-white text-2xl" />
                        </div>
                        <p className="text-xs font-bold text-purple-700">
                          {analysisData.knowledge_graph.disease?.name || analysisData.medications?.[0] || 'Disease'}
                        </p>
                      </motion.div>
                      {/* Arrows */}
                      <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 1.6 }}
                        className="flex flex-col items-center gap-1"
                      >
                        <div className="w-16 h-1 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full"></div>
                        <span className="text-xs text-purple-600 font-medium">treated by</span>
                      </motion.div>
                      {/* Medication Nodes */}
                      <div className="flex gap-3">
                        {analysisData.knowledge_graph.medications?.slice(0, 3).map((med, idx) => (
                          <motion.div
                            key={idx}
                            initial={{ scale: 0, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            transition={{ delay: 1.7 + idx * 0.1, type: "spring" }}
                            className="text-center"
                          >
                            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center shadow-lg mx-auto mb-2">
                              <FaPills className="text-white text-xl" />
                            </div>
                            <p className="text-xs font-bold text-pink-700 max-w-[80px] truncate">
                              {med.name || 'Medication'}
                            </p>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-center gap-4 mt-4">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                        <span className="text-xs text-gray-600">Disease</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-pink-500"></div>
                        <span className="text-xs text-gray-600">Medication</span>
                      </div>
                      {analysisData.knowledge_graph.disease?.symptoms && (
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                          <span className="text-xs text-gray-600">
                            {analysisData.knowledge_graph.disease.symptoms.length} Symptoms
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Footer */}
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.4 }}
                className="flex items-center justify-between pt-4 border-t border-gray-300/50"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg ${analysisData.verification_status === 'SAFE' ? 'bg-gradient-to-br from-green-500 to-emerald-500' : 'bg-gradient-to-br from-teal-500 to-teal-500'} flex items-center justify-center shadow-md`}>
                    {analysisData.verification_status === 'SAFE' ? (
                      <FiCheck className="text-white text-lg" />
                    ) : (
                      <FiX className="text-white text-lg" />
                    )}
                  </div>
                  <span className="text-sm font-bold text-gray-700">Database Verification: <span className={analysisData.verification_status === 'SAFE' ? 'text-green-600' : 'text-teal-600'}>{analysisData.verification_status}</span></span>
                </div>

                {hasPdf && analysisData && (
                  <motion.button
                    whileHover={{ scale: 1.05, rotate: -1 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => onDownloadPDF && onDownloadPDF(analysisData)}
                    className="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-red-500 via-pink-500 to-rose-500 hover:from-red-600 hover:via-pink-600 hover:to-rose-600 text-white rounded-xl shadow-xl hover:shadow-2xl transition-all font-bold text-sm"
                  >
                    <FiDownload size={18} />
                    Download PDF Report
                  </motion.button>
                )}
              </motion.div>
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  // Render Knowledge Graph Modal
  if (showGraph && analysisData?.knowledge_graph && (analysisData.knowledge_graph.disease || analysisData.knowledge_graph.medications?.length > 0)) {
    return <KnowledgeGraph graphData={analysisData.knowledge_graph} onClose={() => setShowGraph(false)} />;
  }

  // Render JSON response in a structured, stylish format
  const renderJSONResponse = (data) => {
    const renderValue = (value, key) => {
      if (Array.isArray(value)) {
        return (
          <div className="flex flex-wrap gap-2 mt-2">
            {value.map((item, idx) => (
              <motion.span
                key={idx}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.05 }}
                className="px-3 py-1.5 bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 rounded-full text-sm font-semibold shadow-sm border border-blue-200"
              >
                {String(item)}
              </motion.span>
            ))}
          </div>
        );
      }
      if (typeof value === 'object' && value !== null) {
        return (
          <div className="mt-2 bg-white/50 backdrop-blur-sm rounded-xl p-3 border border-gray-200">
            {Object.entries(value).map(([k, v], idx) => (
              <div key={idx} className="flex gap-2 py-1 border-b border-gray-100 last:border-b-0">
                <span className="font-semibold text-gray-600 capitalize min-w-[120px]">{k}:</span>
                <span className="text-gray-800">{renderValue(v, k)}</span>
              </div>
            ))}
          </div>
        );
      }
      if (typeof value === 'boolean') {
        return (
          <span className={`px-2 py-1 rounded-md text-xs font-bold ${value ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
            {value ? '✓ Yes' : '✗ No'}
          </span>
        );
      }
      return <span className="text-gray-800">{String(value)}</span>;
    };

    const formatKey = (key) => {
      return key
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, (str) => str.toUpperCase());
    };

    return (
      <div className="space-y-4">
        {Object.entries(data).map(([key, value], index) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className="bg-white/70 backdrop-blur-md rounded-2xl p-4 border border-white/50 shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-md">
                <FaHeartbeat className="text-white text-sm" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-gray-600">{formatKey(key)}</span>
            </div>
            <div className="ml-11">
              {renderValue(value, key)}
            </div>
          </motion.div>
        ))}
      </div>
    );
  };

  // Render structured AI medical response (disease prediction, etc.)
  const renderAIResponse = (data) => {
    return (
      <div className="space-y-4">
        {/* Header Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white/70 backdrop-blur-md rounded-2xl p-4 border border-white/50 shadow-lg"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shadow-md">
                <FaStethoscope className="text-white text-lg" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider opacity-70">Disease</span>
            </div>
            <p className="font-bold text-lg text-gray-800 capitalize">{data.disease || 'N/A'}</p>
          </motion.div>
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white/70 backdrop-blur-md rounded-2xl p-4 border border-white/50 shadow-lg"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className={`w-10 h-10 rounded-xl ${data.is_correct_medication ? 'bg-gradient-to-br from-emerald-500 to-green-500' : 'bg-gradient-to-br from-amber-500 to-orange-500'} flex items-center justify-center shadow-md`}>
                <FaCheckCircle className="text-white text-lg" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider opacity-70">Medication</span>
            </div>
            <p className={`font-bold text-lg ${data.is_correct_medication ? 'text-emerald-700' : 'text-amber-700'}`}>
              {data.is_correct_medication ? '✓ Correct Prescription' : '⚠ Review Needed'}
            </p>
          </motion.div>
        </div>

        {/* Recommended Medications */}
        {data.recommended_medications && data.recommended_medications.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 border-2 border-blue-300 rounded-2xl p-5 shadow-xl"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-lg">
                <FaPills className="text-white text-xl" />
              </div>
              <span className="text-sm font-bold text-blue-800 uppercase tracking-wide">Recommended Medications</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {data.recommended_medications.map((med, idx) => (
                <motion.span
                  key={idx}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: idx * 0.05 }}
                  className="px-4 py-2 bg-white rounded-full text-sm font-bold text-blue-700 shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
                >
                  {med}
                </motion.span>
              ))}
            </div>
          </motion.div>
        )}

        {/* Alerts */}
        {data.alerts && data.alerts.length > 0 ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gradient-to-r from-red-50 via-teal-50 to-teal-50 border-2 border-red-300 rounded-2xl p-5 shadow-xl"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center shadow-lg">
                <FiAlertCircle className="text-white text-2xl" />
              </div>
              <span className="text-sm font-bold text-red-800 uppercase tracking-wide">
                Alerts ({data.alerts.length})
              </span>
            </div>
            <div className="space-y-2">
              {data.alerts.map((alert, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className="flex items-start gap-3 bg-white/70 backdrop-blur-sm rounded-xl p-3 border-l-4 border-red-500"
                >
                  <span className="text-red-600 mt-1 text-lg">●</span>
                  <p className="text-gray-800 text-sm leading-relaxed">{alert}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gradient-to-br from-emerald-50 to-green-50 border-2 border-emerald-300 rounded-2xl p-4 shadow-lg"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-green-500 flex items-center justify-center shadow-md">
                <FaCheckCircle className="text-white text-lg" />
              </div>
              <span className="text-sm font-bold text-emerald-800">No critical alerts detected</span>
            </div>
          </motion.div>
        )}

        {/* Agent Advice */}
        {data.agent_advice && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/70 backdrop-blur-md rounded-2xl p-5 border-2 border-purple-200 shadow-lg"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shadow-md">
                <FaInfoCircle className="text-white text-lg" />
              </div>
              <span className="text-sm font-bold uppercase tracking-wider opacity-70">Clinical Advice</span>
            </div>
            <p className="text-sm text-gray-800 leading-relaxed">{data.agent_advice}</p>
          </motion.div>
        )}
      </div>
    );
  };

  // Enhanced error message with structured display
  const renderErrorMessage = (content) => {
    // Check if content is an object with structured error data
    if (typeof content === 'object' && content !== null && !Array.isArray(content)) {
      const { type, message, errors, error_id } = content;
      
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-rose-500 flex items-center justify-center shadow-md">
              <FiAlertCircle className="text-white text-lg" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-red-800">
                {type === 'validation_error' ? 'Input Validation Error' : 
                 type === 'processing_error' ? 'Processing Error' : 'Error'}
              </h3>
              {error_id && <p className="text-xs text-red-600">Error ID: {error_id}</p>}
            </div>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-800 font-medium mb-2">{message}</p>
            
            {errors && Array.isArray(errors) && errors.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-red-700 font-semibold">Details:</p>
                <ul className="space-y-1">
                  {errors.map((error, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-red-700">
                      <span className="text-red-500 mt-1">•</span>
                      <span>{error}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <h4 className="text-blue-800 font-semibold mb-2">💡 Suggestions:</h4>
            <ul className="space-y-1 text-sm text-blue-700">
              <li>• Check that all required fields are filled</li>
              <li>• Ensure medication names are spelled correctly</li>
              <li>• Verify age and gender information is accurate</li>
              <li>• Try again in a few moments</li>
            </ul>
          </div>
        </div>
      );
    }
    
    // Fallback for string errors
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-rose-500 flex items-center justify-center shadow-md">
            <FiAlertCircle className="text-white text-lg" />
          </div>
          <h3 className="text-lg font-bold text-red-800">Error</h3>
        </div>
        
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-800">{content}</p>
        </div>
      </div>
    );
  };

  // Format markdown for text content
  const formatMarkdown = (text) => {
    if (!text) return '';
    return text
      .replace(/## (.*?)\n/g, '<h3 class="text-xl font-bold mb-2 mt-4 text-gray-800">$1</h3>')
      .replace(/### (.*?)\n/g, '<h4 class="text-lg font-semibold mb-1 mt-3 text-gray-700">$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-gray-900">$1</strong>')
      .replace(/\*(.*?)\*/g, '<em class="text-gray-600">$1</em>')
      .replace(/^\*\s+(.*?)$/gm, '<li class="ml-4 text-gray-700">$1</li>')
      .replace(/^•\s+(.*?)$/gm, '<li class="ml-4 text-gray-700">$1</li>')
      .replace(/\n\n/g, '</p><p class="mb-3">')
      .replace(/\n/g, '<br/>');
  };

  // For assistant messages with structured disease content or other JSON responses
  if (role === 'assistant' && isContentObject && (content.disease || content.alerts || content.recommended_medications)) {
    return (
      <motion.div variants={variants} initial="hidden" animate="visible" className="flex justify-start mb-4">
        <div className="flex items-start gap-4 max-w-5xl w-full">
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-400 via-pink-400 to-indigo-400 flex items-center justify-center shadow-xl"
          >
            <FaRobot className="text-white text-3xl" />
          </motion.div>
          <div className="flex-1 bg-white text-gray-800 p-6 rounded-3xl shadow-2xl border-2 border-purple-200 backdrop-blur-sm">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg">
                <FaClipboardCheck className="text-white text-xl" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800">AI Medical Analysis</h3>
            </div>
            {renderAIResponse(content)}
          </div>
        </div>
      </motion.div>
    );
  }

  // For assistant messages with other JSON/object content (generic structured display)
  if (role === 'assistant' && isContentObject) {
    return (
      <motion.div variants={variants} initial="hidden" animate="visible" className="flex justify-start mb-4">
        <div className="flex items-start gap-4 max-w-5xl w-full">
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-400 via-blue-400 to-indigo-400 flex items-center justify-center shadow-xl"
          >
            <FaRobot className="text-white text-3xl" />
          </motion.div>
          <div className="flex-1 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 text-gray-800 p-6 rounded-3xl shadow-2xl border-2 border-blue-200 backdrop-blur-sm">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg">
                <FaHeartbeat className="text-white text-xl" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800">Analysis Result</h3>
            </div>
            {renderJSONResponse(content)}
          </div>
        </div>
      </motion.div>
    );
  }

  // Enhanced simple text response (error messages, info messages, etc.)
  const isErrorMessage = (content && typeof content === 'string' && (content.includes('❌') || content.includes('Error') || content.includes('failed'))) || 
                      (content && typeof content === 'object' && content.type && (content.type.includes('error') || content.type === 'validation_error' || content.type === 'processing_error'));
  const isInfoMessage = content && typeof content === 'string' && (content.includes('📸') || content.includes('Image') || content.includes('🔍') || content.includes('Prediction'));
  const isGenericMessage = content && typeof content === 'string' && (content.includes('✅') || content.includes('Success') || content.includes('completed'));

  const responseCardStyle = isErrorMessage
    ? { bg: 'from-red-50 via-rose-50 to-pink-50', border: 'border-red-300', accent: 'from-red-500 to-rose-500', icon: 'from-red-500 to-rose-500', text: 'text-red-900', header: 'Error' }
    : isInfoMessage
    ? { bg: 'from-blue-50 via-indigo-50 to-purple-50', border: 'border-blue-300', accent: 'from-blue-500 to-indigo-500', icon: 'from-blue-500 to-indigo-500', text: 'text-blue-900', header: content.includes('🔍') ? 'Disease Prediction' : 'Image Analysis' }
    : isGenericMessage
    ? { bg: 'from-emerald-50 via-green-50 to-teal-50', border: 'border-emerald-300', accent: 'from-emerald-500 to-teal-500', icon: 'from-emerald-500 to-teal-500', text: 'text-emerald-900', header: 'Success' }
    : { bg: 'from-slate-50 via-gray-50 to-zinc-50', border: 'border-gray-300', accent: 'from-slate-500 to-gray-600', icon: 'from-slate-500 to-gray-600', text: 'text-gray-900', header: 'Message' };

  return (
    <motion.div variants={variants} initial="hidden" animate="visible" className="flex justify-start mb-4">
      <div className="flex items-start gap-4 max-w-5xl w-full">
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${isErrorMessage ? 'from-red-400 to-rose-400' : isInfoMessage ? 'from-blue-400 via-purple-400 to-indigo-400' : isGenericMessage ? 'from-emerald-400 to-teal-400' : 'from-slate-400 via-gray-400 to-zinc-400'} flex items-center justify-center shadow-xl`}
        >
          {isErrorMessage ? (
            <FiAlertCircle className="text-white text-3xl" />
          ) : isInfoMessage ? (
            <FaClipboardCheck className="text-white text-3xl" />
          ) : isGenericMessage ? (
            <FaCheckCircle className="text-white text-3xl" />
          ) : (
            <FaRobot className="text-white text-3xl" />
          )}
        </motion.div>
        <div className={`flex-1 bg-gradient-to-br ${responseCardStyle.bg} text-gray-800 p-6 rounded-3xl shadow-2xl border-2 ${responseCardStyle.border} backdrop-blur-sm ring-4 ring-opacity-20 ${responseCardStyle.border.replace('border-', 'ring-')}`}>
          {/* Header with icon */}
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${responseCardStyle.accent} flex items-center justify-center shadow-lg`}>
              {isErrorMessage ? (
                <FiAlertCircle className="text-white text-lg" />
              ) : isInfoMessage ? (
                content.includes('📸') || content.includes('Image') ? (
                  <FaImage className="text-white text-lg" />
                ) : (
                  <FaStethoscope className="text-white text-lg" />
                )
              ) : isGenericMessage ? (
                <FaCheckCircle className="text-white text-lg" />
              ) : (
                <FiMessageSquare className="text-white text-lg" />
              )}
            </div>
            <h3 className={`text-xl font-bold ${responseCardStyle.text}`}>
              {responseCardStyle.header}
            </h3>
          </div>
          {/* Content */}
          <div className={`prose prose-sm max-w-none ${responseCardStyle.text}`}>
            {content ? (
              isErrorMessage ? (
                renderErrorMessage(content)
              ) : typeof content === 'string' ? (
                <div
                  className="text-sm leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: `<p class="mb-3">${formatMarkdown(content)}</p>` }}
                />
              ) : (
                <div className="text-sm leading-relaxed">
                  {renderJSONResponse(content)}
                </div>
              )
            ) : (
              <p className="text-gray-500 italic">No content</p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default Message;
