# Society Maintenance App

A comprehensive Flask-based web application for managing society maintenance, houses, members, and payments.

## Features

### Core Features (MVP)
- **Authentication & Roles**: Admin login system with role-based access
- **House & Member Management**: Complete CRUD operations for houses and members
- **Maintenance Tracking**: Track monthly maintenance payments with status updates
- **Admin Interface**: Full administrative control over the system
- **Payment Management**: Mark payments as paid/partial/pending with receipt generation

### Key Functionality
- Add, edit, and delete houses with complete details
- Manage member information including vehicle and parking details
- Track maintenance payments with automatic receipt generation
- Dashboard with statistics and recent activity
- Responsive design with modern UI

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)
- MySQL Server 5.7 or higher

### Installation Steps

1. **Install MySQL Server**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install mysql-server
   
   # Start MySQL service
   sudo systemctl start mysql
   sudo systemctl enable mysql
   
   # Secure MySQL installation
   sudo mysql_secure_installation
   ```

2. **Clone or navigate to the project directory**
   ```bash
   cd /path/to/society-app
   ```

3. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure MySQL database**
   - Edit `app.py` and update the database configuration:
     ```python
     DB_USERNAME = 'root'  # Your MySQL username
     DB_PASSWORD = 'your_password'  # Your MySQL password
     DB_HOST = 'localhost'
     DB_PORT = '3306'
     DB_NAME = 'society_app'
     ```

6. **Setup the database**
   ```bash
   python setup_database.py
   ```

7. **Run the application**
   ```bash
   python app.py
   ```

8. **Access the application**
   - Open your web browser and go to: `http://localhost:5000`
   - Default admin credentials:
     - Username: `admin`
     - Password: `admin123`

## Database

The application uses MySQL database (`society_app`) which needs to be created before running the application. The database includes the following tables:

- **users**: Admin user accounts
- **houses**: House/flat information
- **members**: Member details linked to houses
- **maintenance**: Maintenance payment records

## Usage Guide

### Admin Dashboard
- View statistics: total houses, members, maintenance records, and pending payments
- Quick access to all management functions
- Recent maintenance records overview

### House Management
- Add new houses with complete details (house number, building/wing, owner info)
- Edit existing house information
- Delete houses (with confirmation)

### Member Management
- Add members linked to specific houses
- Include personal details, emergency contacts, and vehicle information
- Support for both owners and tenants

### Maintenance Tracking
- Add monthly maintenance records for each house
- Track payment status (Pending/Partial/Paid)
- Mark payments as received with amount tracking
- Automatic receipt number generation for completed payments

## Security Notes

- Change the default admin password after first login
- Update the `SECRET_KEY` in `app.py` for production use
- Consider using environment variables for sensitive configuration

## File Structure

```
society-app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── login.html        # Login page
│   ├── dashboard.html    # Admin dashboard
│   ├── houses.html       # Houses listing
│   ├── add_house.html    # Add house form
│   ├── edit_house.html   # Edit house form
│   ├── members.html      # Members listing
│   ├── add_member.html   # Add member form
│   ├── maintenance.html  # Maintenance records
│   └── add_maintenance.html # Add maintenance form
└── static/
    └── css/
        └── style.css     # Custom styling
```

## Future Enhancements

The application is designed to be extensible. Potential future features include:

- Member login system for residents
- Online payment gateway integration
- Email/SMS notifications
- Document management
- Complaint/request system
- Event and facility booking
- Advanced reporting and analytics

## Support

For issues or questions, please check the code comments or create an issue in the project repository.

## License

This project is open source and available under the MIT License.