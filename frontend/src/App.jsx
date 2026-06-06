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
import LegalPage from './LegalPage';
import { FiPlus } from 'react-icons/fi';

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
    if (hashPath.includes('privacy')) {
      return 'privacy';
    }
    if (hashPath.includes('terms')) {
      return 'terms';
    }
    if (hashPath.includes('helpline')) {
      return 'helpline';
    }
    if (hashPath.includes('guidelines')) {
      return 'guidelines';
    }
    if (hashPath.includes('clinical-studies')) {
      return 'clinical-studies';
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
    if (path.includes('/privacy')) {
      return 'privacy';
    }
    if (path.includes('/terms')) {
      return 'terms';
    }
    if (path.includes('/helpline')) {
      return 'helpline';
    }
    if (path.includes('/guidelines')) {
      return 'guidelines';
    }
    if (path.includes('/clinical-studies')) {
      return 'clinical-studies';
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
  const [prevScreen, setPrevScreen] = useState('login');

  const navigateToLegal = (screen) => {
    if (!['privacy', 'terms', 'helpline', 'guidelines', 'clinical-studies'].includes(currentScreen)) {
      setPrevScreen(currentScreen);
    }
    setCurrentScreen(screen);
  };

  const isAuthenticated = () => {
    const token = sessionStorage.getItem('authToken');
    const role = sessionStorage.getItem('userRole');
    const sessionFlag = localStorage.getItem('doctorSessionActive');
    return Boolean(token && role === 'doctor' && sessionFlag === 'true');
  };

  const clearAuthAndRedirect = () => {
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('userRole');
    sessionStorage.removeItem('doctorName');
    sessionStorage.removeItem('doctorEmail');
    localStorage.removeItem('doctorSessionActive');
    localStorage.removeItem('currentPatient');
    setPatientData(null);
    setCurrentScreen('login');
  };

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
        title = 'DiabAssist Patient Information | AI Clinical Assistance Tool';
        break;
      case 'consultation':
        title = 'DiabAssist Clinical Consultation | AI Clinical Assistance Tool';
        break;
      case 'privacy':
        title = 'Privacy Statement | DiabAssist';
        break;
      case 'terms':
        title = 'Terms & Conditions | DiabAssist';
        break;
      case 'helpline':
        title = 'Helpline & Support | DiabAssist';
        break;
      case 'guidelines':
        title = 'Guidelines | DiabAssist';
        break;
      case 'clinical-studies':
        title = 'Clinical Studies | DiabAssist';
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

    const token = sessionStorage.getItem('authToken');
    const role = sessionStorage.getItem('userRole');
    const sessionFlag = localStorage.getItem('doctorSessionActive');
    const savedPatient = localStorage.getItem('currentPatient');

    if (token && role === 'doctor' && sessionFlag === 'true') {
      if (savedPatient) {
        setPatientData(JSON.parse(savedPatient));
        setCurrentScreen('consultation');
      } else {
        setCurrentScreen('verification');
      }
      return;
    }

    if (token && sessionFlag !== 'true') {
      sessionStorage.removeItem('authToken');
      sessionStorage.removeItem('userRole');
      sessionStorage.removeItem('doctorName');
      sessionStorage.removeItem('doctorEmail');
    }

    if (routeScreen === 'privacy' || routeScreen === 'terms' || routeScreen === 'helpline' || routeScreen === 'guidelines' || routeScreen === 'clinical-studies') {
      setCurrentScreen(routeScreen);
    } else {
      setCurrentScreen('login');
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleStorageEvent = (event) => {
      if (event.key === 'doctorSessionActive' && event.newValue !== 'true') {
        clearAuthAndRedirect();
      }
    };

    window.addEventListener('storage', handleStorageEvent);
    return () => window.removeEventListener('storage', handleStorageEvent);
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
    else if (currentScreen === 'privacy') targetHash = '#/privacy';
    else if (currentScreen === 'terms') targetHash = '#/terms';
    else if (currentScreen === 'helpline') targetHash = '#/helpline';
    else if (currentScreen === 'guidelines') targetHash = '#/guidelines';
    else if (currentScreen === 'clinical-studies') targetHash = '#/clinical-studies';
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
          <DoctorLogin onLoginSuccess={handleLoginSuccess} onNavigate={navigateToLegal} />
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
            onNavigate={navigateToLegal}
          />
        )}

        {currentScreen === 'consultation' && (
          <IntelliHealthInterface
            patientData={patientData}
            onBack={handleBackToVerification}
            onLogout={handleLogout}
          />
        )}

        {currentScreen === 'privacy' && (
          <LegalPage page="privacy" onBack={() => setCurrentScreen(prevScreen)} onNavigate={navigateToLegal} />
        )}

        {currentScreen === 'terms' && (
          <LegalPage page="terms" onBack={() => setCurrentScreen(prevScreen)} onNavigate={navigateToLegal} />
        )}

        {currentScreen === 'helpline' && (
          <LegalPage page="helpline" onBack={() => setCurrentScreen(prevScreen)} onNavigate={navigateToLegal} />
        )}

        {currentScreen === 'guidelines' && (
          <LegalPage page="guidelines" onBack={() => setCurrentScreen(prevScreen)} onNavigate={navigateToLegal} />
        )}

        {currentScreen === 'clinical-studies' && (
          <LegalPage page="clinical-studies" onBack={() => setCurrentScreen(prevScreen)} onNavigate={navigateToLegal} />
        )}
      </div>

      {/* Global footer — hidden on login since login has its own */}
      {!['login', 'privacy', 'terms', 'helpline'].includes(currentScreen) && (
        <footer
          className="global-footer"
          style={{
            padding: '12px 16px',
            textAlign: 'center',
            background: '#f8fafc',
            flexShrink: 0,
            borderTop: '1px solid #e2e8f0',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <div style={{ color: '#6b7280', fontSize: '11px', lineHeight: '1.4', marginBottom: currentScreen === 'consultation' ? '12px' : '8px' }}>
            This tool provides guideline-aligned suggestions only. The final diagnosis, treatment plan, and prescription are the sole responsibility of the licensed treating physician
          </div>

          {currentScreen === 'consultation' && (
            <div className="w-full max-w-[1800px] mx-auto flex items-center justify-between px-4 mb-4">
              <div className="flex items-center gap-3">
                <button onClick={() => navigateToLegal('guidelines')} className="px-8 py-2.5 bg-white border border-gray-200 rounded-xl font-bold text-gray-800 shadow-sm hover:bg-gray-50 text-sm">Guidelines</button>
                <button onClick={() => navigateToLegal('clinical-studies')} className="px-8 py-2.5 bg-white border border-gray-200 rounded-xl font-bold text-gray-800 shadow-sm hover:bg-gray-50 text-sm">Clinical Studies</button>
              </div>
              <button onClick={handleBackToVerification} className="px-8 py-2.5 bg-white border border-gray-200 rounded-xl font-bold text-gray-800 shadow-sm hover:bg-gray-50 text-sm flex items-center gap-2">
                <FiPlus size={16} /> Next Patient
              </button>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '4px' }}>
            <a href="#" onClick={(e) => { e.preventDefault(); navigateToLegal('privacy'); }} style={{ color: '#6b7280', textDecoration: 'none', fontSize: '11px' }}>Privacy Statement</a>
            <span style={{ color: '#d1d5db' }}>•</span>
            <a href="#" onClick={(e) => { e.preventDefault(); navigateToLegal('terms'); }} style={{ color: '#6b7280', textDecoration: 'none', fontSize: '11px' }}>Terms and Conditions</a>
            <span style={{ color: '#d1d5db' }}>•</span>
            <a href="#" onClick={(e) => { e.preventDefault(); navigateToLegal('helpline'); }} style={{ color: '#6b7280', textDecoration: 'none', fontSize: '11px' }}>Helpline</a>
          </div>
          <div style={{ color: '#374151', fontSize: '12px', fontWeight: 'bold' }}>
            Powered by Elements Interactive
          </div>
        </footer>
      )}

    </div>
  );
}

export default App;