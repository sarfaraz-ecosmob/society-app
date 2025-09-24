from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import smtplib
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

# File Upload Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'txt', 'xlsx', 'xls'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# MySQL Database Configuration
# Update these values according to your MySQL setup
DB_USERNAME = 'root'
DB_PASSWORD = 'root'  # Change this to your MySQL password
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'society_app'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_member = db.Column(db.Boolean, default=False)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    house = db.relationship('House', backref=db.backref('users', lazy=True))

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_number = db.Column(db.String(20), nullable=False)
    building_wing = db.Column(db.String(50), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    number_of_occupants = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Owner/Tenant
    emergency_contact = db.Column(db.String(15), nullable=True)
    vehicle_number = db.Column(db.String(20), nullable=True)
    parking_slot = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    house = db.relationship('House', backref=db.backref('members', lazy=True))

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    month_year = db.Column(db.String(10), nullable=False)  # Format: YYYY-MM
    amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='Pending')  # Paid/Pending/Partial
    payment_date = db.Column(db.Date, nullable=True)
    receipt_number = db.Column(db.String(20), nullable=True)
    payment_method = db.Column(db.String(20), default='Cash')  # Cash/Online - for future payment gateway
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    house = db.relationship('House', backref=db.backref('maintenance_records', lazy=True))

