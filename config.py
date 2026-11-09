import os

SECRET_KEY = "your_secret_key"

# Database Configuration (SQLite)
DB_NAME = "smartcart.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)

# Legacy MySQL settings (kept for backwards compatibility if needed)
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "root"

# Email SMTP Settings
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'gandhamsushmashree@gmail.com'
MAIL_PASSWORD = 'gayb bgyu nqew jouj'   # Gmail App Password
RAZORPAY_KEY_ID = "rzp_test_TLeM6Ox9b7K9Dp"
RAZORPAY_KEY_SECRET = "dU4b4haEuqjJU1pc61pvF0UE"
