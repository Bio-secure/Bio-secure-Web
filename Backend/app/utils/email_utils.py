import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import traceback
from dotenv import load_dotenv
import datetime
import pytz # Import pytz for timezone awareness, especially good for timestamps

load_dotenv() # Load environment variables

# Email Configuration - Load from environment variables
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587)) # Default to 587 for TLS
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def send_authentication_report_email(
    customer_email: str,
    customer_name: str,
    biometric_type: str,
    is_success: bool,
    details: dict
):
    if not all([EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, SENDER_EMAIL]):
        print("ERROR: Email configuration missing. Cannot send email report.")
        return

    subject = f"Authentication {'Success' if is_success else 'Failed'} Notification"
    
    # Get current time in a user-friendly timezone (e.g., UTC or your local timezone)
    # Using pytz for robust timezone handling
    local_timezone = pytz.timezone('Asia/Bangkok') # Example: Set to your local timezone
    attempt_time_utc = datetime.datetime.now(pytz.utc)
    attempt_time_local = attempt_time_utc.astimezone(local_timezone)
    formatted_time = attempt_time_local.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    status_message = "successful" if is_success else "unsuccessful"
    status_color = "color: #28a745;" if is_success else "color: #dc3545;" # Green for success, red for failure

    # Build the email body using HTML for better formatting
    html_body = f"""
    <html>
    <head></head>
    <body>
        <p>Dear {customer_name},</p>
        <p>This is an automated notification regarding a recent biometric authentication attempt on your account.</p>
        
        <p><strong>Authentication Status:</strong> <span style="{status_color} font-weight: bold;">{status_message.upper()}</span></p>
        <p><strong>Biometric Type:</strong> {biometric_type.capitalize()} Scan</p>
        <p><strong>Attempt Time:</strong> {formatted_time}</p>
        <p><strong>Transaction Type:</strong> {details.get('transactiontype')}</p>
        
        <h3>Details:</h3>
        <ul>
            <li><strong>Message:</strong> {details.get('message', 'N/A')}</li>
            {f"<li><strong>Distance:</strong> {details.get('distance', 'N/A'):.4f}</li>" if 'distance' in details else ''}
            {f"<li><strong>Similarity:</strong> {details.get('face_distance', 'N/A'):.4f}</li>" if 'face_distance' in details else ''}
            {f"<li><strong>Matched User ID:</strong> {details.get('matched_user_id', 'N/A')}</li>" if 'matched_user_id' in details else ''}
            {f"<li><strong>Similarity:</strong> {details['iris_simiarity']:.4f}</li>" if isinstance(details.get('iris_simiarity'), (float, int)) else ''}
            {f"<li><strong>Reason:</strong> {details.get('detail', 'N/A')}</li>" if 'detail' in details else ''}
        </ul>

        <p>If you did not initiate this authentication attempt, please contact support immediately.</p>
        <p>Thank you,</p>
        <p>Your Biometric Security Team</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = customer_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    try:
        # Connect to the SMTP server
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()  # Upgrade connection to TLS (secure)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"SUCCESS: Authentication report email sent to {customer_email}")
    except Exception as e:
        print(f"ERROR: Failed to send authentication report email to {customer_email}: {e}")
        traceback.print_exc() # Print full traceback for debugging