class Fund(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_amount = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def get_fund(cls):
        fund = cls.query.first()
        if not fund:
            fund = cls(total_amount=0.0, last_updated=datetime.utcnow)
            db.session.add(fund)
            db.session.commit()
        return fund

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # Electricity, Maintenance, Security, etc.
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    creator = db.relationship('User', backref=db.backref('expenses', lazy=True))

class NotificationSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(20), nullable=False)  # smtp, whatsapp
    is_active = db.Column(db.Boolean, default=True)
    
    # SMTP Settings
    smtp_server = db.Column(db.String(100), nullable=True)
    smtp_port = db.Column(db.Integer, nullable=True)
    smtp_username = db.Column(db.String(100), nullable=True)
    smtp_password = db.Column(db.String(200), nullable=True)
    smtp_use_tls = db.Column(db.Boolean, default=True)
    
    # WhatsApp Settings
    whatsapp_api_url = db.Column(db.String(200), nullable=True)
    whatsapp_api_key = db.Column(db.String(200), nullable=True)
    whatsapp_phone_number = db.Column(db.String(20), nullable=True)
    
    # General Settings
    sender_name = db.Column(db.String(100), nullable=True)
    sender_email = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_active_settings(cls):
        return cls.query.filter_by(is_active=True).first()
    
    @classmethod
    def get_by_type(cls, notification_type):
        return cls.query.filter_by(notification_type=notification_type, is_active=True).first()

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # plumbing, electric, security, other
    status = db.Column(db.String(20), default='Open')  # Open, In Progress, Resolved
    priority = db.Column(db.String(10), default='Medium')  # Low, Medium, High, Urgent
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    creator = db.relationship('User', backref=db.backref('complaints', lazy=True))
    house = db.relationship('House', backref=db.backref('complaints', lazy=True))

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    document_type = db.Column(db.String(50), nullable=False)  # Legal, Financial, Meeting Minutes, etc.
    file_name = db.Column(db.String(255), nullable=False)
    original_file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    file_extension = db.Column(db.String(10), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    uploader = db.relationship('User', backref=db.backref('documents', lazy=True))
    
    @property
    def file_size_formatted(self):
        """Return file size in human readable format"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_image(self):
        """Check if file is an image"""
        return self.file_extension.lower() in ['jpg', 'jpeg', 'png', 'gif']
    
    @property
    def is_pdf(self):
        """Check if file is PDF"""
        return self.file_extension.lower() == 'pdf'

# File Upload Helper Functions
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_icon(extension):
    """Get appropriate icon for file type"""
    ext = extension.lower()
    if ext in ['pdf']:
        return 'fas fa-file-pdf text-danger'
    elif ext in ['jpg', 'jpeg', 'png', 'gif']:
        return 'fas fa-file-image text-success'
    elif ext in ['doc', 'docx']:
        return 'fas fa-file-word text-primary'
    elif ext in ['xls', 'xlsx']:
        return 'fas fa-file-excel text-success'
    elif ext in ['txt']:
        return 'fas fa-file-alt text-secondary'
    else:
        return 'fas fa-file text-muted'

# Make helper functions available in templates
app.jinja_env.globals.update(get_file_icon=get_file_icon)

# Notification Service Functions
class NotificationService:
    @staticmethod
    def send_email_receipt(settings, recipient_email, recipient_name, maintenance_record):
        """Send maintenance receipt via email using the working method"""
        try:
            # Validate required fields
            if not settings.smtp_server or not settings.smtp_server.strip():
                return False, "SMTP server address is required"
            
            if not settings.smtp_port:
                return False, "SMTP port is required"
            
            if not settings.smtp_username or not settings.smtp_username.strip():
                return False, "SMTP username is required"
            
            if not settings.smtp_password or not settings.smtp_password.strip():
                return False, "SMTP password is required"
            
            # Clean server address
            smtp_server = settings.smtp_server.strip()
            if smtp_server.startswith('.'):
                return False, "SMTP server address cannot start with a dot"
            
            # Create the email (same structure as your working code)
            msg = MIMEMultipart()
            msg['From'] = settings.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"Maintenance Receipt - {maintenance_record.house.house_number}"
            
            # Create email body
            body = f"""
Dear {recipient_name},

Thank you for your payment. Please find your maintenance receipt details below:

Receipt Number: {maintenance_record.receipt_number}
House: {maintenance_record.house.house_number} - {maintenance_record.house.building_wing}
Month/Year: {maintenance_record.month_year}
Amount Paid: ₹{maintenance_record.paid_amount:.2f}
Payment Date: {maintenance_record.payment_date.strftime('%d/%m/%Y')}
Payment Method: {maintenance_record.payment_method}

Thank you for your timely payment.

Best regards,
{settings.sender_name}
Society Management
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Use the exact same method as your working smtp-test.py
            server = smtplib.SMTP(smtp_server, settings.smtp_port)
            
            if settings.smtp_use_tls:
                server.starttls()
            
            server.login(settings.smtp_username.strip(), settings.smtp_password.strip())
            server.sendmail(settings.sender_email, recipient_email, msg.as_string())
            server.quit()
            
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError as e:
            return False, f"SMTP Authentication failed: {str(e)}"
        except smtplib.SMTPConnectError as e:
            return False, f"SMTP Connection failed: {str(e)}"
        except smtplib.SMTPException as e:
            return False, f"SMTP Error: {str(e)}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    @staticmethod
    def send_whatsapp_receipt(settings, recipient_phone, recipient_name, maintenance_record):
        """Send maintenance receipt via WhatsApp"""
        try:
            message = f"""
*Maintenance Receipt*

Dear {recipient_name},

Thank you for your payment. Here are your receipt details:

*Receipt Number:* {maintenance_record.receipt_number}
*House:* {maintenance_record.house.house_number} - {maintenance_record.house.building_wing}
*Month/Year:* {maintenance_record.month_year}
*Amount Paid:* ₹{maintenance_record.paid_amount:.2f}
*Payment Date:* {maintenance_record.payment_date.strftime('%d/%m/%Y')}
*Payment Method:* {maintenance_record.payment_method}

Thank you for your timely payment.

Best regards,
{settings.sender_name}
Society Management
            """
            
            # Prepare WhatsApp API request
            url = settings.whatsapp_api_url
            headers = {
                'Authorization': f'Bearer {settings.whatsapp_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'to': recipient_phone,
                'message': message
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return True, "WhatsApp message sent successfully"
            else:
                return False, f"WhatsApp API error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"Failed to send WhatsApp message: {str(e)}"
    
    @staticmethod
    def test_email_connection(settings):
        """Test SMTP connection using the working method"""
        try:
            # Validate required fields
            if not settings.smtp_server or not settings.smtp_server.strip():
                return False, "SMTP server address is required"
            
            if not settings.smtp_port:
                return False, "SMTP port is required"
            
            if not settings.smtp_username or not settings.smtp_username.strip():
                return False, "SMTP username is required"
            
            if not settings.smtp_password or not settings.smtp_password.strip():
                return False, "SMTP password is required"
            
            # Clean server address
            smtp_server = settings.smtp_server.strip()
            if smtp_server.startswith('.'):
                return False, "SMTP server address cannot start with a dot"
            
            print(f"Testing SMTP connection: {smtp_server}:{settings.smtp_port}")
            
            # Use the exact same method as your working smtp-test.py
            server = smtplib.SMTP(smtp_server, settings.smtp_port)
            
            if settings.smtp_use_tls:
                server.starttls()
            
            server.login(settings.smtp_username.strip(), settings.smtp_password.strip())
            server.quit()
            
            return True, "SMTP connection successful"
            
        except smtplib.SMTPAuthenticationError as e:
            return False, f"SMTP Authentication failed: {str(e)}"
        except smtplib.SMTPConnectError as e:
            return False, f"SMTP Connection failed: {str(e)}"
        except smtplib.SMTPException as e:
            return False, f"SMTP Error: {str(e)}"
        except Exception as e:
            return False, f"SMTP connection failed: {str(e)}"
    
    @staticmethod
    def test_whatsapp_connection(settings):
        """Test WhatsApp API connection"""
        try:
            url = settings.whatsapp_api_url
            headers = {
                'Authorization': f'Bearer {settings.whatsapp_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Send a test message
            data = {
                'to': settings.whatsapp_phone_number,
                'message': 'Test message from Society Management System'
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return True, "WhatsApp API connection successful"
            else:
                return False, f"WhatsApp API error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"WhatsApp API connection failed: {str(e)}"

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def member_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_member:
            flash('Member access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

# Document Management Routes
@app.route('/documents')
@admin_required
def documents():
    documents = Document.query.order_by(Document.upload_date.desc()).all()
    return render_template('documents.html', documents=documents)

@app.route('/documents/upload', methods=['GET', 'POST'])
@admin_required
def upload_document():
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Get form data
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            document_type = request.form.get('document_type', '').strip()
            
            if not title:
                flash('Document title is required', 'error')
                return redirect(request.url)
            
            if not document_type:
                flash('Document type is required', 'error')
                return redirect(request.url)
            
            # Secure the filename
            original_filename = file.filename
            filename = secure_filename(original_filename)
            
            # Add timestamp to avoid filename conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
            
            # Get file info
            file_size = len(file.read())
            file.seek(0)  # Reset file pointer
            file_extension = ext[1:].lower()  # Remove the dot
            
            # Save file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Create document record
            document = Document(
                title=title,
                description=description,
                document_type=document_type,
                file_name=filename,
                original_file_name=original_filename,
                file_size=file_size,
                file_extension=file_extension,
                uploaded_by=session['user_id']
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash(f'Document "{title}" uploaded successfully!', 'success')
            return redirect(url_for('documents'))
        else:
            flash('Invalid file type. Allowed types: PDF, PNG, JPG, JPEG, GIF, DOC, DOCX, TXT, XLS, XLSX', 'error')
            return redirect(request.url)
    
    return render_template('upload_document.html')

@app.route('/documents/view/<int:document_id>')
@admin_required
def view_document(document_id):
    document = Document.query.get_or_404(document_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.file_name)
    
    if not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('documents'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], document.file_name, as_attachment=False)

@app.route('/documents/download/<int:document_id>')
@admin_required
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.file_name)
    
    if not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('documents'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], document.file_name, 
                              as_attachment=True, download_name=document.original_file_name)

@app.route('/documents/edit/<int:document_id>', methods=['GET', 'POST'])
@admin_required
def edit_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    if request.method == 'POST':
        document.title = request.form.get('title', '').strip()
        document.description = request.form.get('description', '').strip()
        document.document_type = request.form.get('document_type', '').strip()
        
        if not document.title:
            flash('Document title is required', 'error')
            return render_template('edit_document.html', document=document)
        
        if not document.document_type:
            flash('Document type is required', 'error')
            return render_template('edit_document.html', document=document)
        
        db.session.commit()
        flash('Document updated successfully!', 'success')
        return redirect(url_for('documents'))
    
    return render_template('edit_document.html', document=document)

@app.route('/documents/delete/<int:document_id>', methods=['POST'])
@admin_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Delete file from filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete database record
    db.session.delete(document)
    db.session.commit()
    
    flash(f'Document "{document.title}" deleted successfully!', 'success')
    return redirect(url_for('documents'))

# Notification Management Routes
@app.route('/notifications')
@admin_required
def notifications():
    settings = NotificationSettings.query.all()
    return render_template('notifications.html', settings=settings)

@app.route('/notifications/add', methods=['GET', 'POST'])
@admin_required
def add_notification_settings():
    if request.method == 'POST':
        notification_type = request.form['notification_type']
        
        # Deactivate existing settings of the same type
        existing_settings = NotificationSettings.query.filter_by(notification_type=notification_type).all()
        for setting in existing_settings:
            setting.is_active = False
        
        # Create new settings
        new_settings = NotificationSettings(
            notification_type=notification_type,
            sender_name=request.form.get('sender_name'),
            sender_email=request.form.get('sender_email')
        )
        
        if notification_type == 'smtp':
            new_settings.smtp_server = request.form.get('smtp_server')
            new_settings.smtp_port = int(request.form.get('smtp_port', 587))
            new_settings.smtp_username = request.form.get('smtp_username')
            new_settings.smtp_password = request.form.get('smtp_password')
            new_settings.smtp_use_tls = 'smtp_use_tls' in request.form
            
            print(f"New SMTP settings created: Server='{new_settings.smtp_server}', Username='{new_settings.smtp_username}', Password Length={len(new_settings.smtp_password) if new_settings.smtp_password else 0}")
        elif notification_type == 'whatsapp':
            new_settings.whatsapp_api_url = request.form.get('whatsapp_api_url')
            new_settings.whatsapp_api_key = request.form.get('whatsapp_api_key')
            new_settings.whatsapp_phone_number = request.form.get('whatsapp_phone_number')
        
        db.session.add(new_settings)
        db.session.commit()
        
        flash(f'{notification_type.upper()} notification settings added successfully!', 'success')
        return redirect(url_for('notifications'))
    
    return render_template('add_notification.html')

@app.route('/notifications/edit/<int:setting_id>', methods=['GET', 'POST'])
@admin_required
def edit_notification_settings(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    if request.method == 'POST':
        setting.sender_name = request.form.get('sender_name')
        setting.sender_email = request.form.get('sender_email')
        
        if setting.notification_type == 'smtp':
            setting.smtp_server = request.form.get('smtp_server')
            setting.smtp_port = int(request.form.get('smtp_port', 587))
            setting.smtp_username = request.form.get('smtp_username')
            
            # Only update password if a new one is provided
            new_password = request.form.get('smtp_password')
            if new_password and new_password.strip():
                setting.smtp_password = new_password.strip()
                print(f"Password updated for setting {setting.id}: Length = {len(new_password.strip())}")
            else:
                print(f"No new password provided for setting {setting.id}, keeping existing")
            
            setting.smtp_use_tls = 'smtp_use_tls' in request.form
        elif setting.notification_type == 'whatsapp':
            setting.whatsapp_api_url = request.form.get('whatsapp_api_url')
            setting.whatsapp_api_key = request.form.get('whatsapp_api_key')
            setting.whatsapp_phone_number = request.form.get('whatsapp_phone_number')
        
        setting.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'{setting.notification_type.upper()} notification settings updated successfully!', 'success')
        return redirect(url_for('notifications'))
    
    return render_template('edit_notification.html', setting=setting)

@app.route('/notifications/test/<int:setting_id>')
@admin_required
def test_notification_settings(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    if setting.notification_type == 'smtp':
        # Debug: Show what's actually stored
        debug_info = f"Debug - Server: '{setting.smtp_server}', Port: {setting.smtp_port}, Username: '{setting.smtp_username}', Password: {'[SET]' if setting.smtp_password else '[EMPTY]'}, TLS: {setting.smtp_use_tls}"
        print(f"SMTP Debug: {debug_info}")
        
        success, message = NotificationService.test_email_connection(setting)
        
        # Include debug info in the message
        if not success:
            message = f"{message} | {debug_info}"
    elif setting.notification_type == 'whatsapp':
        success, message = NotificationService.test_whatsapp_connection(setting)
    else:
        success, message = False, "Invalid notification type"
    
    if success:
        flash(f'Test successful: {message}', 'success')
    else:
        flash(f'Test failed: {message}', 'error')
    
    return redirect(url_for('notifications'))

@app.route('/notifications/send_test_email/<int:setting_id>', methods=['POST'])
@admin_required
def send_test_email(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    test_email = request.form.get('test_email')
    
    if not test_email:
        flash('Please provide a test email address', 'error')
        return redirect(url_for('notifications'))
    
    if setting.notification_type == 'smtp':
        # Create a dummy maintenance record for testing
        class DummyMaintenance:
            def __init__(self):
                self.receipt_number = "TEST-001"
                self.paid_amount = 1000.00
                self.payment_date = date.today()
                self.payment_method = "Test"
                self.month_year = "2024-01"
                self.house = type('House', (), {
                    'house_number': 'TEST-001',
                    'building_wing': 'Test Wing'
                })()
        
        dummy_record = DummyMaintenance()
        success, message = NotificationService.send_email_receipt(
            setting, test_email, "Test User", dummy_record
        )
        
        if success:
            flash(f'Test email sent successfully to {test_email}', 'success')
        else:
            flash(f'Failed to send test email: {message}', 'error')
    else:
        flash('This function is only available for SMTP settings', 'error')
    
    return redirect(url_for('notifications'))

@app.route('/notifications/activate/<int:setting_id>')
@admin_required
def activate_notification_settings(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    # Deactivate all settings of the same type
    NotificationSettings.query.filter_by(notification_type=setting.notification_type).update({'is_active': False})
    
    # Activate the selected setting
    setting.is_active = True
    db.session.commit()
    
    flash(f'{setting.notification_type.upper()} notification settings activated successfully!', 'success')
    return redirect(url_for('notifications'))

@app.route('/notifications/debug/<int:setting_id>')
@admin_required
def debug_notification_settings(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    debug_info = {
        'id': setting.id,
        'notification_type': setting.notification_type,
        'is_active': setting.is_active,
        'sender_name': setting.sender_name,
        'sender_email': setting.sender_email,
        'smtp_server': setting.smtp_server,
        'smtp_port': setting.smtp_port,
        'smtp_username': setting.smtp_username,
        'smtp_password': '[HIDDEN]' if setting.smtp_password else '[EMPTY]',
        'smtp_password_length': len(setting.smtp_password) if setting.smtp_password else 0,
        'smtp_use_tls': setting.smtp_use_tls,
        'whatsapp_api_url': setting.whatsapp_api_url,
        'whatsapp_api_key': '[HIDDEN]' if setting.whatsapp_api_key else '[EMPTY]',
        'whatsapp_phone_number': setting.whatsapp_phone_number,
        'created_at': setting.created_at,
        'updated_at': setting.updated_at
    }
    
    flash(f'Debug Info: {debug_info}', 'info')
    return redirect(url_for('notifications'))

@app.route('/notifications/raw_data/<int:setting_id>')
@admin_required
def show_raw_data(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    raw_data = {
        'smtp_server_raw': repr(setting.smtp_server),
        'smtp_server_type': str(type(setting.smtp_server)),
        'smtp_server_length': len(setting.smtp_server) if setting.smtp_server else 0,
        'smtp_server_stripped': repr(setting.smtp_server.strip()) if setting.smtp_server else 'None',
        'smtp_port_raw': repr(setting.smtp_port),
        'smtp_username_raw': repr(setting.smtp_username),
        'smtp_password_raw': '[HIDDEN]' if setting.smtp_password else '[EMPTY]',
        'smtp_password_length': len(setting.smtp_password) if setting.smtp_password else 0,
    }
    
    flash(f'Raw Data: {raw_data}', 'info')
    return redirect(url_for('notifications'))

@app.route('/notifications/simple_test/<int:setting_id>')
@admin_required
def simple_test_smtp(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    if setting.notification_type != 'smtp':
        flash('This test is only for SMTP settings', 'error')
        return redirect(url_for('notifications'))
    
    try:
        # Method 1: Direct connection (like your smtp-test.py)
        import smtplib
        
        print(f"=== SMTP Test Starting ===")
        print(f"Server: {setting.smtp_server}")
        print(f"Port: {setting.smtp_port}")
        print(f"Username: {setting.smtp_username}")
        print(f"Password length: {len(setting.smtp_password) if setting.smtp_password else 0}")
        print(f"Use TLS: {setting.smtp_use_tls}")
        
        # Try the most basic connection method
        server = smtplib.SMTP(setting.smtp_server, setting.smtp_port)
        
        if setting.smtp_use_tls:
            server.starttls()
        
        server.login(setting.smtp_username, setting.smtp_password)
        server.quit()
        
        flash('SMTP test successful!', 'success')
        print("=== SMTP Test Successful ===")
        
    except Exception as e:
        flash(f'SMTP test failed: {str(e)}', 'error')
        print(f"=== SMTP Test Failed: {str(e)} ===")
    
    return redirect(url_for('notifications'))

@app.route('/notifications/custom_test/<int:setting_id>')
@admin_required
def custom_test_smtp(setting_id):
    """Test with custom SMTP settings - you can modify this to match your working smtp-test.py"""
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    if setting.notification_type != 'smtp':
        flash('This test is only for SMTP settings', 'error')
        return redirect(url_for('notifications'))
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = setting.sender_email
        msg['To'] = setting.sender_email  # Send to yourself for testing
        msg['Subject'] = "Test Email from Society App"
        
        body = "This is a test email from the Society Management System."
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send (matching your working smtp-test.py method)
        server = smtplib.SMTP(setting.smtp_server, setting.smtp_port)
        
        if setting.smtp_use_tls:
            server.starttls()
        
        server.login(setting.smtp_username, setting.smtp_password)
        
        # Send the email
        text = msg.as_string()
        server.sendmail(setting.sender_email, setting.sender_email, text)
        server.quit()
        
        flash('Custom SMTP test successful! Test email sent.', 'success')
        
    except Exception as e:
        flash(f'Custom SMTP test failed: {str(e)}', 'error')
        print(f"Custom test error: {str(e)}")
    
    return redirect(url_for('notifications'))

@app.route('/notifications/delete/<int:setting_id>', methods=['POST'])
@admin_required
def delete_notification_settings(setting_id):
    setting = NotificationSettings.query.get_or_404(setting_id)
    notification_type = setting.notification_type
    
    db.session.delete(setting)
    db.session.commit()
    
    flash(f'{notification_type.upper()} notification settings deleted successfully!', 'success')
    return redirect(url_for('notifications'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        login_type = request.form.get('login_type', 'admin')  # admin or member
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Check if user type matches login type
            if login_type == 'admin' and user.is_admin:
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                session['is_member'] = user.is_member
                session['login_type'] = 'admin'
                flash('Admin login successful!', 'success')
                return redirect(url_for('dashboard'))
            elif login_type == 'member' and user.is_member:
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                session['is_member'] = user.is_member
                session['login_type'] = 'member'
                session['house_id'] = user.house_id
                flash('Member login successful!', 'success')
                return redirect(url_for('member_dashboard'))
            else:
                flash(f'Invalid login type. Please select {login_type} login.', 'error')
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Redirect to appropriate dashboard based on login type
    if session.get('login_type') == 'member':
        return redirect(url_for('member_dashboard'))
    
    # Get statistics for admin dashboard
    total_houses = House.query.count()
    total_members = Member.query.count()
    total_maintenance = Maintenance.query.count()
    pending_payments = Maintenance.query.filter_by(payment_status='Pending').count()
    
    # Get fund information
    fund = Fund.get_fund()
    
    # Get recent maintenance records
    recent_maintenance = Maintenance.query.order_by(Maintenance.created_at.desc()).limit(5).all()
    
    # Get recent expenses
    recent_expenses = Expense.query.order_by(Expense.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_houses=total_houses,
                         total_members=total_members,
                         total_maintenance=total_maintenance,
                         pending_payments=pending_payments,
                         recent_maintenance=recent_maintenance,
                         fund=fund,
                         recent_expenses=recent_expenses)

@app.route('/member/dashboard')
@member_required
def member_dashboard():
    user = User.query.get(session['user_id'])
    house = House.query.get(user.house_id)
    
    # Get member's maintenance records
    maintenance_records = Maintenance.query.filter_by(house_id=user.house_id).order_by(Maintenance.month_year.desc()).all()
    
    # Calculate current month dues
    current_month = datetime.now().strftime('%Y-%m')
    current_month_record = Maintenance.query.filter_by(house_id=user.house_id, month_year=current_month).first()
    
    # Calculate pending dues
    pending_records = Maintenance.query.filter_by(house_id=user.house_id, payment_status='Pending').all()
    pending_amount = sum(record.amount for record in pending_records)
    
    # Get recent complaints
    recent_complaints = Complaint.query.filter_by(created_by=user.id).order_by(Complaint.created_at.desc()).limit(5).all()
    
    return render_template('member_dashboard.html',
                         user=user,
                         house=house,
                         maintenance_records=maintenance_records,
                         current_month_record=current_month_record,
                         pending_amount=pending_amount,
                         recent_complaints=recent_complaints)

@app.route('/member/maintenance')
@member_required
def member_maintenance():
    user = User.query.get(session['user_id'])
    house = House.query.get(user.house_id)
    
    # Get all maintenance records for this house
    maintenance_records = Maintenance.query.filter_by(house_id=user.house_id).order_by(Maintenance.month_year.desc()).all()
    
    # Calculate current month dues
    current_month = datetime.now().strftime('%Y-%m')
    current_month_record = Maintenance.query.filter_by(house_id=user.house_id, month_year=current_month).first()
    
    # Calculate pending dues
    pending_records = Maintenance.query.filter_by(house_id=user.house_id, payment_status='Pending').all()
    pending_amount = sum(record.amount for record in pending_records)
    
    # Get payment history (paid records)
    payment_history = Maintenance.query.filter_by(house_id=user.house_id, payment_status='Paid').order_by(Maintenance.payment_date.desc()).all()
    
    return render_template('member_maintenance.html',
                         user=user,
                         house=house,
                         maintenance_records=maintenance_records,
                         current_month_record=current_month_record,
                         pending_amount=pending_amount,
                         payment_history=payment_history)

# Complaint System Routes
@app.route('/member/complaints')
@member_required
def member_complaints():
    user = User.query.get(session['user_id'])
    complaints = Complaint.query.filter_by(created_by=user.id).order_by(Complaint.created_at.desc()).all()
    return render_template('member_complaints.html', complaints=complaints, user=user)

@app.route('/member/complaints/raise', methods=['GET', 'POST'])
@member_required
def raise_complaint():
    user = User.query.get(session['user_id'])
    house = House.query.get(user.house_id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        priority = request.form.get('priority', 'Medium').strip()
        
        if not title or not description or not category:
            flash('Please fill in all required fields', 'error')
            return render_template('raise_complaint.html', house=house)
        
        # Create complaint
        complaint = Complaint(
            title=title,
            description=description,
            category=category,
            priority=priority,
            created_by=user.id,
            house_id=user.house_id
        )
        
        db.session.add(complaint)
        db.session.commit()
        
        # Send notification to admin (placeholder for now)
        flash('Complaint raised successfully! Admin has been notified.', 'success')
        return redirect(url_for('member_complaints'))
    
    return render_template('raise_complaint.html', house=house)

@app.route('/member/profile')
@member_required
def member_profile():
    user = User.query.get(session['user_id'])
    house = House.query.get(user.house_id)
    return render_template('member_profile.html', user=user, house=house)

# Admin Complaint Management Routes
@app.route('/admin/complaints')
@admin_required
def admin_complaints():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin_complaints.html', complaints=complaints)

@app.route('/admin/complaints/<int:complaint_id>/update_status', methods=['POST'])
@admin_required
def update_complaint_status(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    new_status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '').strip()
    
    if new_status in ['Open', 'In Progress', 'Resolved']:
        complaint.status = new_status
        complaint.admin_notes = admin_notes
        complaint.updated_at = datetime.utcnow()
        
        if new_status == 'Resolved':
            complaint.resolved_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Complaint status updated to {new_status}', 'success')
    else:
        flash('Invalid status', 'error')
    
    return redirect(url_for('admin_complaints'))


@app.route('/houses')
@admin_required
def houses():
    houses = House.query.all()
    return render_template('houses.html', houses=houses)

@app.route('/houses/add', methods=['GET', 'POST'])
@admin_required
def add_house():
    if request.method == 'POST':
        house = House(
            house_number=request.form['house_number'],
            building_wing=request.form['building_wing'],
            owner_name=request.form['owner_name'],
            contact_number=request.form['contact_number'],
            email=request.form.get('email'),
            number_of_occupants=int(request.form['number_of_occupants'])
        )
        db.session.add(house)
        db.session.commit()
        flash('House added successfully!', 'success')
        return redirect(url_for('houses'))
    
    return render_template('add_house.html')

@app.route('/houses/edit/<int:house_id>', methods=['GET', 'POST'])
@admin_required
def edit_house(house_id):
    house = House.query.get_or_404(house_id)
    
    if request.method == 'POST':
        house.house_number = request.form['house_number']
        house.building_wing = request.form['building_wing']
        house.owner_name = request.form['owner_name']
        house.contact_number = request.form['contact_number']
        house.email = request.form.get('email')
        house.number_of_occupants = int(request.form['number_of_occupants'])
        
        db.session.commit()
        flash('House updated successfully!', 'success')
        return redirect(url_for('houses'))
    
    return render_template('edit_house.html', house=house)

@app.route('/houses/delete/<int:house_id>')
@admin_required
def delete_house(house_id):
    house = House.query.get_or_404(house_id)
    db.session.delete(house)
    db.session.commit()
    flash('House deleted successfully!', 'success')
    return redirect(url_for('houses'))

@app.route('/members')
@admin_required
def members():
    members = Member.query.join(House).all()
    return render_template('members.html', members=members)

@app.route('/members/add', methods=['GET', 'POST'])
@admin_required
def add_member():
    if request.method == 'POST':
        # Get form data
        house_id = int(request.form['house_id'])
        name = request.form['name']
        age = int(request.form['age'])
        gender = request.form['gender']
        role = request.form['role']
        emergency_contact = request.form.get('emergency_contact')
        vehicle_number = request.form.get('vehicle_number')
        parking_slot = request.form.get('parking_slot')
        
        # Get optional login credentials
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Create member
        member = Member(
            house_id=house_id,
            name=name,
            age=age,
            gender=gender,
            role=role,
            emergency_contact=emergency_contact,
            vehicle_number=vehicle_number,
            parking_slot=parking_slot
        )
        db.session.add(member)
        db.session.flush()  # Get the member ID
        
        # Create member user if credentials provided
        if username and password:
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash(f'Username "{username}" already exists. Member added but login credentials not created.', 'warning')
            else:
                # Validate password length
                if len(password) < 6:
                    flash('Password must be at least 6 characters long. Member added but login credentials not created.', 'warning')
                else:
                    # Create member user
                    member_user = User(
                        username=username,
                        password_hash=generate_password_hash(password),
                        is_member=True,
                        house_id=house_id
                    )
                    db.session.add(member_user)
                    flash(f'Member "{name}" added successfully with login credentials!', 'success')
        else:
            flash(f'Member "{name}" added successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('members'))
    
    houses = House.query.all()
    return render_template('add_member.html', houses=houses)

@app.route('/members/edit/<int:member_id>', methods=['GET', 'POST'])
@admin_required
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    
    if request.method == 'POST':
        member.house_id = int(request.form['house_id'])
        member.name = request.form['name']
        member.age = int(request.form['age'])
        member.gender = request.form['gender']
        member.role = request.form['role']
        member.emergency_contact = request.form.get('emergency_contact')
        member.vehicle_number = request.form.get('vehicle_number')
        member.parking_slot = request.form.get('parking_slot')
        
        db.session.commit()
        flash('Member updated successfully!', 'success')
        return redirect(url_for('members'))
    
    houses = House.query.all()
    return render_template('edit_member.html', member=member, houses=houses)

@app.route('/members/delete/<int:member_id>', methods=['POST'])
@admin_required
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    member_name = member.name
    db.session.delete(member)
    db.session.commit()
    flash(f'Member "{member_name}" deleted successfully!', 'success')
    return redirect(url_for('members'))

@app.route('/maintenance')
@admin_required
def maintenance():
    maintenance_records = Maintenance.query.join(House).all()
    return render_template('maintenance.html', maintenance_records=maintenance_records)

@app.route('/maintenance/add', methods=['GET', 'POST'])
@admin_required
def add_maintenance():
    if request.method == 'POST':
        maintenance = Maintenance(
            house_id=int(request.form['house_id']),
            month_year=request.form['month_year'],
            amount=float(request.form['amount'])
        )
        db.session.add(maintenance)
        db.session.commit()
        flash('Maintenance record added successfully!', 'success')
        return redirect(url_for('maintenance'))
    
    houses = House.query.all()
    return render_template('add_maintenance.html', houses=houses)

@app.route('/maintenance/edit/<int:maintenance_id>', methods=['GET', 'POST'])
@admin_required
def edit_maintenance(maintenance_id):
    maintenance = Maintenance.query.get_or_404(maintenance_id)
    
    if request.method == 'POST':
        maintenance.house_id = int(request.form['house_id'])
        maintenance.month_year = request.form['month_year']
        maintenance.amount = float(request.form['amount'])
        
        db.session.commit()
        flash('Maintenance record updated successfully!', 'success')
        return redirect(url_for('maintenance'))
    
    houses = House.query.all()
    return render_template('edit_maintenance.html', maintenance=maintenance, houses=houses)

@app.route('/maintenance/delete/<int:maintenance_id>', methods=['POST'])
@admin_required
def delete_maintenance(maintenance_id):
    maintenance = Maintenance.query.get_or_404(maintenance_id)
    
    # If the record was paid, we need to subtract the paid amount from the fund
    if maintenance.payment_status == 'Paid' and maintenance.paid_amount > 0:
        fund = Fund.get_fund()
        fund.total_amount -= maintenance.paid_amount
        fund.last_updated = datetime.utcnow()
        flash(f'₹{maintenance.paid_amount:.2f} deducted from society fund due to record deletion!', 'info')
    
    house_info = f"{maintenance.house.house_number} - {maintenance.house.building_wing}"
    month_year = maintenance.month_year
    
    db.session.delete(maintenance)
    db.session.commit()
    flash(f'Maintenance record for {house_info} ({month_year}) deleted successfully!', 'success')
    return redirect(url_for('maintenance'))

@app.route('/maintenance/mark_paid/<int:maintenance_id>', methods=['POST'])
@admin_required
def mark_maintenance_paid(maintenance_id):
    maintenance = Maintenance.query.get_or_404(maintenance_id)
    paid_amount = float(request.form['paid_amount'])
    payment_method = request.form.get('payment_method', 'Cash')
    
    # Calculate the amount being added to fund (only new payments)
    previous_paid = maintenance.paid_amount
    new_payment_amount = paid_amount - previous_paid
    
    maintenance.paid_amount = paid_amount
    maintenance.payment_date = date.today()
    maintenance.payment_method = payment_method
    
    if paid_amount >= maintenance.amount:
        maintenance.payment_status = 'Paid'
    elif paid_amount > 0:
        maintenance.payment_status = 'Partial'
    else:
        maintenance.payment_status = 'Pending'
    
    # Generate receipt number and add to fund
    if maintenance.payment_status == 'Paid':
        if not maintenance.receipt_number:  # Only generate receipt if not already generated
            maintenance.receipt_number = f"RCP-{maintenance.id:06d}"
        
        # Add payment to fund (only if it's a new payment)
        if new_payment_amount > 0:
            fund = Fund.get_fund()
            fund.total_amount += new_payment_amount
            fund.last_updated = datetime.utcnow()
            flash(f'₹{new_payment_amount:.2f} added to society fund!', 'info')
    
    db.session.commit()
    
    # Send notification if payment is complete
    if maintenance.payment_status == 'Paid':
        try:
            # Get active notification settings
            notification_settings = NotificationSettings.get_active_settings()
            
            if notification_settings:
                house = maintenance.house
                recipient_name = house.owner_name
                
                if notification_settings.notification_type == 'smtp' and house.email:
                    success, message = NotificationService.send_email_receipt(
                        notification_settings, house.email, recipient_name, maintenance
                    )
                    if success:
                        flash('Receipt sent via email successfully!', 'success')
                    else:
                        flash(f'Failed to send email receipt: {message}', 'warning')
                
                elif notification_settings.notification_type == 'whatsapp' and house.contact_number:
                    success, message = NotificationService.send_whatsapp_receipt(
                        notification_settings, house.contact_number, recipient_name, maintenance
                    )
                    if success:
                        flash('Receipt sent via WhatsApp successfully!', 'success')
                    else:
                        flash(f'Failed to send WhatsApp receipt: {message}', 'warning')
                
                else:
                    flash('No valid contact information found for sending receipt', 'warning')
            else:
                flash('No notification settings configured. Receipt not sent.', 'info')
                
        except Exception as e:
            flash(f'Error sending receipt: {str(e)}', 'warning')
    
    flash('Payment status updated successfully!', 'success')
    return redirect(url_for('maintenance'))

@app.route('/change_password', methods=['GET', 'POST'])
@admin_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Get current user
        user = User.query.get(session['user_id'])
        
        # Verify current password
        if not check_password_hash(user.password_hash, current_password):
            flash('Current password is incorrect', 'error')
            return render_template('change_password.html')
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long', 'error')
            return render_template('change_password.html')
        
        # Update password
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html')

# Fund and Expense Management Routes
@app.route('/funds')
@admin_required
def funds():
    fund = Fund.get_fund()
    recent_expenses = Expense.query.order_by(Expense.created_at.desc()).limit(10).all()
    return render_template('funds.html', fund=fund, recent_expenses=recent_expenses)

@app.route('/expenses')
@admin_required
def expenses():
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    return render_template('expenses.html', expenses=expenses)

@app.route('/expenses/add', methods=['GET', 'POST'])
@admin_required
def add_expense():
    if request.method == 'POST':
        category = request.form['category']
        description = request.form['description']
        amount = float(request.form['amount'])
        expense_date = datetime.strptime(request.form['expense_date'], '%Y-%m-%d').date()
        
        # Validate fund availability
        fund = Fund.get_fund()
        if amount > fund.total_amount:
            flash('Insufficient funds! Available: ₹{:.2f}'.format(fund.total_amount), 'error')
            return render_template('add_expense.html')
        
        # Create expense
        expense = Expense(
            category=category,
            description=description,
            amount=amount,
            expense_date=expense_date,
            created_by=session['user_id']
        )
        
        # Update fund
        fund.total_amount -= amount
        fund.last_updated = datetime.utcnow()
        
        db.session.add(expense)
        db.session.commit()
        
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expenses'))
    
    return render_template('add_expense.html')

@app.route('/expenses/report')
@admin_required
def expense_report():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    query = Expense.query
    
    if from_date:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        query = query.filter(Expense.expense_date >= from_date_obj)
    
    if to_date:
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        query = query.filter(Expense.expense_date <= to_date_obj)
    
    expenses = query.order_by(Expense.expense_date.desc()).all()
    
    # Calculate totals by category
    category_totals = {}
    total_amount = 0
    
    for expense in expenses:
        if expense.category not in category_totals:
            category_totals[expense.category] = 0
        category_totals[expense.category] += expense.amount
        total_amount += expense.amount
    
    return render_template('expense_report.html', 
                         expenses=expenses, 
                         category_totals=category_totals,
                         total_amount=total_amount,
                         from_date=from_date,
                         to_date=to_date)

@app.route('/expenses/download_report')
@admin_required
def download_expense_report():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    query = Expense.query
    
    if from_date:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        query = query.filter(Expense.expense_date >= from_date_obj)
    
    if to_date:
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        query = query.filter(Expense.expense_date <= to_date_obj)
    
    expenses = query.order_by(Expense.expense_date.desc()).all()
    
    # Generate CSV content
    csv_content = "Date,Category,Description,Amount,Created By\n"
    for expense in expenses:
        csv_content += f"{expense.expense_date},{expense.category},{expense.description},{expense.amount},{expense.creator.username}\n"
    
    # Create response
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=expense_report_{from_date or "all"}_{to_date or "all"}.csv'
    
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created: username='admin', password='admin123'")
    
    app.run(debug=True, host='0.0.0.0', port=5002)
