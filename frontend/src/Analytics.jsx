// Analytics.jsx
// Purpose: Visual dashboard for patient-level analytics and trends.
// Notes:
// - Fetches aggregated AI analysis history for a patient and renders
//   charts using Recharts. Keep heavy aggregation server-side for
//   performance and pass precomputed series to this component.
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
 LineChart,
 Line,
 AreaChart,
 Area,
 XAxis,
 YAxis,
 CartesianGrid,
 Tooltip,
 Legend,
 ResponsiveContainer,
 PieChart,
 Pie,
 Cell,
 BarChart,
 Bar,
 RadarChart,
 PolarGrid,
 PolarAngleAxis,
 PolarRadiusAxis,
 Radar
} from 'recharts';
import {
 FiActivity, FiCalendar, FiTrendingUp, FiDatabase, FiAlertCircle, FiX, FiUser, FiMail, FiShield,
 FiClock, FiCheckCircle, FiAlertTriangle, FiXCircle, FiPieChart, FiTarget, FiHeart, FiZap,
 FiDroplet, FiAward
} from 'react-icons/fi';
import axios from 'axios';
import { API_URL } from './apiConfig';


const Analytics = ({ patientName, patientEmail }) => {
 const [timeRange, setTimeRange] = useState('1month');
 const [analyticsData, setAnalyticsData] = useState(null);
 const [dashboardData, setDashboardData] = useState(null);
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState(null);
 const [showDoctorAlert, setShowDoctorAlert] = useState(false);
 const [selectedMetric, setSelectedMetric] = useState('overview');

 const timeRangeOptions = [
 { value: '24h', label: '24H' },
 { value: '1month', label: '1 Month' },
 { value: '1year', label: '1 Year' },
 ];

 useEffect(() => {
 if (patientName && patientName.trim()) {
 fetchData(timeRange);
 } else {
 setAnalyticsData(null);
 setDashboardData(null);
 }
 }, [timeRange, patientName]);

 useEffect(() => {
 if (analyticsData?.summary?.decisionDistribution?.UNSAFE > 0 ||
 analyticsData?.summary?.overallRiskLevel === 'CRITICAL' ||
 analyticsData?.summary?.overallRiskLevel === 'HIGH') {
 setShowDoctorAlert(true);
 } else {
 setShowDoctorAlert(false);
 }
 }, [analyticsData]);

 // Generate health score trend data
 const generateHealthScoreData = () => {
 if (!analyticsData?.trendData) return [];
 return analyticsData.trendData.map(point => ({
 ...point,
 healthScore: Math.round(100 - ((point.medications || 0) * 5 + (point.diseases || 0) * 10))
 }));
 };

 // Generate medication trend data - track top medications over time
 const generateMedicationTrendData = () => {
 if (!analyticsData?.trendData || !analyticsData?.topMedications) return [];
 const topMeds = analyticsData.topMedications.slice(0, 5).map(m => m.medication);
 
 return analyticsData.trendData.map(point => {
 const medicationData = { timestamp: point.timestamp };
 topMeds.forEach(med => {
 medicationData[med] = point.medication_names?.filter(m => m === med).length || 0;
 });
 medicationData.total = point.medications || 0;
 return medicationData;
 });
 };

 // Generate disease trend data - track top diseases over time
 const generateDiseaseTrendData = () => {
 if (!analyticsData?.trendData || !analyticsData?.topDiseases) return [];
 const topDiseases = analyticsData.topDiseases.slice(0, 5).map(d => d.disease);
 
 return analyticsData.trendData.map(point => {
 const diseaseData = { timestamp: point.timestamp };
 topDiseases.forEach(disease => {
 diseaseData[disease] = point.disease_names?.filter(d => d === disease).length || 0;
 });
 diseaseData.total = point.diseases || 0;
 return diseaseData;
 });
 };

 // Generate risk distribution data for pie chart
 const getRiskDistributionData = () => {
 if (!dashboardData?.statistics?.riskDistribution) return [];
 const colors = {
 LOW: '#10B981',
 MEDIUM: '#F59E0B',
 HIGH: '#EF4444',
 CRITICAL: '#DC2626',
 UNKNOWN: '#6B7280'
 };
 return Object.entries(dashboardData.statistics.riskDistribution)
 .filter(([_, value]) => value > 0)
 .map(([name, value]) => ({
 name,
 value,
 color: colors[name] || colors.UNKNOWN
 }));
 };

 // Generate decision distribution data
 const getDecisionDistributionData = () => {
 if (!dashboardData?.statistics?.decisionDistribution) return [];
 const colors = {
 SAFE: '#10B981',
 CAUTION: '#F59E0B',
 UNSAFE: '#EF4444'
 };
 return Object.entries(dashboardData.statistics.decisionDistribution)
 .filter(([_, value]) => value > 0)
 .map(([name, value]) => ({
 name,
 value,
 color: colors[name] || '#6B7280'
 }));
 };

 // Generate medication categories data
 const getMedicationCategoriesData = () => {
 if (!analyticsData?.topMedications) return [];
 return analyticsData.topMedications.slice(0, 5).map(med => ({
 name: med.medication.length > 15 ? med.medication.substring(0, 15) + '...' : med.medication,
 count: med.count,
 fullName: med.medication
 }));
 };

 // Generate disease categories data
 const getDiseaseCategoriesData = () => {
 if (!analyticsData?.topDiseases) return [];
 return analyticsData.topDiseases.slice(0, 5).map(disease => ({
 name: disease.disease.length > 15 ? disease.disease.substring(0, 15) + '...' : disease.disease,
 count: disease.count,
 fullName: disease.disease
 }));
 };

 // Calculate average risk score
 const getAverageRiskScore = () => {
 if (!dashboardData?.recentConsultations?.length) return 0;
 const total = dashboardData.recentConsultations.reduce((sum, c) => {
 const riskValues = { LOW: 25, MEDIUM: 50, HIGH: 75, CRITICAL: 100, UNKNOWN: 50 };
 return sum + (riskValues[c.risk_level] || 50);
 }, 0);
 return Math.round(total / dashboardData.recentConsultations.length);
 };

 // Get medication safety score
 const getMedicationSafetyScore = () => {
 if (!analyticsData?.summary?.safetyRate) return 0;
 return analyticsData.summary.safetyRate;
 };

 const fetchData = async (range) => {
 setLoading(true);
 setError(null);
 try {
 const [analyticsRes, dashboardRes] = await Promise.all([
 axios.get(`${API_URL}/medical-analytics/${patientName}?range=${range}`),
 axios.get(`${API_URL}/patient-dashboard/${patientName}`)
 ]);
 console.log('Analytics data:', analyticsRes.data);
 console.log('Trend data:', analyticsRes.data.trendData);
 console.log('Dashboard data:', dashboardRes.data);
 setAnalyticsData(analyticsRes.data);
 setDashboardData(dashboardRes.data);
 } catch (err) {
 console.error('Error fetching data:', err);
 setError(err.response?.data?.detail || 'Failed to fetch data');
 setAnalyticsData(null);
 setDashboardData(null);
 } finally {
 setLoading(false);
 }
 };

 const formatXAxis = (tick) => {
 const date = new Date(tick);
 if (timeRange === '24h') {
 return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
 }
 return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
 };

 const CustomTooltip = ({ active, payload, label }) => {
 if (active && payload && payload.length) {
 const data = payload[0].payload;
 return (
 <div className="bg-white p-4 rounded-xl shadow-lg border border-gray-200">
 <p className="text-sm font-semibold text-gray-700 mb-2">{formatXAxis(label)}</p>
 {payload.map((entry, index) => (
 <div key={index} className="flex items-center gap-2 text-sm">
 <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
 <span className="text-gray-600">{entry.name}:</span>
 <span className="font-bold text-gray-900">{entry.value}</span>
 </div>
 ))}
 </div>
 );
 }
 return null;
 };

 const StatCard = ({ title, value, icon, color, trend }) => (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
 >
 <div className="flex items-center justify-between mb-4">
 <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
 {icon}
 </div>
 {trend && (
 <div className={`flex items-center gap-1 text-sm font-medium ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
 <FiTrendingUp className={trend < 0 ? 'rotate-180' : ''} />
 <span>{Math.abs(trend)}%</span>
 </div>
 )}
 </div>
 <h3 className="text-gray-500 text-sm font-medium mb-1">{title}</h3>
 <p className="text-3xl font-bold text-gray-900">{value}</p>
 </motion.div>
 );
 
 const getRiskColor = (risk) => {
 switch (risk?.toUpperCase()) {
 case 'LOW': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
 case 'MEDIUM': return 'bg-amber-100 text-amber-700 border-amber-200';
 case 'HIGH': return 'bg-orange-100 text-orange-700 border-orange-200';
 case 'CRITICAL': return 'bg-red-100 text-red-700 border-red-200';
 default: return 'bg-gray-100 text-gray-700 border-gray-200';
 }
 };

 const getDecisionIcon = (decision) => {
 switch (decision) {
 case 'SAFE': return <FiCheckCircle className="text-green-500" size={20} />;
 case 'CAUTION': return <FiAlertTriangle className="text-amber-500" size={20} />;
 case 'UNSAFE': return <FiXCircle className="text-red-500" size={20} />;
 default: return <FiAlertCircle className="text-gray-500" size={20} />;
 }
 };

 if (!patientName || !patientName.trim()) {
 return (
 <div className="h-full flex items-center justify-center">
 <div className="text-center max-w-md">
 <FiDatabase className="w-16 h-16 mx-auto mb-4 text-gray-300" />
 <h3 className="text-xl font-semibold text-gray-700 mb-2">No Patient Selected</h3>
 <p className="text-gray-500 mb-4">Please register a patient first to view analytics.</p>
 </div>
 </div>
 );
 }

 if (loading) {
 return (
 <div className="h-full flex items-center justify-center">
 <div className="text-center">
 <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
 <p className="text-gray-600 font-medium">Loading analytics...</p>
 </div>
 </div>
 );
 }

 if (error) {
 return (
 <div className="h-full flex items-center justify-center">
 <div className="text-center max-w-md">
 <FiAlertCircle className="w-16 h-16 mx-auto mb-4 text-red-300" />
 <h3 className="text-xl font-semibold text-gray-700 mb-2">Error Loading Data</h3>
 <p className="text-gray-500">{error}</p>
 </div>
 </div>
 );
 }

 if (!analyticsData || !dashboardData) {
 return (
 <div className="h-full flex items-center justify-center">
 <div className="text-center max-w-md">
 <FiActivity className="w-16 h-16 mx-auto mb-4 text-gray-300" />
 <h3 className="text-xl font-semibold text-gray-700 mb-2">No Analytics Data</h3>
 <p className="text-gray-500 mb-4">No medical records found for <strong>{patientName}</strong>.</p>
 </div>
 </div>
 );
 }
 
 const { patient } = dashboardData;
 const { summary, trendData, topMedications, topDiseases } = analyticsData;

 return (
 <div className="h-full overflow-y-auto bg-purple-50">
 <div className="max-w-7xl mx-auto p-8">
 {showDoctorAlert && (
 <motion.div
 initial={{ opacity: 0, y: -20 }}
 animate={{ opacity: 1, y: 0 }}
 className="mb-6 bg-red-500 rounded-2xl p-6 text-white shadow-lg border-2 border-red-300"
 >
 <div className="flex items-start justify-between">
 <div className="flex items-center gap-4">
 <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center animate-pulse">
 <FiAlertCircle size={32} />
 </div>
 <div>
 <h3 className="text-2xl font-bold mb-2">⚠️ High Risk Detected - Doctor Consultation Required</h3>
 <p className="text-red-100 mb-3">
 Based on your recent medical analyses, we've identified potential health risks that require immediate professional attention.
 </p>
 </div>
 </div>
 <button
 onClick={() => setShowDoctorAlert(false)}
 className="text-white/80 hover:text-white transition-colors"
 >
 <FiX size={24} />
 </button>
 </div>
 </motion.div>
 )}

 <motion.div
 initial={{ opacity: 0, y: -20 }}
 animate={{ opacity: 1, y: 0 }}
 className="mb-8"
 >
 <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
 <div>
 <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
 <FiActivity className="text-purple-600" />
 Medical Analytics for {patient.name}
 </h1>
 </div>

 <div className="flex items-center gap-2 bg-white rounded-xl p-1.5 shadow-sm border border-gray-200">
 <FiCalendar className="text-gray-400 mr-2" />
 {timeRangeOptions.map((option) => (
 <button
 key={option.value}
 onClick={() => setTimeRange(option.value)}
 className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
 timeRange === option.value
 ? 'bg-purple-600 text-white shadow-md'
 : 'text-gray-600 hover:bg-gray-100'
 }`}
 >
 {option.label}
 </button>
 ))}
 </div>
 </div>
 </motion.div>
 
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 className="bg-purple-400 rounded-2xl p-6 mb-8 text-white shadow-lg"
 >
 <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
 <div className="flex items-center gap-4">
 <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
 <FiUser size={24} />
 </div>
 <div>
 <p className="text-purple-100 text-sm">Patient Name</p>
 <p className="text-lg font-semibold">{patient?.name}</p>
 </div>
 </div>
 <div className="flex items-center gap-4">
 <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
 <FiMail size={24} />
 </div>
 <div>
 <p className="text-purple-100 text-sm">Email</p>
 <p className="text-lg font-semibold">{patient?.email || 'Not provided'}</p>
 </div>
 </div>
 <div className="flex items-center gap-4">
 <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
 <FiShield size={24} />
 </div>
 <div>
 <p className="text-purple-100 text-sm">Patient ID</p>
 <p className="text-lg font-mono font-semibold">{patient?.user_id}</p>
 </div>
 </div>
 </div>
 </motion.div>

 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
 <StatCard
 title="Total Analyses"
 value={summary?.totalAnalyses || 0}
 icon={<FiDatabase className="w-6 h-6 text-white" />}
 color="bg-purple-400"
 />
 <StatCard
 title="Unique Medications"
 value={summary?.uniqueMedications || 0}
 icon={<FiActivity className="w-6 h-6 text-white" />}
 color="bg-emerald-500"
 />
 
 <StatCard
 title="Unique Diseases"
 value={summary?.uniqueDiseases || 0}
 icon={<FiTrendingUp className="w-6 h-6 text-white" />}
 color="bg-purple-400"
 />
 <StatCard
 title="Safety Rate"
 value={`${summary?.safetyRate || 0}%`}
 icon={<FiAlertCircle className="w-6 h-6 text-white" />}
 color="bg-amber-500"
 />
 </div>

 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.1 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-8"
 >
 <div className="mb-6">
 <h2 className="text-xl font-bold text-gray-900 mb-1">📊 Trends Over Time</h2>
 <p className="text-sm text-gray-500">Medical consultations, medications, and diseases tracked over selected period</p>
 </div>

 {trendData && trendData.length > 0 ? (
 <div>
 <div className="h-96 mb-6">
 <ResponsiveContainer width="100%" height="100%">
 <LineChart data={trendData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
 <CartesianGrid 
 strokeDasharray="3 3" 
 stroke="#D1D5DB" 
 strokeWidth={1}
 horizontal={true}
 vertical={true}
 />
 <XAxis
 dataKey="timestamp"
 tickFormatter={formatXAxis}
 stroke="#9CA3AF"
 tick={{ fontSize: 11 }}
 tickMargin={10}
 interval="preserveStartEnd"
 label={{ value: 'Time Period', position: 'insideBottomRight', offset: -5, style: { fill: '#6B7280', fontSize: 12, fontWeight: 500 } }}
 />
 <YAxis
 stroke="#6B7280"
 tick={{ fontSize: 12, fontWeight: 500 }}
 allowDecimals={false}
 domain={[0, 'auto']}
 tickCount={8}
 width={40}
 label={{ value: 'Count', angle: -90, position: 'insideLeft', style: { fill: '#6B7280', fontSize: 12, fontWeight: 500 } }}
 />
 <Tooltip content={<CustomTooltip />} />
 <Legend 
 wrapperStyle={{ paddingTop: '20px' }} 
 verticalAlign="bottom"
 height={36}
 />
 <Line
 type="monotone"
 dataKey="consultations"
 name="👥 Consultations"
 stroke="#8B5CF6"
 strokeWidth={3}
 dot={{ r: 5, strokeWidth: 2, fill: '#8B5CF6', stroke: '#fff' }}
 activeDot={{ r: 8, strokeWidth: 2 }}
 isAnimationActive={true}
 animationDuration={1000}
 />
 <Line
 type="monotone"
 dataKey="medications"
 name="💊 Medications"
 stroke="#A855F7"
 strokeWidth={2.5}
 dot={{ r: 4, strokeWidth: 2, fill: '#A855F7', stroke: '#fff' }}
 activeDot={{ r: 6, strokeWidth: 2 }}
 isAnimationActive={true}
 animationDuration={1000}
 />
 <Line
 type="monotone"
 dataKey="diseases"
 name="🏥 Diseases"
 stroke="#10B981"
 strokeWidth={2.5}
 dot={{ r: 4, strokeWidth: 2, fill: '#10B981', stroke: '#fff' }}
 activeDot={{ r: 6, strokeWidth: 2 }}
 isAnimationActive={true}
 animationDuration={1000}
 />
 </LineChart>
 </ResponsiveContainer>
 </div>
 </div>
 ) : (
 <div className="h-96 flex flex-col items-center justify-center text-gray-400">
 <FiActivity size={48} className="mb-4 opacity-50" />
 <p className="text-lg font-medium">No trend data available</p>
 <p className="text-sm">Perform some prescription analyses to see trends over time</p>
 </div>
 )}
 </motion.div>

 {/* Medication Trends Chart */}
 {topMedications && topMedications.length > 0 && (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.15 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-8"
 >
 <div className="mb-6">
 <h2 className="text-xl font-bold text-gray-900 mb-1">💊 Medication Usage Trends</h2>
 <p className="text-sm text-gray-500">Individual medication tracking over selected period</p>
 </div>

 {generateMedicationTrendData().length > 0 ? (
 <div className="h-80">
 <ResponsiveContainer width="100%" height="100%">
 <LineChart data={generateMedicationTrendData()} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
 <CartesianGrid 
 strokeDasharray="3 3" 
 stroke="#E5E7EB" 
 strokeWidth={1}
 />
 <XAxis
 dataKey="timestamp"
 tickFormatter={formatXAxis}
 stroke="#9CA3AF"
 tick={{ fontSize: 10 }}
 interval="preserveStartEnd"
 label={{ value: 'Time Period', position: 'insideBottomRight', offset: -5, style: { fill: '#6B7280', fontSize: 11 } }}
 />
 <YAxis
 stroke="#6B7280"
 tick={{ fontSize: 11 }}
 allowDecimals={false}
 domain={[0, 'auto']}
 width={35}
 label={{ value: 'Count', angle: -90, position: 'insideLeft', style: { fill: '#6B7280', fontSize: 11 } }}
 />
 <Tooltip content={<CustomTooltip />} />
 <Legend 
 wrapperStyle={{ paddingTop: '15px' }}
 height={30}
 wrapperClassName="text-xs"
 />
 {topMedications.slice(0, 5).map((med, idx) => {
 const colors = ['#A855F7', '#9333EA', '#EC4899', '#FACC15', '#10B981'];
 return (
 <Line
 key={med.medication}
 type="monotone"
 dataKey={med.medication}
 stroke={colors[idx % colors.length]}
 strokeWidth={2.5}
 dot={{ r: 3, strokeWidth: 1.5 }}
 activeDot={{ r: 5, strokeWidth: 2 }}
 name={med.medication.length > 15 ? med.medication.substring(0, 15) + '...' : med.medication}
 />
 );
 })}
 </LineChart>
 </ResponsiveContainer>
 </div>
 ) : null}
 </motion.div>
 )}

 {/* Disease Trends Chart */}
 {topDiseases && topDiseases.length > 0 && (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.2 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-8"
 >
 <div className="mb-6">
 <h2 className="text-xl font-bold text-gray-900 mb-1">🏥 Disease Prevalence Trends</h2>
 <p className="text-sm text-gray-500">Individual disease tracking over selected period</p>
 </div>

 {generateDiseaseTrendData().length > 0 ? (
 <div className="h-80">
 <ResponsiveContainer width="100%" height="100%">
 <LineChart data={generateDiseaseTrendData()} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
 <CartesianGrid 
 strokeDasharray="3 3" 
 stroke="#E5E7EB" 
 strokeWidth={1}
 />
 <XAxis
 dataKey="timestamp"
 tickFormatter={formatXAxis}
 stroke="#9CA3AF"
 tick={{ fontSize: 10 }}
 interval="preserveStartEnd"
 label={{ value: 'Time Period', position: 'insideBottomRight', offset: -5, style: { fill: '#6B7280', fontSize: 11 } }}
 />
 <YAxis
 stroke="#6B7280"
 tick={{ fontSize: 11 }}
 allowDecimals={false}
 domain={[0, 'auto']}
 width={35}
 label={{ value: 'Count', angle: -90, position: 'insideLeft', style: { fill: '#6B7280', fontSize: 11 } }}
 />
 <Tooltip content={<CustomTooltip />} />
 <Legend 
 wrapperStyle={{ paddingTop: '15px' }}
 height={30}
 wrapperClassName="text-xs"
 />
 {topDiseases.slice(0, 5).map((disease, idx) => {
 const colors = ['#10B981', '#06B6D4', '#6366F1', '#DC2626', '#F59E0B'];
 return (
 <Line
 key={disease.disease}
 type="monotone"
 dataKey={disease.disease}
 stroke={colors[idx % colors.length]}
 strokeWidth={2.5}
 dot={{ r: 3, strokeWidth: 1.5 }}
 activeDot={{ r: 5, strokeWidth: 2 }}
 name={disease.disease.length > 15 ? disease.disease.substring(0, 15) + '...' : disease.disease}
 />
 );
 })}
 </LineChart>
 </ResponsiveContainer>
 </div>
 ) : null}
 </motion.div>
 )}

 {/* Advanced Analytics Section */}
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.3 }}
 className="mb-8"
 >
 <div className="flex items-center justify-between mb-4">
 <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
 <FiPieChart className="text-purple-600" />
 Advanced Analytics
 </h2>
 <div className="flex gap-2">
 {['overview', 'risk', 'medications', 'diseases'].map((metric) => (
 <button
 key={metric}
 onClick={() => setSelectedMetric(metric)}
 className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all capitalize ${
 selectedMetric === metric
 ? 'bg-purple-600 text-white shadow-md'
 : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
 }`}
 >
 {metric}
 </button>
 ))}
 </div>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
 {/* Health Score Radar Chart */}
 {selectedMetric === 'overview' && (
 <>
 <motion.div
 initial={{ opacity: 0, scale: 0.9 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
 >
 <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
 <FiAward className="text-purple-600" />
 Health Metrics Overview
 </h3>
 <div className="h-64">
 <ResponsiveContainer width="100%" height="100%">
 <RadarChart data={[
 { metric: 'Safety Rate', value: getMedicationSafetyScore(), fullMark: 100 },
 { metric: 'Low Risk', value: dashboardData?.statistics?.riskDistribution?.LOW || 0, fullMark: Math.max(dashboardData?.statistics?.totalConsultations || 1, 1) },
 { metric: 'Medication Diversity', value: summary?.uniqueMedications || 0, fullMark: Math.max(summary?.uniqueMedications || 1, 1) },
 { metric: 'Disease Tracking', value: summary?.uniqueDiseases || 0, fullMark: Math.max(summary?.uniqueDiseases || 1, 1) },
 { metric: 'Consultation Rate', value: Math.min(summary?.totalAnalyses || 0, 20) * 5, fullMark: 100 },
 ]}>
 <PolarGrid stroke="#E5E7EB" />
 <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: '#6B7280' }} />
 <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
 <Radar name="Score" dataKey="value" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.5} />
 <Tooltip />
 </RadarChart>
 </ResponsiveContainer>
 </div>
 </motion.div>

 <motion.div
 initial={{ opacity: 0, scale: 0.9 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
 >
 <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
 <FiTarget className="text-green-600" />
 Decision Distribution
 </h3>
 <div className="h-64">
 <ResponsiveContainer width="100%" height="100%">
 <PieChart>
 <Pie
 data={getDecisionDistributionData()}
 cx="50%"
 cy="50%"
 labelLine={false}
 label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
 outerRadius={80}
 fill="#8884d8"
 dataKey="value"
 >
 {getDecisionDistributionData().map((entry, index) => (
 <Cell key={`cell-${index}`} fill={entry.color} />
 ))}
 </Pie>
 <Tooltip />
 </PieChart>
 </ResponsiveContainer>
 </div>
 <div className="flex justify-center gap-4 mt-4">
 {getDecisionDistributionData().map((item) => (
 <div key={item.name} className="flex items-center gap-2">
 <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
 <span className="text-sm text-gray-600">{item.name}</span>
 </div>
 ))}
 </div>
 </motion.div>
 </>
 )}

 {/* Risk Distribution */}
 {selectedMetric === 'risk' && (
 <>
 <motion.div
 initial={{ opacity: 0, scale: 0.9 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
 >
 <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
 <FiHeart className="text-red-600" />
 Risk Level Distribution
 </h3>
 <div className="h-64">
 <ResponsiveContainer width="100%" height="100%">
 <PieChart>
 <Pie
 data={getRiskDistributionData()}
 cx="50%"
 cy="50%"
 labelLine={false}
 label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
 outerRadius={80}
 fill="#8884d8"
 dataKey="value"
 >
 {getRiskDistributionData().map((entry, index) => (
 <Cell key={`cell-${index}`} fill={entry.color} />
 ))}
 </Pie>
 <Tooltip />
 </PieChart>
 </ResponsiveContainer>
 </div>
 <div className="grid grid-cols-5 gap-2 mt-4">
 {getRiskDistributionData().map((item) => (
 <div key={item.name} className="text-center">
 <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ backgroundColor: item.color }} />
 <span className="text-xs text-gray-600">{item.name}</span>
 <p className="text-sm font-bold text-gray-900">{item.value}</p>
 </div>
 ))}
 </div>
 </motion.div>

 <motion.div
 initial={{ opacity: 0, scale: 0.9 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
 >
 <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
 <FiZap className="text-teal-600" />
 Risk Analysis
 </h3>
 <div className="space-y-4">
 <div className="flex items-center justify-between p-3 bg-red-50 rounded-xl">
 <div className="flex items-center gap-3">
 <FiAlertTriangle className="text-red-600" size={20} />
 <span className="text-sm font-medium text-gray-700">Average Risk Score</span>
 </div>
 <span className="text-lg font-bold text-red-600">{getAverageRiskScore()}/100</span>
 </div>
 <div className="flex items-center justify-between p-3 bg-green-50 rounded-xl">
 <div className="flex items-center gap-3">
 <FiCheckCircle className="text-green-600" size={20} />
 <span className="text-sm font-medium text-gray-700">Safe Consultations</span>
 </div>
 <span className="text-lg font-bold text-green-600">{dashboardData?.statistics?.decisionDistribution?.SAFE || 0}</span>
 </div>
 <div className="flex items-center justify-between p-3 bg-amber-50 rounded-xl">
 <div className="flex items-center gap-3">
 <FiAlertCircle className="text-amber-600" size={20} />
 <span className="text-sm font-medium text-gray-700">Caution Needed</span>
 </div>
 <span className="text-lg font-bold text-amber-600">{dashboardData?.statistics?.decisionDistribution?.CAUTION || 0}</span>
 </div>
 <div className="flex items-center justify-between p-3 bg-red-50 rounded-xl">
 <div className="flex items-center gap-3">
 <FiXCircle className="text-red-600" size={20} />
 <span className="text-sm font-medium text-gray-700">Unsafe Cases</span>
 </div>
 <span className="text-lg font-bold text-red-600">{dashboardData?.statistics?.decisionDistribution?.UNSAFE || 0}</span>
 </div>
 </div>
 </motion.div>
 </>
 )}

 {/* Medications Analysis */}
 {selectedMetric === 'medications' && (
 <motion.div
 initial={{ opacity: 0, scale: 0.9 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 lg:col-span-2"
 >
 <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
 <FiDroplet className="text-purple-600" />
 Top Medications Analysis
 </h3>
 <div className="h-64">
 <ResponsiveContainer width="100%" height="100%">
 <BarChart data={getMedicationCategoriesData()}>
 <CartesianGrid 
 strokeDasharray="3 3" 
 stroke="#D1D5DB" 
 strokeWidth={1}
 horizontal={true}
 vertical={false}
 />
 <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" height={60} />
 <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#6B7280" />
 <Tooltip
 content={({ active, payload }) => {
 if (active && payload && payload[0]) {
 return (
 <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
 <p className="text-sm font-semibold text-gray-700">{payload[0].payload.fullName}</p>
 <p className="text-gray-600">Count: <span className="font-bold">{payload[0].value}</span></p>
 </div>
 );
 }
 return null;
 }}
 />
 <Bar dataKey="count" fill="#A855F7" radius={[4, 4, 0, 0]} />
 </BarChart>
 </ResponsiveContainer>
 </div>
 </motion.div>
 )}

 {/* Diseases Analysis */}
 {selectedMetric === 'diseases' && (
 <motion.div
 initial={{ opacity: 0, scale: 0.9 }}
 animate={{ opacity: 1, scale: 1 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 lg:col-span-2"
 >
 <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
 <FiActivity className="text-purple-600" />
 Top Diseases/Conditions
 </h3>
 <div className="h-64">
 <ResponsiveContainer width="100%" height="100%">
 <BarChart data={getDiseaseCategoriesData()}>
 <CartesianGrid 
 strokeDasharray="3 3" 
 stroke="#D1D5DB" 
 strokeWidth={1}
 horizontal={true}
 vertical={false}
 />
 <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" height={60} />
 <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#6B7280" />
 <Tooltip
 content={({ active, payload }) => {
 if (active && payload && payload[0]) {
 return (
 <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
 <p className="text-sm font-semibold text-gray-700">{payload[0].payload.fullName}</p>
 <p className="text-gray-600">Count: <span className="font-bold">{payload[0].value}</span></p>
 </div>
 );
 }
 return null;
 }}
 />
 <Bar dataKey="count" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
 </BarChart>
 </ResponsiveContainer>
 </div>
 </motion.div>
 )}
 </div>
 </motion.div>
 
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.6 }}
 className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
 >
 <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
 <FiClock size={20} />
 Recent Consultations
 </h2>
 <div className="space-y-3">
 {dashboardData.recentConsultations && dashboardData.recentConsultations.length > 0 ? (
 dashboardData.recentConsultations.map((consultation, index) => (
 <motion.div
 key={consultation.id || index}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 0.1 + index * 0.1 }}
 className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
 >
 <div className="flex items-center gap-4">
 {getDecisionIcon(consultation.final_decision)}
 <div>
 <p className="font-semibold text-gray-900">{consultation.disease}</p>
 <p className="text-sm text-gray-500">{consultation.medication}</p>
 </div>
 </div>
 <div className="flex items-center gap-4">
 <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getRiskColor(consultation.risk_level)}`}>
 {consultation.risk_level}
 </span>
 <span className="text-sm text-gray-500">
 {new Date(consultation.date).toLocaleDateString()}
 </span>
 </div>
 </motion.div>
 ))
 ) : (
 <p className="text-gray-500 text-center py-8">No consultations yet</p>
 )}
 </div>
 </motion.div>

 {/* Advertisement Section - Placeholder for future ads (Google Style) */}
 <div className="mt-8 pt-4">
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
 </div>
 </div>
 );
};

export default Analytics;
