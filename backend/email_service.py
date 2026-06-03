# email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Email configuration and delivery helpers.
#
# Notes:
# - All credentials are read from environment variables. Never commit
#   credentials to source control. In development the code prints
#   verification/reset URLs instead of sending emails when the password
#   is missing.
# - Avoid logging full secrets (passwords) to prevent accidental leaks.
#   The code should only indicate presence/absence or masked lengths.
#
# If you enable real email sending, set `EMAIL_HOST_USER` and
# `EMAIL_HOST_PASSWORD` in your environment or .env file.
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "haseebmine24@gmail.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Elements Interactive")


def get_email_html(name: str, verification_url: str) -> str:
    """
    Generate professional HTML email for verification.
    """
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Account</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f7fa;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: #c084fc;
            padding: 40px 30px;
            text-align: center;
        }}
        .logo {{
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 10px;
        }}
        .logo-icon {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
        .tagline {{
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .greeting {{
            font-size: 24px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 20px;
        }}
        .message {{
            font-size: 16px;
            color: #4a5568;
            margin-bottom: 30px;
            line-height: 1.8;
        }}
        .button-container {{
            text-align: center;
            margin: 35px 0;
        }}
        .verify-button {{
            display: inline-block;
            background: #c084fc;
            color: #ffffff;
            text-decoration: none;
            padding: 16px 40px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 4px 14px rgba(102, 126, 234, 0.4);
        }}
        .verify-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }}
        .button-text {{
            color: #ffffff;
            text-decoration: none;
        }}
        .info-box {{
            background: #fefce8;
            border-left: 4px solid #a855f7;
            padding: 20px;
            border-radius: 6px;
            margin: 25px 0;
        }}
        .info-box p {{
            font-size: 14px;
            color: #718096;
            margin: 0;
        }}
        .security-note {{
            background: #fff5f5;
            border: 1px solid #feb2b2;
            padding: 15px;
            border-radius: 6px;
            margin-top: 25px;
        }}
        .security-note p {{
            font-size: 13px;
            color: #c53030;
            margin: 0;
        }}
        .footer {{
            background: #f7fafc;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}
        .footer-text {{
            font-size: 14px;
            color: #718096;
            margin-bottom: 10px;
        }}
        .footer-links {{
            margin-top: 15px;
        }}
        .footer-links a {{
            color: #9333ea;
            text-decoration: none;
            margin: 0 10px;
            font-size: 13px;
        }}
        .copyright {{
            margin-top: 20px;
            font-size: 12px;
            color: #a0aec0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo-icon">🏥</div>
            <div class="logo">Elements Interactive</div>
            <div class="tagline">Your Trusted Medical Safety Partner</div>
        </div>

        <!-- Content -->
        <div class="content">
            <div class="greeting">Hello {name},</div>
            
            <div class="message">
                Thank you for registering with <strong>Elements Interactive</strong>.
                <br><br>
                To activate your account and begin using our advanced medical validation system, 
                please verify your email address by clicking the button below.
            </div>

            <!-- Verify Button -->
            <div class="button-container">
                <a href="{verification_url}" class="verify-button">
                    <span class="button-text">✓ Verify My Account</span>
                </a>
            </div>

            <!-- Info Box -->
            <div class="info-box">
                <p>
                    <strong>What happens next?</strong><br>
                    After verification, you'll have access to your personal medical dashboard where you can:
                    <ul style="margin-top: 10px; padding-left: 20px;">
                        <li>Submit prescriptions for AI-powered safety analysis</li>
                        <li>View your medical history and past analyses</li>
                        <li>Manage your profile and preferences</li>
                    </ul>
                </p>
            </div>

            <!-- Security Note -->
            <div class="security-note">
                <p>
                    🔒 <strong>Security Notice:</strong> If you did not create this account, 
                    you can safely ignore this email. No changes have been made to your account.
                </p>
            </div>

            <div class="message" style="margin-top: 30px;">
                Best Regards,<br>
                <strong>The Elements Interactive Team</strong>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <div class="footer-text">
                This email was sent to verify your account registration.
            </div>
            <div class="footer-links">
                <a href="#">Privacy Policy</a> | 
                <a href="#">Terms of Service</a> | 
                <a href="#">Contact Support</a>
            </div>
            <div class="copyright">
                © 2026 {EMAIL_FROM_NAME}. All rights reserved.
            </div>
        </div>
    </div>
</body>
</html>
    """
    return html.strip()


async def send_verification_email(email: str, name: str, verification_url: str) -> bool:
    """
    Send verification email to user.
    
    Args:
        email: Recipient email address
        name: Recipient name
        verification_url: URL for email verification
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not EMAIL_HOST_PASSWORD or EMAIL_HOST_PASSWORD == "your-app-password-here":
        print("⚠️  Email password not configured. Skipping email send (development mode).")
        print(f"🔗 Verification URL for {email}: {verification_url}")
        return True
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify Your Account – Elements Interactive"
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg["To"] = email

        # Generate HTML content
        html_content = get_email_html(name, verification_url)
        
        # Create plain text version
        text_content = f"""
Hello {name},

Thank you for registering with Elements Interactive.

To activate your account and begin using the system, please verify your email address 
by clicking the link below:

{verification_url}

If you did not create this account, you can safely ignore this email.

Best Regards,
{EMAIL_FROM_NAME} Team
        """

        # Attach both versions
        part_text = MIMEText(text_content, "plain")
        part_html = MIMEText(html_content, "html")
        msg.attach(part_text)
        msg.attach(part_html)

        # Send email
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(EMAIL_FROM, email, msg.as_string())

        print(f"✅ Verification email sent successfully to {email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {str(e)}")
        print(f"   Check your email credentials in .env file")
        print(f"   EMAIL_HOST_USER: {EMAIL_HOST_USER}")
        print(f"   PASSWORD LENGTH: {len(EMAIL_HOST_PASSWORD)} chars")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error occurred: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def send_password_reset_email(email: str, name: str, reset_url: str) -> bool:
    """
    Send password reset email to user.

    Args:
        email: Recipient email address
        name: Recipient name
        reset_url: URL for password reset

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 40px auto; padding: 30px; background: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: #c084fc; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .button {{ display: inline-block; background: #a855f7; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div style="padding: 30px;">
            <p>Hello {name},</p>
            <p>We received a request to reset your password for Elements Interactive.</p>
            <p>Click the button below to reset your password:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset My Password</a>
            </p>
            <p>This link will expire in 1 hour.</p>
            <p><strong>Didn't request this?</strong> If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
        </div>
        <div class="footer">
            <p>© 2026 Elements Interactive. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
    """

    if not EMAIL_HOST_PASSWORD or EMAIL_HOST_PASSWORD == "your-app-password-here":
        print(f"Password reset URL for {email}: {reset_url}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Password Reset Request – Elements Interactive"
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg["To"] = email

        part_html = MIMEText(html_content, "html")
        msg.attach(part_html)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(EMAIL_FROM, email, msg.as_string())

        print(f"Password reset email sent successfully to {email}")
        return True

    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")
        return False


def send_diagnosis_email(patient_email: str, patient_name: str, doctor_name: str, 
                        diagnosis_summary: str, clinic_name: str = "DiabAssist Clinic") -> bool:
    """
    Send diagnosis notification email to patient when doctor performs diagnosis.

    Args:
        patient_email: Patient's email address
        patient_name: Patient's name
        doctor_name: Doctor's name who performed the diagnosis
        diagnosis_summary: Brief summary of the diagnosis/analysis
        clinic_name: Name of the clinic/platform

    Returns:
        bool: True if email sent successfully
    """
    print(f"\n📤 send_diagnosis_email called:")
    print(f"   - To: {patient_email}")
    print(f"   - Patient: {patient_name}")
    print(f"   - Doctor: {doctor_name}")
    print(f"   - EMAIL_HOST_USER: {EMAIL_HOST_USER}")
    print(f"   - EMAIL_HOST_PASSWORD length: {len(EMAIL_HOST_PASSWORD) if EMAIL_HOST_PASSWORD else 0}")
    print(f"   - EMAIL_FROM: {EMAIL_FROM}")
    
    if not EMAIL_HOST_PASSWORD or EMAIL_HOST_PASSWORD == "your-app-password-here":
        print(f"⚠️  DEVELOPMENT MODE: Email password not configured!")
        print(f"   Diagnosis email WOULD be sent to: {patient_email}")
        print(f"   Doctor: {doctor_name}")
        print(f"   Summary preview: {diagnosis_summary[:100]}...")
        return True

    try:
        print(f"\n🔄 Attempting to connect to SMTP server...")
        print(f"   - SMTP Host: {EMAIL_HOST}")
        print(f"   - SMTP Port: {EMAIL_PORT}")
        print(f"   - Using TLS: {EMAIL_USE_TLS}")
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your Medical Consultation Report - DiabAssist"
        msg["From"] = f"DiabAssist <{EMAIL_FROM}>"
        msg["To"] = patient_email

        # Create plain text version
        text_content = f"""
Dear {patient_name},

Your healthcare provider has completed a medical consultation and analysis.

Consulting Doctor: {doctor_name}
Clinic: {clinic_name}
Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

MEDICAL ANALYSIS SUMMARY:
{diagnosis_summary}

What's Next?
Please review the analysis summary. If you have any questions or concerns, please contact your healthcare provider.

This email contains private medical information. If you did not expect to receive this, please contact our support team immediately.

Wishing you good health,
The DiabAssist Team

© 2026 DiabAssist. All rights reserved.
        """

        part_text = MIMEText(text_content, "plain")
        msg.attach(part_text)

        # Send email
        print(f"\n📡 Connecting to SMTP server...")
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                print(f"   - Starting TLS...")
                server.starttls()
            print(f"   - Logging in with user: {EMAIL_HOST_USER}")
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            print(f"   - Login successful! Sending email...")
            server.sendmail(EMAIL_FROM, patient_email, msg.as_string())
            print(f"   - Email sent successfully!")

        print(f"\n✅ Diagnosis notification email sent successfully to {patient_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ SMTP Authentication failed: {str(e)}")
        print(f"   ⚠️  Your Gmail App Password is INCORRECT or INVALID")
        print(f"   👉 Please check: https://myaccount.google.com/apppasswords")
        print(f"   👉 Generate a NEW 16-character app password")
        print(f"   👉 Update your .env file: EMAIL_HOST_PASSWORD=your-new-password")
        return False
    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Failed to send diagnosis email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def send_registration_email(patient_email: str, patient_name: str, user_id: str, role: str = "patient", specialization: str = None) -> bool:
    """
    Send welcome email to newly registered patient or doctor.

    Args:
        patient_email: User's email address
        patient_name: User's name
        user_id: Generated user ID
        role: User role (patient or doctor)
        specialization: Doctor's specialization (for doctors only)

    Returns:
        bool: True if email sent successfully
    """
    if not EMAIL_HOST_PASSWORD or EMAIL_HOST_PASSWORD == "your-app-password-here":
        print(f"Registration email would be sent to {patient_email} (development mode)")
        print(f"User ID: {user_id}, Role: {role}")
        return True
    
    # Generate email content based on role
    if role == "doctor":
        subject = "Welcome to Elements Interactive - Doctor Dashboard"
        greeting = f"Welcome, Dr. {patient_name}!"
        welcome_text = f"Your doctor account has been successfully created! Your unique Doctor ID is:"
        features = """
                        <li>Access comprehensive patient management dashboard</li>
                        <li>View and manage patient medical records</li>
                        <li>AI-powered prescription safety analysis for your patients</li>
                        <li>Generate detailed medical reports</li>
                        <li>Track patient consultations and history</li>
                    """
    else:
        subject = "Welcome to Elements Interactive - Your Patient ID Inside"
        greeting = f"Hello {patient_name},"
        welcome_text = "Your patient account has been successfully created! Your unique Patient ID is:"
        features = """
                        <li>Get AI-powered prescription safety analysis</li>
                        <li>Track your medical history and consultations</li>
                        <li>View personalized health analytics</li>
                        <li>Download detailed medical reports</li>
                    """
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Elements Interactive</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #fefce8; }}
        .container {{ max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); }}
        .header {{ background: #c084fc; padding: 40px 30px; text-align: center; }}
        .logo {{ font-size: 32px; font-weight: bold; color: #ffffff; margin-bottom: 10px; }}
        .content {{ padding: 40px 30px; }}
        .info-box {{ background: #fefce8; border-left: 4px solid #a855f7; padding: 20px; border-radius: 6px; margin: 25px 0; }}
        .id-box {{ background: #fff5f5; border: 2px dashed #fc8181; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; }}
        .id-number {{ font-size: 24px; font-weight: bold; color: #c53030; font-family: monospace; letter-spacing: 2px; }}
        .footer {{ background: #fefce8; padding: 30px; text-align: center; border-top: 1px solid #e9d5ff; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="font-size: 48px;">🏥</div>
            <div class="logo">Welcome to Elements Interactive</div>
        </div>
        <div class="content">
            <h2 style="color: #2d3748; margin-bottom: 15px;">{greeting}</h2>
            <p style="color: #4a5568; margin-bottom: 20px;">
                {welcome_text}
            </p>
            <div class="id-box">
                <div style="color: #718096; margin-bottom: 10px;">Your ID</div>
                <div class="id-number">{user_id}</div>
            </div>
            <div class="info-box">
                <p><strong>What you can do now:</strong></p>
                <ul style="margin-top: 10px; padding-left: 20px; color: #4a5568;">
                    {features}
                </ul>
            </div>
            <p style="color: #718096; margin-top: 25px;">
                Keep your ID safe. You'll need it to access your dashboard.
            </p>
        </div>
        <div class="footer">
            <p style="color: #718096; font-size: 14px;">© 2026 Elements Interactive. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
    """
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg["To"] = patient_email
        
        part_html = MIMEText(html_content, "html")
        msg.attach(part_html)
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(EMAIL_FROM, patient_email, msg.as_string())
        
        print(f"Welcome email sent to {patient_email}")
        return True
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")
        return False