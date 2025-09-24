import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP server details
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # TLS port

# Sender and recipient details
sender_email = "sarfaraz.shaikh@ecosmob.com"
receiver_email = "sarfaraz.shaikh@ecosmob.com"
password = "nuxcyqsrxlmvzbbj"  # Use App Password for Gmail, not your real password

# Create the email
message = MIMEMultipart()
message["From"] = sender_email
message["To"] = receiver_email
message["Subject"] = "Test Email from Python"

# Email body
body = "Hello, this is a test email sent using Python SMTP."
message.attach(MIMEText(body, "plain"))

try:
    # Connect to SMTP server
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()  # Upgrade connection to TLS
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, message.as_string())
    print("✅ Email sent successfully!")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    server.quit()

