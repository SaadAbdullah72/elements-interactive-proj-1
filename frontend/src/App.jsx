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
  const getInitialScreen = () => {
    if (typeof window === 'undefined') {
      return 'login';
    }
    const path = window.location.pathname.replace(/\/+$/, '').toLowerCase();
    if (path === '/signup' || path === '/doctor/signup' || path === '/doctor-signup' || path.includes('/signup')) {
      return 'signup';
    }
    if (path === '/verification' || path.includes('/verification')) {
      return 'verification';
    }
    if (path === '/consultation' || path.includes('/consultation')) {
      return 'consultation';
    }
    return 'login';
  };

  const [currentScreen, setCurrentScreen] = useState(getInitialScreen);
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
    // If a previous doctor session flag exists in localStorage but
    // sessionStorage has no auth token, the user likely closed the tab
    // and reopened it — force logout (clear flag) so they aren't silently logged in.
    const sessionFlag = localStorage.getItem('doctorSessionActive');
    const token = sessionStorage.getItem('authToken');
    const role = sessionStorage.getItem('userRole');
    const savedPatient = localStorage.getItem('currentPatient');

    if (sessionFlag && !token) {
      // clear persistent markers and remain on login screen
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
    }
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
    let targetPath = '/';
    if (currentScreen === 'signup') targetPath = '/signup';
    else if (currentScreen === 'verification') targetPath = '/verification';
    else if (currentScreen === 'consultation') targetPath = '/consultation';
    else if (currentScreen === 'login') targetPath = '/login';

    const currentPath = window.location.pathname.replace(/\/+$/, '') || '/';
    if (currentPath.toLowerCase() !== targetPath.toLowerCase()) {
      window.history.replaceState(null, '', targetPath);
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