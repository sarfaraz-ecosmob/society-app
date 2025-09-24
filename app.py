from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
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
    # Get statistics for dashboard
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
        member = Member(
            house_id=int(request.form['house_id']),
            name=request.form['name'],
            age=int(request.form['age']),
            gender=request.form['gender'],
            role=request.form['role'],
            emergency_contact=request.form.get('emergency_contact'),
            vehicle_number=request.form.get('vehicle_number'),
            parking_slot=request.form.get('parking_slot')
        )
        db.session.add(member)
        db.session.commit()
        flash('Member added successfully!', 'success')
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
