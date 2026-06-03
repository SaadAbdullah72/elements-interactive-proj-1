// KnowledgeGraph.jsx
// Purpose: Visual, interactive representation of disease-symptom-medication
// relationships. This component is purely visual and accepts `graphData` as
// input; heavy graph computations should be preprocessed server-side where
// possible to keep the UI responsive.
import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FaNotesMedical, FaPills, FaVirus, FaTimes, FaArrowRight } from 'react-icons/fa';

const KnowledgeGraph = ({ graphData, onClose }) => {
 const [selectedNode, setSelectedNode] = useState(null);
 const [zoom, setZoom] = useState(1);
 const [pan, setPan] = useState({ x: 0, y: 0 });
 const [isDragging, setIsDragging] = useState(false);
 const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

 // Process graph data and create layout
 const { nodes, edges, width, height, hasData } = useMemo(() => {
 if (!graphData) {
 return { nodes: [], edges: [], width: 900, height: 600, hasData: false };
 }

 // Handle different graph data structures
 const diseaseInfo = graphData.disease;
 const medicationList = graphData.medications || [];
 
 // Use provided nodes/edges or create from disease/medications
 let nodes = graphData.nodes || [];
 let edges = graphData.edges || [];
 
 // If no nodes provided but we have disease/medication info, create them
 if (nodes.length === 0) {
 const centerX = 450;
 const centerY = 300;
 
 // Add disease node
 if (diseaseInfo) {
 nodes.push({
 id: diseaseInfo.name || 'Unknown Disease',
 type: 'disease',
 label: diseaseInfo.name || 'Unknown Disease',
 x: centerX,
 y: centerY
 });
 
 // Add symptom nodes
 if (diseaseInfo.symptoms) {
 diseaseInfo.symptoms.slice(0, 5).forEach((symptom, i) => {
 const angle = Math.PI / 2 + (i / Math.max(diseaseInfo.symptoms.slice(0, 5).length - 1, 1)) * Math.PI;
 const radius = 180;
 nodes.push({
 id: symptom,
 type: 'symptom',
 label: symptom,
 x: centerX - Math.cos(angle) * radius,
 y: centerY - Math.sin(angle) * radius
 });
 edges.push({
 source: diseaseInfo.name || 'Unknown Disease',
 target: symptom,
 type: 'has_symptom'
 });
 });
 }
 }
 
 // Add medication nodes
 medicationList.forEach((med, i) => {
 const medName = med.name || med;
 const angle = -Math.PI / 2 + (i / Math.max(medicationList.length - 1, 1)) * Math.PI;
 const radius = 180;
 const medX = centerX - Math.cos(angle) * radius;
 const medY = centerY - Math.sin(angle) * radius;
 
 nodes.push({
 id: medName,
 type: 'medication',
 label: medName,
 x: medX,
 y: medY
 });
 
 if (diseaseInfo) {
 edges.push({
 source: diseaseInfo.name || 'Unknown Disease',
 target: medName,
 type: 'treated_by'
 });
 }
 });
 }

 // Calculate layout for nodes without positions
 const diseaseNodes = nodes.filter(n => n.type === 'disease');
 const symptomNodes = nodes.filter(n => n.type === 'symptom');
 const medicationNodes = nodes.filter(n => n.type === 'medication');

 const layoutNodes = [];
 const centerX = 450;
 const centerY = 300;

 // Position disease nodes in center
 diseaseNodes.forEach((node, i) => {
 layoutNodes.push({
 ...node,
 x: node.x || centerX,
 y: node.y || centerY
 });
 });

 // Position symptoms in a semicircle on the left
 symptomNodes.forEach((node, i) => {
 if (node.x && node.y) {
 layoutNodes.push(node);
 } else {
 const angle = Math.PI / 2 + (i / Math.max(symptomNodes.length - 1, 1)) * Math.PI;
 const radius = 180;
 layoutNodes.push({
 ...node,
 x: centerX - Math.cos(angle) * radius,
 y: centerY - Math.sin(angle) * radius
 });
 }
 });

 // Position medications in a semicircle on the right
 medicationNodes.forEach((node, i) => {
 if (node.x && node.y) {
 layoutNodes.push(node);
 } else {
 const angle = -Math.PI / 2 + (i / Math.max(medicationNodes.length - 1, 1)) * Math.PI;
 const radius = 180;
 layoutNodes.push({
 ...node,
 x: centerX - Math.cos(angle) * radius,
 y: centerY - Math.sin(angle) * radius
 });
 }
 });

 return { 
 nodes: layoutNodes, 
 edges, 
 width: 900, 
 height: 600,
 hasData: layoutNodes.length > 0
 };
 }, [graphData]);

 const getNodeColor = (type) => {
 switch (type) {
 case 'disease': return '#8B5CF6';
 case 'symptom': return '#3B82F6';
 case 'medication': return '#EC4899';
 default: return '#6B7280';
 }
 };

 const getNodeIcon = (type) => {
 switch (type) {
 case 'disease': return <FaNotesMedical size={18} />;
 case 'symptom': return <FaVirus size={14} />;
 case 'medication': return <FaPills size={18} />;
 default: return null;
 }
 };

 const handleMouseDown = (e) => {
 if (e.target.tagName === 'svg' || e.target.classList.contains('graph-background')) {
 setIsDragging(true);
 setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
 }
 };

 const handleMouseMove = (e) => {
 if (isDragging) {
 setPan({
 x: e.clientX - dragStart.x,
 y: e.clientY - dragStart.y
 });
 }
 };

 const handleMouseUp = () => {
 setIsDragging(false);
 };

 const handleWheel = (e) => {
 e.preventDefault();
 const newZoom = Math.max(0.5, Math.min(2, zoom - e.deltaY * 0.001));
 setZoom(newZoom);
 };

 // Alternative medications based on disease
 const alternativeMedications = useMemo(() => {
 if (!graphData?.disease?.medications) return [];
 const currentMeds = graphData.medications?.map(m => m.name?.toLowerCase()) || [];
 return graphData.disease.medications
 .filter(med => !currentMeds.includes(med.toLowerCase()))
 .slice(0, 5);
 }, [graphData]);

 return (
 <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
 <motion.div
 initial={{ opacity: 0, scale: 0.9, y: 20 }}
 animate={{ opacity: 1, scale: 1, y: 0 }}
 exit={{ opacity: 0, scale: 0.9, y: 20 }}
 className="bg-purple-50 rounded-3xl shadow-2xl w-full max-w-6xl overflow-hidden border-2 border-purple-200 max-h-[90vh] flex flex-col"
 >
 {/* Header */}
 <div className="bg-purple-400 p-6 flex justify-between items-center shrink-0">
 <div>
 <h2 className="text-2xl font-bold text-white flex items-center gap-3">
 <FaNotesMedical className="text-3xl" />
 Medical Knowledge Graph
 </h2>
 <p className="text-purple-100 text-sm mt-1">
 Visualizing disease-symptom-medication relationships
 </p>
 </div>
 <button
 onClick={onClose}
 className="text-white hover:bg-white/20 rounded-full p-3 transition-all hover:rotate-90"
 >
 <FaTimes size={24} />
 </button>
 </div>

 {/* Graph Controls */}
 <div className="bg-white/50 backdrop-blur-sm px-6 py-3 flex justify-between items-center border-b border-purple-200 shrink-0">
 <div className="flex items-center gap-4">
 <div className="flex items-center gap-2">
 <div className="w-4 h-4 rounded-full bg-purple-500"></div>
 <span className="text-sm text-gray-700">Disease</span>
 </div>
 <div className="flex items-center gap-2">
 <div className="w-4 h-4 rounded-full bg-blue-500"></div>
 <span className="text-sm text-gray-700">Symptom</span>
 </div>
 <div className="flex items-center gap-2">
 <div className="w-4 h-4 rounded-full bg-pink-500"></div>
 <span className="text-sm text-gray-700">Medication</span>
 </div>
 </div>
 <div className="flex items-center gap-2">
 <button
 onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
 className="px-3 py-1.5 bg-white rounded-lg shadow hover:shadow-md transition-all text-purple-600 font-bold"
 >
 −
 </button>
 <span className="text-sm text-gray-600 font-medium">{Math.round(zoom * 100)}%</span>
 <button
 onClick={() => setZoom(z => Math.min(2, z + 0.1))}
 className="px-3 py-1.5 bg-white rounded-lg shadow hover:shadow-md transition-all text-purple-600 font-bold"
 >
 +
 </button>
 <button
 onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
 className="px-3 py-1.5 bg-purple-100 rounded-lg shadow hover:shadow-md transition-all text-purple-600 font-bold text-sm"
 >
 Reset
 </button>
 </div>
 </div>

 {/* Main Content Area */}
 <div className="flex-1 flex overflow-hidden">
 {/* Graph Canvas */}
 <div
 className="flex-1 relative bg-purple-50 overflow-hidden"
 onMouseDown={handleMouseDown}
 onMouseMove={handleMouseMove}
 onMouseUp={handleMouseUp}
 onMouseLeave={handleMouseUp}
 onWheel={handleWheel}
 >
 {!hasData ? (
 <div className="flex items-center justify-center h-full text-gray-500">
 <div className="text-center">
 <FaNotesMedical size={48} className="mx-auto mb-4 opacity-50" />
 <p className="text-lg font-medium">No graph data available</p>
 <p className="text-sm">Enter patient details to visualize the knowledge graph</p>
 </div>
 </div>
 ) : (
 <svg
 width="100%"
 height="100%"
 viewBox={`0 0 ${width} ${height}`}
 className="graph-background cursor-grab active:cursor-grabbing"
 preserveAspectRatio="xMidYMid meet"
 >
 <defs>
 {/* Gradients for edges */}
 <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
 <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.6" />
 <stop offset="100%" stopColor="#EC4899" stopOpacity="0.6" />
 </linearGradient>
 {/* Glow filter */}
 <filter id="glow">
 <feGaussianBlur stdDeviation="3" result="coloredBlur" />
 <feMerge>
 <feMergeNode in="coloredBlur" />
 <feMergeNode in="SourceGraphic" />
 </feMerge>
 </filter>
 {/* Shadow filter */}
 <filter id="shadow">
 <feDropShadow dx="0" dy="2" stdDeviation="4" floodOpacity="0.3" />
 </filter>
 {/* Grid pattern */}
 <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
 <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e5e7eb" strokeWidth="1"/>
 </pattern>
 </defs>

 {/* Background Grid */}
 <rect width="100%" height="100%" fill="url(#grid)" opacity="0.5" />

 {/* X and Y Axes */}
 <g className="axes" stroke="#9ca3af" strokeWidth="1" opacity="0.3">
 {/* X-axis */}
 <line x1="50" y1={height - 50} x2={width - 50} y2={height - 50} markerEnd="url(#arrowhead)" />
 {/* Y-axis */}
 <line x1="50" y1="50" x2="50" y2={height - 50} markerEnd="url(#arrowheadY)" />
 
 {/* Axis labels */}
 <text x={width - 40} y={height - 30} fontSize="12" fill="#6b7280">Medications →</text>
 <text x="60" y="40" fontSize="12" fill="#6b7280">← Symptoms</text>
 </g>

 <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
 {/* Edges with smooth curves */}
 {edges.map((edge, index) => {
 const sourceNode = nodes.find(n => n.id === edge.source);
 const targetNode = nodes.find(n => n.id === edge.target);
 if (!sourceNode || !targetNode) return null;

 const isSymptomEdge = edge.type === 'has_symptom';
 const controlX1 = sourceNode.x - 50;
 const controlX2 = targetNode.x + 50;

 return (
 <g key={`edge-${index}`}>
 <motion.path
 initial={{ pathLength: 0, opacity: 0 }}
 animate={{ pathLength: 1, opacity: 0.6 }}
 transition={{ delay: index * 0.1, duration: 0.8 }}
 d={`M ${sourceNode.x} ${sourceNode.y} C ${controlX1} ${sourceNode.y}, ${controlX2} ${targetNode.y}, ${targetNode.x} ${targetNode.y}`}
 fill="none"
 stroke={isSymptomEdge ? '#3B82F6' : '#EC4899'}
 strokeWidth="2.5"
 strokeDasharray="6,4"
 >
 <animate
 attributeName="stroke-dashoffset"
 from="100"
 to="0"
 dur="3s"
 repeatCount="indefinite"
 />
 </motion.path>
 
 {/* Edge label */}
 <text
 x={(sourceNode.x + targetNode.x) / 2}
 y={(sourceNode.y + targetNode.y) / 2 - 10}
 textAnchor="middle"
 fontSize="10"
 fill={isSymptomEdge ? '#3B82F6' : '#EC4899'}
 fontWeight="600"
 >
 {isSymptomEdge ? 'has symptom' : 'treated by'}
 </text>
 </g>
 );
 })}

 {/* Nodes */}
 {nodes.map((node, index) => (
 <motion.g
 key={`node-${node.id}`}
 initial={{ scale: 0, opacity: 0 }}
 animate={{ scale: 1, opacity: 1 }}
 transition={{ delay: index * 0.1, type: "spring", stiffness: 200 }}
 onClick={() => setSelectedNode(selectedNode?.id === node.id ? null : node)}
 className="cursor-pointer"
 >
 {/* Outer glow ring */}
 <circle
 cx={node.x}
 cy={node.y}
 r={node.type === 'disease' ? 55 : 40}
 fill={getNodeColor(node.type)}
 opacity="0.15"
 >
 <animate
 attributeName="r"
 values={`${node.type === 'disease' ? 55 : 40};${node.type === 'disease' ? 60 : 45};${node.type === 'disease' ? 55 : 40}`}
 dur="2s"
 repeatCount="indefinite"
 />
 </circle>

 {/* Main node circle */}
 <circle
 cx={node.x}
 cy={node.y}
 r={node.type === 'disease' ? 50 : 35}
 fill={getNodeColor(node.type)}
 filter="url(#shadow)"
 stroke="white"
 strokeWidth="4"
 />

 {/* Icon */}
 <g
 transform={`translate(${node.x - 10}, ${node.y - 10})`}
 fill="white"
 >
 {getNodeIcon(node.type)}
 </g>

 {/* Label */}
 <text
 x={node.x}
 y={node.y + (node.type === 'disease' ? 75 : 60)}
 textAnchor="middle"
 fill="#374151"
 fontSize="13"
 fontWeight="700"
 className="select-none"
 >
 {node.label.length > 25 ? node.label.substring(0, 25) + '...' : node.label}
 </text>

 {/* Hover effect */}
 <circle
 cx={node.x}
 cy={node.y}
 r={node.type === 'disease' ? 50 : 35}
 fill="transparent"
 stroke={getNodeColor(node.type)}
 strokeWidth="3"
 strokeDasharray="6,4"
 opacity="0"
 className="hover:opacity-100 transition-opacity"
 >
 <animateTransform
 attributeName="transform"
 type="rotate"
 from={`0 ${node.x} ${node.y}`}
 to={`360 ${node.x} ${node.y}`}
 dur="15s"
 repeatCount="indefinite"
 />
 </circle>
 </motion.g>
 ))}
 </g>

 {/* Arrow markers */}
 <defs>
 <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
 <polygon points="0 0, 10 3.5, 0 7" fill="#9ca3af" />
 </marker>
 <marker id="arrowheadY" markerWidth="10" markerHeight="7" refX="3.5" refY="9" orient="auto">
 <polygon points="3.5 0, 7 10, 0 10" fill="#9ca3af" />
 </marker>
 </defs>
 </svg>
 )}

 {/* Selected Node Info Panel */}
 {selectedNode && (
 <motion.div
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 exit={{ opacity: 0, x: 20 }}
 className="absolute top-4 right-4 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl p-5 border-2 border-purple-200 max-w-xs"
 >
 <div className="flex items-center gap-3 mb-3">
 <div
 className="w-10 h-10 rounded-xl flex items-center justify-center text-white"
 style={{ backgroundColor: getNodeColor(selectedNode.type) }}
 >
 {getNodeIcon(selectedNode.type)}
 </div>
 <div>
 <h3 className="font-bold text-gray-800 capitalize">{selectedNode.type}</h3>
 <p className="text-xs text-gray-500">Node Details</p>
 </div>
 </div>
 <p className="text-sm text-gray-700 font-semibold">{selectedNode.label}</p>
 <div className="mt-3 flex gap-2">
 <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-md text-xs font-medium">
 {selectedNode.type}
 </span>
 </div>
 </motion.div>
 )}

 {/* Instructions */}
 <div className="absolute bottom-4 left-4 bg-white/80 backdrop-blur-sm rounded-xl px-4 py-3 shadow-lg border border-purple-100">
 <p className="text-xs text-gray-600">
 <span className="font-semibold">🖱️ Drag</span> to pan • <span className="font-semibold">🔍 Scroll</span> to zoom • <span className="font-semibold">👆 Click</span> for details
 </p>
 </div>
 </div>

 {/* Sidebar with Alternative Medications */}
 {alternativeMedications.length > 0 && (
 <div className="w-72 bg-white/70 backdrop-blur-sm border-l border-purple-200 p-4 overflow-y-auto">
 <div className="bg-green-500 rounded-2xl p-4 border-2 border-emerald-300">
 <div className="flex items-center gap-2 mb-3">
 <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center shadow-md">
 <FaArrowRight className="text-white text-sm" />
 </div>
 <h3 className="font-bold text-emerald-800 text-sm">Alternative Medications</h3>
 </div>
 <p className="text-xs text-emerald-700 mb-3">
 Consider these alternatives for {graphData.disease?.name}:
 </p>
 <div className="space-y-2">
 {alternativeMedications.map((med, idx) => (
 <motion.div
 key={idx}
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: idx * 0.1 }}
 className="px-3 py-2 bg-white rounded-lg border border-emerald-200 shadow-sm"
 >
 <p className="text-sm font-semibold text-gray-800">{med}</p>
 </motion.div>
 ))}
 </div>
 <p className="text-xs text-emerald-600 mt-3 italic">
 ⚠️ Always consult with a healthcare professional before changing medications
 </p>
 </div>
 </div>
 )}
 </div>

 {/* Footer Stats */}
 <div className="bg-white/50 backdrop-blur-sm px-6 py-4 border-t border-purple-200 flex justify-between items-center shrink-0">
 <div className="flex gap-6">
 <div className="text-center">
 <p className="text-2xl font-bold text-purple-600">{nodes.filter(n => n.type === 'disease').length}</p>
 <p className="text-xs text-gray-600">Diseases</p>
 </div>
 <div className="text-center">
 <p className="text-2xl font-bold text-blue-600">{nodes.filter(n => n.type === 'symptom').length}</p>
 <p className="text-xs text-gray-600">Symptoms</p>
 </div>
 <div className="text-center">
 <p className="text-2xl font-bold text-pink-600">{nodes.filter(n => n.type === 'medication').length}</p>
 <p className="text-xs text-gray-600">Medications</p>
 </div>
 <div className="text-center">
 <p className="text-2xl font-bold text-indigo-600">{edges.length}</p>
 <p className="text-xs text-gray-600">Relationships</p>
 </div>
 </div>
 <p className="text-sm text-gray-500 italic">
 Interactive medical knowledge visualization
 </p>
 </div>
 </motion.div>
 </div>
 );
};

export default KnowledgeGraph;
