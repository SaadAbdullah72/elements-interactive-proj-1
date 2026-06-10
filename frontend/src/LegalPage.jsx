import React from 'react';
import AppHeader from './AppHeader';
import { BG_IMG } from './DoctorLogin';

const FRONTEND_PDFS = [
  { name: '14. Children and Adolescents.pdf', path: '/guidelines/14. Children and Adolescents.pdf' },
  { name: '15. Management of Diabetes in Pregnancy.pdf', path: '/guidelines/15. Management of Diabetes in Pregnancy.pdf' },
  { name: '16. Diabetes Care in the Hospital.pdf', path: '/guidelines/16. Diabetes Care in the Hospital.pdf' },
];

const LegalPage = ({ page, onBack, onNavigate }) => {

  let title = '';
  let content = null;

  if (page === 'privacy') {
    title = 'Privacy Statement';
    content = (
      <div className="legal-content-wrapper">
        <section className="legal-section">
          <h3>1. Data Confidentiality & Protection</h3>
          <p>
            DiabAssist is dedicated to protecting the privacy and security of all medical professionals and their patients. In alignment with established health data protection standards (including HIPAA and GDPR principles), all clinical data processed through the DiabAssist application is treated with the highest degree of confidentiality.
          </p>
        </section>

        <section className="legal-section">
          <h3>2. Information We Process</h3>
          <p>
            We process the clinical metrics and parameters input by treating physicians during patient verification and clinical consultation. This includes:
          </p>
          <ul>
            <li>Physician authentication information (Name, Email, and Access Tokens).</li>
            <li>Anonymized patient profiles (Age, Year of Birth, Gender, and Medical Metrics).</li>
            <li>Clinical parameters (Disease Type, Conditions, and Current Medication Regimens).</li>
          </ul>
        </section>

        <section className="legal-section">
          <h3>3. Use of Clinical Data</h3>
          <p>
            The metrics collected are processed in real-time solely to generate evidence-based clinical guidance and decision support. DiabAssist does not sell, rent, or distribute patient data or medical records to third-party advertisers, insurance providers, or unauthorized entities.
          </p>
        </section>

        <section className="legal-section">
          <h3>4. Encryption & Session Security</h3>
          <p>
            All connection streams between the frontend application and the backend clinical inference engines are encrypted using Industry Standard SSL/TLS protocols. Access tokens are kept securely in temporary session storage, which is automatically purged when the user logs out or closes the browser window.
          </p>
        </section>

        <section className="legal-section">
          <h3>5. Access and Rights</h3>
          <p>
            Licensed physicians retain full ownership and discretion over the inputs submitted during a session. If you have any inquiries regarding data protection policies or server configuration compliance, please contact our Data Protection Officer at <span className="highlight-text">dpo@diabassist.com</span>.
          </p>
        </section>
      </div>
    );
  } else if (page === 'terms') {
    title = 'Terms & Conditions';
    content = (
      <div className="legal-content-wrapper">
        <section className="legal-section">
          <h3>1. Agreement & Scope</h3>
          <p>
            Please read these Terms and Conditions carefully before using DiabAssist. By accessing or using the platform, you (the licensed treating physician) agree to be bound by the terms set forth in this Agreement. If you do not agree to these terms, you must immediately cease using the application.
          </p>
        </section>

        <section className="legal-section">
          <h3>2. Clinical Decision Support Disclaimer</h3>
          <p>
            DiabAssist is an AI-powered clinical assistance tool designed to provide guideline-aligned suggestions based on deep learning models and evidence-based medicine. It is a decision support system and is NOT a medical device, nor is it a substitute for professional clinical judgment, diagnosis, or treatment.
          </p>
        </section>

        <section className="legal-section">
          <h3>3. Physician Responsibility</h3>
          <p>
            The final diagnosis, treatment plan, and prescription are the sole and absolute responsibility of the licensed treating physician. The suggestions provided by this tool must be independently verified by the physician before any clinical actions are taken.
          </p>
        </section>

        <section className="legal-section">
          <h3>4. Account Security & Integrity</h3>
          <p>
            You are responsible for maintaining the confidentiality of your credentials and access tokens. You agree to notify the system administrator immediately of any unauthorized use of your account. HealthApps SDN BHD shall not be liable for any unauthorized access or breach of physician-patient confidentiality arising from poor credential management.
          </p>
        </section>

        <section className="legal-section">
          <h3>5. Limitation of Liability</h3>
          <p>
            In no event shall HealthApps, its developers, clinical advisers, or affiliates be held liable for any direct, indirect, incidental, or consequential damages (including, without limitation, medical malpractice, patient injury, or loss of life) arising out of the use or inability to use this decision-support system.
          </p>
        </section>
      </div>
    );
  } else if (page === 'guidelines') {
    title = 'Guidelines';
    content = (
      <div className="legal-content-wrapper">
        <section className="legal-section">
          <h3>Clinical Guideline PDFs</h3>
          <p>
            Select any PDF below to download it directly to your device. These are the guideline documents available for review on this system.
          </p>
        </section>

        <section className="legal-section">
          <div style={{ display: 'grid', gap: '12px' }}>
            {FRONTEND_PDFS.map((pdf) => (
              <a
                key={pdf.name}
                href={pdf.path}
                download={pdf.name}
                style={{
                  display: 'block',
                  padding: '14px 16px',
                  border: '1px solid #dbe4f0',
                  borderRadius: '14px',
                  background: 'linear-gradient(135deg, #ffffff 0%, #f8fbff 100%)',
                  color: '#0f172a',
                  textDecoration: 'none',
                  boxShadow: '0 8px 18px rgba(15, 23, 42, 0.08)',
                }}
              >
                <div style={{ fontWeight: 700, fontSize: '15px', marginBottom: '4px' }}>{pdf.name}</div>
                <div style={{ color: '#475569', fontSize: '12px' }}>
                  Direct frontend PDF • Click to download
                </div>
              </a>
            ))}
          </div>
        </section>
      </div>
    );
  } else if (page === 'clinical-studies') {
    title = 'Clinical Studies';
    content = (
      <div className="legal-content-wrapper">
        <section className="legal-section">
          <h3>Clinical Study PDFs</h3>
          <p>Download the available PDF documents directly from this page.</p>
        </section>

        <section className="legal-section">
          <div style={{ display: 'grid', gap: '12px' }}>
            {FRONTEND_PDFS.map((pdf) => (
              <a
                key={pdf.name}
                href={pdf.path}
                download={pdf.name}
                style={{
                  display: 'block',
                  padding: '14px 16px',
                  border: '1px solid #dbe4f0',
                  borderRadius: '14px',
                  background: 'linear-gradient(135deg, #ffffff 0%, #f8fbff 100%)',
                  color: '#0f172a',
                  textDecoration: 'none',
                  boxShadow: '0 8px 18px rgba(15, 23, 42, 0.08)',
                }}
              >
                <div style={{ fontWeight: 700, fontSize: '15px', marginBottom: '4px' }}>{pdf.name}</div>
                <div style={{ color: '#475569', fontSize: '12px' }}>
                  Direct frontend PDF • Click to download
                </div>
              </a>
            ))}
          </div>
        </section>
      </div>
    );
  } else if (page === 'product-info') {
    title = 'Product Information';
    content = (
      <div className="legal-content-wrapper">
        <section className="legal-section">
          <h3>About DiabAssist — Product Overview</h3>
          <p>
            This placeholder page provides product information for the clinic-facing DiabAssist application. Replace this content with the official product details, features, and deployment notes.
          </p>
        </section>

        <section className="legal-section">
          <h3>Key Features (Dummy Data)</h3>
          <ul>
            <li>AI-assisted clinical decision support</li>
            <li>Guideline-aligned recommendations</li>
            <li>Session persistence and PDF export</li>
          </ul>
        </section>

        <section className="legal-section">
          <h3>Next Steps</h3>
          <p>
            Replace this placeholder with the official product brochure, integration instructions, or marketing copy as required.
          </p>
        </section>
      </div>
    );
  } else if (page === 'helpline') {
    title = 'Helpline & Support';
    content = (
      <div className="legal-content-wrapper">
        <section className="legal-section">
          <h3>1. Technical & Application Support</h3>
          <p>
            If you experience technical issues, authentication errors, or database connectivity problems, please reach out to our technical support desk:
          </p>
          <div className="support-card">
            <p><strong>📧 Support Email:</strong> support@diabassist.com</p>
            <p><strong>📞 Technical Support Helpline:</strong> +1 (800) 555-0199</p>
            <p><strong>⏱️ Availability:</strong> 24/7 technical operations desk</p>
          </div>
        </section>

        <section className="legal-section">
          <h3>2. Emergency Medical Disclaimer</h3>
          <p>
            <strong>IMPORTANT:</strong> This application is NOT intended for acute medical emergencies. If your patient is experiencing a medical crisis, diabetic ketoacidosis (DKA), severe hypoglycemia, or other life-threatening conditions, please contact your local emergency services immediately:
          </p>
          <div className="emergency-box">
            <p>🚨 <strong>Call local emergency helpline:</strong> 1122 / 911 / 999</p>
          </div>
        </section>

        <section className="legal-section">
          <h3>3. Frequently Asked Questions (FAQs)</h3>
          <div className="faq-item">
            <h4>Q: How is patient age calculated?</h4>
            <p>A: The system automatically calculates patient age in real-time based on the Year of Birth input, ensuring accuracy and saving clinic entry time.</p>
          </div>
          <div className="faq-item">
            <h4>Q: Can I add multiple medications?</h4>
            <p>A: Yes, you can add unlimited medications under the Add Patient panel by clicking the 'Add Medication' button to represent a patient's exact current regimen.</p>
          </div>
          <div className="faq-item">
            <h4>Q: What should I do if the AI suggestions do not load?</h4>
            <p>A: Ensure you have an active network connection to the backend FastAPI server. If the issue persists, refresh the page to restart the session securely.</p>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="legal-page-wrapper">
      <style>{`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        .legal-page-wrapper {
          font-family: 'Myriad Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          min-height: 100vh;
          width: 100%;
          display: flex;
          flex-direction: column;
          background: #ffffff;
          position: relative;
        }

        /* ── HERO ── */
        .legal-hero {
          position: relative;
          height: 150px;
          width: 100%;
          overflow: visible;
          flex-shrink: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        }

        .legal-hero-bg {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: center center;
          display: block;
          z-index: 1;
        }

        /* Go Back Button */
        .go-back-btn {
          position: absolute;
          top: 16px;
          right: 32px;
          z-index: 10;
          background: linear-gradient(to right, #ec4899, #f43f5e);
          color: white;
          font-size: 13px;
          font-weight: 600;
          padding: 6px 20px;
          border: none;
          border-radius: 9999px;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(244, 63, 94, 0.3);
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .go-back-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(244, 63, 94, 0.45);
          opacity: 0.95;
        }

        /* Pill shaped banner title */
        .legal-title-pill {
          background: #ffffff;
          border-radius: 9999px;
          padding: 8px 30px;
          font-size: 20px;
          font-weight: 700;
          color: #1f2937;
          display: inline-block;
          text-align: center;
          box-shadow: 0 4px 15px rgba(0,0,0,0.15);
          z-index: 2;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          border: 1px solid rgba(0, 0, 0, 0.05);
        }

        /* ── CONTENT CARD ── */
        .legal-card-container {
          width: 100%;
          max-width: 1000px;
          margin: -30px auto 30px;
          padding: 0 24px;
          position: relative;
          z-index: 5;
        }

        .legal-card {
          background: #ffffff;
          border-radius: 20px;
          box-shadow: 0 20px 40px rgba(0,0,0,0.08);
          padding: 30px 40px;
          border: 1px solid #f3f4f6;
        }

        .legal-content-wrapper {
          color: #374151;
          line-height: 1.6;
          font-size: 14px;
        }

        .legal-section {
          margin-bottom: 20px;
        }

        .legal-section:last-child {
          margin-bottom: 0;
        }

        .legal-section h3 {
          color: #1f2937;
          font-size: 16px;
          font-weight: 600;
          margin-bottom: 8px;
          border-bottom: 1px solid #f3f4f6;
          padding-bottom: 6px;
        }

        .legal-section p {
          margin-bottom: 8px;
        }

        .legal-section ul {
          margin-left: 24px;
          margin-bottom: 8px;
        }

        .legal-section li {
          margin-bottom: 4px;
        }

        .highlight-text {
          color: #8b5cf6;
          font-weight: 600;
        }

        .support-card {
          background: #f9fafb;
          border-left: 4px solid #8b5cf6;
          padding: 12px 16px;
          border-radius: 0 12px 12px 0;
          margin-top: 12px;
        }

        .support-card p {
          margin-bottom: 4px;
        }

        .support-card p:last-child {
          margin-bottom: 0;
        }

        .emergency-box {
          background: #fee2e2;
          border-left: 4px solid #f43f5e;
          padding: 12px 16px;
          border-radius: 0 12px 12px 0;
          color: #991b1b;
          font-weight: 500;
        }

        .faq-item {
          margin-bottom: 16px;
          background: #f9fafb;
          padding: 14px;
          border-radius: 12px;
        }

        .faq-item h4 {
          font-size: 14px;
          color: #1f2937;
          margin-bottom: 4px;
          font-weight: 600;
        }

        .faq-item p {
          margin-bottom: 0;
          font-size: 13px;
          color: #4b5563;
        }

        /* ── FOOTER INSIDE CARD ── */
        .legal-footer {
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #e5e7eb;
          text-align: center;
        }

        .legal-footer-links {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 12px;
          margin-bottom: 10px;
          flex-wrap: wrap;
        }

        .legal-footer-links a {
          color: #6b7280;
          font-size: 13px;
          text-decoration: none;
          font-weight: 500;
          transition: color 0.2s;
        }

        .legal-footer-links a:hover {
          color: #8b5cf6;
        }

        .legal-footer-links span {
          color: #d1d5db;
        }

        .legal-disclaimer {
          color: #9ca3af;
          font-size: 11px;
          line-height: 1.4;
          max-width: 800px;
          margin: 0 auto;
        }

        /* Responsive Styles */
        @media (max-width: 768px) {
          .legal-hero {
            height: 140px;
          }
          .go-back-btn {
            top: 12px;
            right: 12px;
            padding: 6px 16px;
            font-size: 12px;
          }
          .legal-title-pill {
            font-size: 16px;
            padding: 6px 20px;
            margin-top: 10px;
          }
          .legal-card {
            padding: 16px;
            border-radius: 16px;
          }
          .legal-card-container {
            margin-top: -20px;
          }
          .legal-section h3 {
            font-size: 15px;
          }
        }
      `}</style>

      <AppHeader />

      {/* Hero background area */}
      <section className="legal-hero">
        <img src={BG_IMG} alt="space background" className="legal-hero-bg" />
        <button className="go-back-btn" onClick={onBack}>
          ← Go Back
        </button>
        <div className="legal-title-pill">
          {title}
        </div>
      </section>

      {/* Main text content wrapper card */}
      <div className="legal-card-container">
        <div className="legal-card">
          {content}

          {/* Footer content links */}
          <footer className="legal-footer">
            <div className="legal-footer-links">
              <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('privacy'); }}>Privacy Statement</a>
              <span>•</span>
              <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('terms'); }}>Terms and Conditions</a>
              <span>•</span>
              <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('helpline'); }}>Helpline</a>
            </div>
            <div className="legal-disclaimer">
              This tool provides guideline-aligned suggestions only. The final diagnosis, treatment plan, and prescription are the sole responsibility of the licensed treating physician
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
};

export default LegalPage;
