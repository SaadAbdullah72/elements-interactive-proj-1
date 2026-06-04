// App.jsx
// Main frontend router/state manager for the clinician workflow.
// Responsibilities:
// - Maintain `currentScreen` and persist minimal auth/session state.
// - Avoid embedding complex business logic here; delegate to
//   `IntelliHealthInterface` and auth components.
// Security note: sensitive tokens are kept in sessionStorage; prefer
// short-lived tokens and server-side session validation in production.
import React, { useState, useEffect } from 'react';
import DoctorLogin from './DoctorLogin';
import DoctorSignup from './DoctorSignup';
import PatientVerificationForm from './PatientVerificationForm';
import IntelliHealthInterface from './IntelliHealthInterface';

function App() {
  const getScreenFromLocation = () => {
    if (typeof window === 'undefined') {
      return 'login';
    }

    const hashPath = window.location.hash.toLowerCase().replace(/^#\/?/, '');
    if (hashPath.includes('signup')) {
      return 'signup';
    }
    if (hashPath.includes('verification')) {
      return 'verification';
    }
    if (hashPath.includes('consultation')) {
      return 'consultation';
    }

    const path = window.location.pathname.replace(/\/+$/, '').toLowerCase();
    if (path.includes('/signup')) {
      return 'signup';
    }
    if (path.includes('/verification')) {
      return 'verification';
    }
    if (path.includes('/consultation')) {
      return 'consultation';
    }
    return 'login';
  };

  const isLiveDeployment = () => {
    if (typeof window === 'undefined') return false;
    const host = window.location.hostname.toLowerCase();
    return !['localhost', '127.0.0.1', '::1'].includes(host);
  };

  const [currentScreen, setCurrentScreen] = useState('login');
  const [patientData, setPatientData] = useState(null);

  // Update the browser tab title for each screen
  useEffect(() => {
    let title = 'DiabAssist';
    switch (currentScreen) {
      case 'login':
        title = 'Welcome to DiabAssist! Your AI Clinical Assistance Tool';
        break;
      case 'signup':
        title = 'Create Your DiabAssist Doctor Account';
        break;
      case 'verification':
        title = 'DiabAssist Patient Verification | AI Clinical Assistance Tool';
        break;
      case 'consultation':
        title = 'DiabAssist Clinical Consultation | AI Clinical Assistance Tool';
        break;
      default:
        title = 'DiabAssist';
    }
    document.title = title;
  }, [currentScreen]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const routeScreen = getScreenFromLocation();
    const live = isLiveDeployment();

    if (live && routeScreen === 'signup') {
      setCurrentScreen('login');
      return;
    }

    if (routeScreen === 'signup') {
      setCurrentScreen('signup');
      return;
    }

    const sessionFlag = localStorage.getItem('doctorSessionActive');
    const token = sessionStorage.getItem('authToken');
    const role = sessionStorage.getItem('userRole');
    const savedPatient = localStorage.getItem('currentPatient');

    if (sessionFlag && !token) {
      localStorage.removeItem('doctorSessionActive');
      localStorage.removeItem('currentPatient');
      setPatientData(null);
      setCurrentScreen('login');
      return;
    }

    if (token && role === 'doctor') {
      if (savedPatient) {
        setPatientData(JSON.parse(savedPatient));
        setCurrentScreen('consultation');
      } else {
        setCurrentScreen('verification');
      }
      return;
    }

    setCurrentScreen(routeScreen);
  }, []);

  const handleLoginSuccess = (token, doctor) => {
    sessionStorage.setItem('authToken', token);
    sessionStorage.setItem('doctorName', doctor.name);
    sessionStorage.setItem('doctorEmail', doctor.email);
    sessionStorage.setItem('userRole', 'doctor');
    // Mark that a doctor session exists — stored persistently so we can
    // detect if the tab is later closed and reopened (sessionStorage clears).
    localStorage.setItem('doctorSessionActive', 'true');
    setCurrentScreen('verification');
  };

  const handleSignupSuccess = (signupData) => {
    // If account is active, redirect to login
    if (signupData.account_status === 'active') {
      setCurrentScreen('login');
    } else {
      // Show message that account is pending verification
      setCurrentScreen('login');
    }
  };

  const handleBackToLogin = () => {
    setCurrentScreen('login');
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    let targetHash = '#/';
    if (currentScreen === 'signup') targetHash = '#/signup';
    else if (currentScreen === 'verification') targetHash = '#/verification';
    else if (currentScreen === 'consultation') targetHash = '#/consultation';
    else if (currentScreen === 'login') targetHash = '#/login';

    const currentHash = window.location.hash || '#/';
    if (currentHash.toLowerCase() !== targetHash.toLowerCase()) {
      window.location.hash = targetHash;
    }
  }, [currentScreen]);

  useEffect(() => {
    if (currentScreen === 'signup' && isLiveDeployment()) {
      setCurrentScreen('login');
    }
  }, [currentScreen]);

  const handleVerificationSuccess = (patient) => {
    setPatientData(patient);
    localStorage.setItem('currentPatient', JSON.stringify(patient));
    setCurrentScreen('consultation');
  };

  const handleLogout = () => {
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('userRole');
    sessionStorage.removeItem('doctorName');
    sessionStorage.removeItem('doctorEmail');
    localStorage.removeItem('currentPatient');
    // Remove the persistent session marker on explicit logout
    localStorage.removeItem('doctorSessionActive');
    setPatientData(null);
    setCurrentScreen('login');
  };

  const handleBackToVerification = () => {
    localStorage.removeItem('currentPatient');
    setPatientData(null);
    setCurrentScreen('verification');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 'calc(100vh - 18px)' }}>

      {/* Main Screen Content */}
      <div style={{ flex: 1 }}>
        {currentScreen === 'login' && (
          <DoctorLogin onLoginSuccess={handleLoginSuccess} />
        )}

        {currentScreen === 'signup' && (
          <DoctorSignup
            onSignupSuccess={handleSignupSuccess}
            onBackToLogin={handleBackToLogin}
          />
        )}

        {currentScreen === 'verification' && (
          <PatientVerificationForm
            onVerificationSuccess={handleVerificationSuccess}
            onCancel={handleLogout}
          />
        )}

        {currentScreen === 'consultation' && (
          <IntelliHealthInterface
            patientData={patientData}
            onBack={handleBackToVerification}
            onLogout={handleLogout}
          />
        )}
      </div>

      {/* Global footer — hidden on login since login has its own */}
      {currentScreen !== 'login' && (
        <footer
          className="global-footer"
          style={{
            padding: '14px 16px',
            textAlign: 'center',
            background: '#ffffff',
            flexShrink: 0,
            borderTop: '1px solid #f0f0f0',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: '8px',
            alignItems: 'center'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <a href="#" style={{ color: '#6b7280', textDecoration: 'none' }}>Privacy Statement</a>
            <span style={{ color: '#d1d5db' }}>•</span>
            <a href="#" style={{ color: '#6b7280', textDecoration: 'none' }}>Terms and Conditions</a>
            <span style={{ color: '#d1d5db' }}>•</span>
            <a href="#" style={{ color: '#6b7280', textDecoration: 'none' }}>Helpline</a>
          </div>
          <div style={{ color: '#6b7280', fontSize: '12px', whiteSpace: 'nowrap' }}>
            This tool provides guideline-aligned suggestions only. The final diagnosis, treatment plan, and prescription are the sole responsibility of the licensed treating physician
          </div>
        </footer>
      )}

    </div>
  );
}

export default App;