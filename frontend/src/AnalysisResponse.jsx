// AnalysisResponse.jsx
// Purpose: Present structured AI analysis results to clinicians in a
// concise, graded format (risk, decision, interactions, rationale).
// Notes:
// - This is a pure presentation component; data should be validated
//   before being passed in (e.g., risk_score fields).
import React from 'react';
import { motion } from 'framer-motion';
import {
 FiCheckCircle,
 FiAlertTriangle,
 FiXCircle,
 FiInfo,
 FiUsers,
 FiBarChart2,
 FiShare2,
 FiPill,
 FiActivity,
 FiShield,
 FiDownload
} from 'react-icons/fi';

const AnalysisResponse = ({ analysis, onDownloadPDF }) => {
 if (!analysis) return null;

 const {
 final_decision,
 risk_level,
 risk_score,
 explanation,
 drug_interactions,
 possible_reactions,
 knowledge_graph,
 medications,
 ai_confidence,
 ai_commentary,
 } = analysis;

 // CLINICAL SCORING SYSTEM - Doctor-Level Prescription Accuracy
 // 🏆 GOLD STANDARD (85-100): Best-in-class, first-line medication
 // ✅ EXCELLENT (70-84): Appropriate, well-established medication
 // ✓ GOOD (55-69): Works but not ideal (second-line, off-label)
 // ⚠️ ACCEPTABLE (40-54): Needs monitoring, suboptimal choice
 // 🚨 CONCERNING (25-39): Wrong drug or significant concerns
 // ❌ UNSAFE (0-24): Harmful, contraindicated, or dangerous
 const getRiskColorScheme = () => {
 const score = risk_score?.score || 0;
 if (score >= 85) {
 return {
 primary: 'bg-emerald-500',
 light: 'bg-emerald-50',
 text: 'text-emerald-800',
 border: 'border-emerald-300',
 bg: 'bg-emerald-50',
 };
 } else if (score >= 70) {
 return {
 primary: 'bg-green-500',
 light: 'bg-green-50',
 text: 'text-green-800',
 border: 'border-green-300',
 bg: 'bg-green-50',
 };
 } else if (score >= 55) {
 return {
 primary: 'bg-teal-500',
 light: 'bg-teal-50',
 text: 'text-teal-800',
 border: 'border-teal-300',
 bg: 'bg-teal-50',
 };
 } else if (score >= 40) {
 return {
 primary: 'bg-orange-500',
 light: 'bg-amber-50',
 text: 'text-orange-800',
 border: 'border-amber-300',
 bg: 'bg-amber-50',
 };
 } else if (score >= 25) {
 return {
 primary: 'bg-red-500',
 light: 'bg-orange-50',
 text: 'text-red-800',
 border: 'border-orange-300',
 bg: 'bg-orange-50',
 };
 } else {
 return {
 primary: 'bg-red-600',
 light: 'bg-red-50',
 text: 'text-red-900',
 border: 'border-red-300',
 bg: 'bg-red-50',
 };
 }
 };

 const colorScheme = getRiskColorScheme();

 const getDecisionConfig = () => {
 switch (final_decision) {
 case 'SAFE':
 return {
 icon: FiCheckCircle,
 title: 'Safe to Proceed',
 subtitle: 'Prescription analysis completed successfully',
 ...colorScheme,
 };
 case 'CAUTION':
 return {
 icon: FiAlertTriangle,
 title: 'Caution Advised',
 subtitle: 'Review potential interactions before proceeding',
 ...colorScheme,
 };
 case 'UNSAFE':
 return {
 icon: FiXCircle,
 title: 'Unsafe - Review Required',
 subtitle: 'Critical issues detected in prescription',
 ...colorScheme,
 };
 default:
 return {
 icon: FiInfo,
 title: 'Analysis Complete',
 subtitle: 'Review the findings below',
 ...colorScheme,
 };
 }
 };

 const decisionConfig = getDecisionConfig();
 const DecisionIcon = decisionConfig.icon;

 const cardVariants = {
 hidden: { opacity: 0, y: 20 },
 visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
 };

 const Section = ({ title, icon: Icon, iconColor, children, delay = 0 }) => (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay, duration: 0.4 }}
 className="mt-6"
 >
 <div className="flex items-center mb-3">
 <div className={`w-8 h-8 rounded-lg ${iconColor} flex items-center justify-center mr-3`}>
 <Icon className="text-white" size={18} />
 </div>
 <h3 className="text-base font-semibold text-gray-800">{title}</h3>
 </div>
 <div className="ml-11">{children}</div>
 </motion.div>
 );

 return (
 <motion.div
 variants={cardVariants}
 initial="hidden"
 animate="visible"
 className={`w-full max-w-4xl rounded-2xl shadow-lg border overflow-hidden ${colorScheme.bg}`}
 >
 {/* Header */}
 <div className={`${decisionConfig.primary} p-6 text-white relative overflow-hidden`}>
 {/* Background Pattern */}
 <div className="absolute inset-0 opacity-10">
 <div className="absolute top-0 right-0 w-32 h-32 bg-white rounded-full blur-3xl"></div>
 <div className="absolute bottom-0 left-0 w-24 h-24 bg-white rounded-full blur-2xl"></div>
 </div>

 <div className="relative z-10">
 <div className="flex items-start justify-between mb-4">
 <div className="flex items-center gap-4">
 <motion.div
 initial={{ scale: 0, rotate: -180 }}
 animate={{ scale: 1, rotate: 0 }}
 transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
 className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center"
 >
 <DecisionIcon size={32} />
 </motion.div>
 <div>
 <h2 className="text-2xl font-bold">{decisionConfig.title}</h2>
 <p className="text-sm opacity-90">{decisionConfig.subtitle}</p>
 </div>
 </div>

 <div className="flex flex-col items-end gap-2">
 <motion.span
 initial={{ opacity: 0, scale: 0.8 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ delay: 0.3 }}
 className="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-full text-sm font-semibold"
 >
 <FiShield className="inline mr-2" />
 Risk: {risk_level}
 </motion.span>
 {risk_score && (
 <motion.span
 initial={{ opacity: 0, scale: 0.8 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ delay: 0.4 }}
 className="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-full text-sm font-semibold"
 >
 <FiActivity className="inline mr-2" />
 Score: {risk_score.score}/100
 </motion.span>
 )}
 </div>
 </div>

 {/* Risk Progress Bar */}
 <div className="mt-4 bg-white/20 backdrop-blur-sm rounded-full h-2 overflow-hidden">
 <motion.div
 initial={{ width: 0 }}
 animate={{ width: `${risk_score?.score || 0}%` }}
 transition={{ delay: 0.5, duration: 1, ease: 'easeOut' }}
 className="h-full bg-white rounded-full"
 />
 </div>

 {/* AI Confidence Badge */}
 {ai_confidence && (
 <motion.div
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.6 }}
 className="mt-4 flex items-center justify-between bg-white/20 backdrop-blur-sm rounded-lg p-3"
 >
 <div className="flex items-center gap-2">
 <FiShield className="text-white" size={16} />
 <span className="text-sm font-medium text-white">AI Confidence Assessment:</span>
 </div>
 <div className="flex items-center gap-2">
 <div className="w-32 h-2 rounded-full bg-white/30">
 <div 
 className="h-full bg-white rounded-full" 
 style={{ width: `${ai_confidence.confidence_score}%` }}
 />
 </div>
 <span className="text-sm font-bold text-white whitespace-nowrap">
 {ai_confidence.confidence_score}%
 </span>
 </div>
 </motion.div>
 )}
 </div>
 </div>

 {/* Content */}
 <div className="p-6 bg-white">
 {/* AI Commentary Section */}
 {ai_commentary && (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.7 }}
 className="mb-6 bg-purple-50 border-l-4 border-purple-500 rounded-lg p-4"
 >
 <div className="flex items-start gap-3">
 <div className="w-8 h-8 rounded-lg bg-purple-500 flex items-center justify-center flex-shrink-0">
 <FiInfo className="text-white" size={16} />
 </div>
 <div>
 <p className="text-xs font-semibold text-purple-600 uppercase mb-1">Clinical Summary</p>
 <p className="text-gray-700 text-sm leading-relaxed">{ai_commentary}</p>
 </div>
 </div>
 </motion.div>
 )}

 {/* Patient Info Cards */}
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
 <motion.div
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 0.6 }}
 className="bg-teal-50 rounded-xl p-4 border border-teal-200"
 >
 <div className="flex items-center gap-2 mb-2">
 <FiInfo className="text-purple-500" size={18} />
 <span className="text-xs font-semibold text-gray-500 uppercase">Condition</span>
 </div>
 <p className="font-semibold text-gray-900">
 {knowledge_graph?.disease?.name || medications?.[0] || 'N/A'}
 </p>
 </motion.div>

 <motion.div
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 0.7 }}
 className="bg-teal-50 rounded-xl p-4 border border-teal-200"
 >
 <div className="flex items-center gap-2 mb-2">
 <FiPill className="text-purple-500" size={18} />
 <span className="text-xs font-semibold text-gray-500 uppercase">Medications</span>
 </div>
 <p className="font-semibold text-gray-900">{medications?.join(', ') || 'N/A'}</p>
 </motion.div>
 </div>

 {/* AI Analysis */}
 {explanation && (
 <Section title="AI Clinical Analysis" icon={FiInfo} iconColor="bg-purple-500" delay={0.8}>
 <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
 <p className="text-gray-700 leading-relaxed">{explanation}</p>
 </div>
 </Section>
 )}

 {/* Drug Interactions */}
 {drug_interactions && drug_interactions.length > 0 && (
 <Section title="Drug Interactions" icon={FiAlertTriangle} iconColor="bg-red-500" delay={0.9}>
 <div className="space-y-3">
 {drug_interactions.map((interaction, index) => (
 <motion.div
 key={index}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 1 + index * 0.1 }}
 className="bg-red-50 border border-red-200 rounded-xl p-4"
 >
 <div className="flex items-center gap-2 mb-2">
 <FiAlertTriangle className="text-red-500" size={16} />
 <p className="font-semibold text-red-800">
 {interaction.drug1} + {interaction.drug2}
 <span className="ml-2 px-2 py-0.5 bg-red-200 text-red-700 rounded-full text-xs font-medium">
 {interaction.severity}
 </span>
 </p>
 </div>
 <p className="text-sm text-red-700 ml-6">{interaction.description}</p>
 </motion.div>
 ))}
 </div>
 </Section>
 )}

 {/* Possible Reactions */}
 {possible_reactions && possible_reactions.length > 0 && (
 <Section title="Potential Adverse Reactions" icon={FiUsers} iconColor="bg-purple-500" delay={1}>
 <div className="flex flex-wrap gap-2">
 {possible_reactions.map((reaction, index) => (
 <motion.span
 key={index}
 initial={{ opacity: 0, scale: 0.8 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ delay: 1.1 + index * 0.05 }}
 className="px-3 py-1.5 bg-purple-100 text-purple-800 rounded-full text-sm font-medium border border-purple-200"
 >
 {reaction}
 </motion.span>
 ))}
 </div>
 </Section>
 )}

 {/* Risk Score Display */}
 {risk_score && (
 <Section title="Personalized Risk Score" icon={FiBarChart2} iconColor="bg-indigo-500" delay={1.1}>
 <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5">
 <div className="flex items-center gap-4">
 <div className={`w-20 h-20 rounded-full ${colorScheme.light} flex items-center justify-center border-4 ${colorScheme.border}`}>
 <span className={`text-3xl font-bold ${colorScheme.text}`}>{risk_score.score}</span>
 </div>
 <div>
 <p className="text-lg font-bold text-indigo-800">Risk Category: {risk_score.level}</p>
 <p className="text-sm text-gray-600">Based on patient profile and medication analysis</p>
 </div>
 </div>
 </div>
 </Section>
 )}

 {/* Knowledge Graph Preview */}
 {knowledge_graph && (knowledge_graph.disease || knowledge_graph.medications?.length > 0) && (
 <Section title="Medical Knowledge Graph" icon={FiShare2} iconColor="bg-teal-500" delay={1.2}>
 <div className="bg-teal-50 border border-teal-200 rounded-xl p-4">
 <div className="flex items-center justify-between mb-3">
 <p className="text-sm text-gray-600">
 Disease-symptom-medication relationships visualization
 </p>
 <span className="text-xs text-teal-600 font-medium">
 {knowledge_graph.nodes?.length || 0} nodes, {knowledge_graph.edges?.length || 0} connections
 </span>
 </div>
 <div className="bg-white rounded-lg p-4 border border-teal-100">
 <p className="text-sm text-gray-500 text-center">
 Interactive graph visualization available - click "View Graph" to explore relationships
 </p>
 </div>
 </div>
 </Section>
 )}

 {/* Footer Actions */}
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 transition={{ delay: 1.3 }}
 className="mt-6 pt-6 border-t border-gray-200 flex justify-end"
 >
 {onDownloadPDF && (
 <button
 onClick={() => onDownloadPDF(analysis)}
 className="flex items-center gap-2 px-6 py-3 bg-purple-400 text-white rounded-xl font-medium shadow-md hover:shadow-lg transition-all"
 >
 <FiDownload size={18} />
 Download PDF Report
 </button>
 )}
 </motion.div>
 </div>
 </motion.div>
 );
};

export default AnalysisResponse;
