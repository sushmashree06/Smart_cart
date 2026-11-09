from flask import Flask, render_template, request, redirect, session, flash, url_for, send_from_directory, make_response
from flask_mail import Mail, Message
import mysql.connector
import bcrypt
import random
import config
import os
import razorpay
import secrets
from werkzeug.utils import secure_filename
from utils.pdf_generator import generate_pdf


app = Flask(__name__)
app.secret_key = config.SECRET_KEY
razorpay_client = razorpay.Client(
    auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET)
)


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

app.config['MAIL_SERVER'] = config.MAIL_SERVER
app.config['MAIL_PORT'] = config.MAIL_PORT
app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD

mail = Mail(app)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )


# =========================================================
# IMAGE UPLOAD FOLDERS
# =========================================================

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    'static',
    'uploads',
    'product_images'
)

ADMIN_UPLOAD_FOLDER = os.path.join(
    app.root_path,
    'static',
    'uploads',
    'admin_profiles'
)

USER_UPLOAD_FOLDER = os.path.join(
    app.root_path,
    'static',
    'uploads',
    'user_profiles'
)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ADMIN_UPLOAD_FOLDER'] = ADMIN_UPLOAD_FOLDER
app.config['USER_UPLOAD_FOLDER'] = USER_UPLOAD_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ADMIN_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(USER_UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# STATIC FILE SERVING FOR UPLOADS
# =========================================================

@app.route('/uploads/user_profiles/<filename>')
def serve_user_profile(filename):
    return send_from_directory(app.config['USER_UPLOAD_FOLDER'], filename)

@app.route('/uploads/admin_profiles/<filename>')
def serve_admin_profile(filename):
    return send_from_directory(app.config['ADMIN_UPLOAD_FOLDER'], filename)

@app.route('/uploads/product_images/<filename>')
def serve_product_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# =========================================================
# ROOT ROUTE (Allows visitors to see everything at 5000/)
# =========================================================

@app.route('/')
def home():
    if 'admin_id' in session:
        return redirect('/admin-dashboard')
    return redirect('/user/products')


# =========================================================
# ROUTE 1: ADMIN SIGNUP - SEND OTP
# =========================================================

@app.route('/admin-signup', methods=['GET', 'POST'])
def admin_signup():

    if request.method == 'GET':
        return render_template("admin/admin_signup.html")

    name = request.form['name']
    email = request.form['email']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT admin_id FROM admin WHERE email=%s",
        (email,)
    )

    existing_admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if existing_admin:
        flash("This email is already registered. Please login instead.", "danger")
        return redirect('/admin-signup')

    session['signup_name'] = name
    session['signup_email'] = email

    otp = random.randint(100000, 999999)
    session['otp'] = otp

    message = Message(
        subject="SmartCart Admin OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )

    message.body = f"Your OTP for SmartCart Admin Registration is: {otp}"

    mail.send(message)

    flash("OTP sent to your email!", "success")

    return redirect('/verify-otp')


# =========================================================
# ROUTE 2: DISPLAY OTP PAGE
# =========================================================

@app.route('/verify-otp', methods=['GET'])
def verify_otp_get():

    return render_template("admin/verify_otp.html")


# =========================================================
# ROUTE 3: VERIFY OTP AND SAVE ADMIN
# =========================================================

@app.route('/verify-otp', methods=['POST'])
def verify_otp_post():

    user_otp = request.form['otp']
    password = request.form['password']

    if str(session.get('otp')) != str(user_otp):
        flash("Invalid OTP. Try again!", "danger")
        return redirect('/verify-otp')

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO admin (name, email, password)
        VALUES (%s, %s, %s)
        """,
        (
            session['signup_name'],
            session['signup_email'],
            hashed_password
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    session.pop('otp', None)
    session.pop('signup_name', None)
    session.pop('signup_email', None)

    flash("Admin Registered Successfully!", "success")

    return redirect('/admin-signup')


# =========================================================
# ROUTE 4: ADMIN LOGIN
# =========================================================

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'GET':
        return render_template("admin/admin_login.html")

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM admin WHERE email=%s",
        (email,)
    )

    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if admin is None:
        flash("Email not found! Please register first.", "danger")
        return redirect('/admin-login')

    stored_password = admin['password']

    if isinstance(stored_password, str):
        stored_password = stored_password.encode('utf-8')

    if not bcrypt.checkpw(
        password.encode('utf-8'),
        stored_password
    ):
        flash("Incorrect password! Try again.", "danger")
        return redirect('/admin-login')

    session['admin_id'] = admin['admin_id']
    session['admin_name'] = admin['name']
    session['admin_email'] = admin['email']

    flash("Login Successful!", "success")

    return redirect('/admin-dashboard')


# =========================================================
# ROUTE 5: ADMIN DASHBOARD
# =========================================================

@app.route('/admin-dashboard')
def admin_dashboard():

    if 'admin_id' not in session:
        flash("Please login to access dashboard!", "danger")
        return redirect('/admin-login')

    return render_template(
        "admin/dashboard.html",
        admin_name=session['admin_name']
    )


# =========================================================
# ROUTE 6: ADMIN LOGOUT
# =========================================================

@app.route('/admin-logout')
def admin_logout():

    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)

    flash("Logged out successfully.", "success")

    return redirect('/admin-login')


# =========================================================
# ROUTE 7: SHOW ADD PRODUCT PAGE
# =========================================================

@app.route('/admin/add-item', methods=['GET'])
def add_item_page():

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    return render_template("admin/add_item.html")


# =========================================================
# ROUTE 8: ADD PRODUCT WITH ADMIN FOREIGN KEY
# =========================================================

@app.route('/admin/add-item', methods=['POST'])
def add_item():

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']

    image_file = request.files['image']

    if image_file.filename == "":
        flash("Please upload a product image!", "danger")
        return redirect('/admin/add-item')

    filename = secure_filename(image_file.filename)

    image_path = os.path.join(
        app.config['UPLOAD_FOLDER'],
        filename
    )

    image_file.save(image_path)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Store logged-in admin ID as foreign key

    cursor.execute(
        """
        INSERT INTO products
        (admin_id, name, description, category, price, image)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            session['admin_id'],
            name,
            description,
            category,
            price,
            filename
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Product added successfully!", "success")

    return redirect('/admin/item-list')


# =========================================================
# ROUTE 9: PRODUCT LIST WITH SEARCH AND CATEGORY FILTER (ISOLATED TO LOGGED-IN ADMIN)
# =========================================================

@app.route('/admin/item-list')
def item_list():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch category names belonging ONLY to this admin
    cursor.execute(
        """
        SELECT DISTINCT category
        FROM products
        WHERE admin_id = %s
          AND category IS NOT NULL
          AND category != ''
        ORDER BY category
        """,
        (admin_id,)
    )

    category_rows = cursor.fetchall()
    categories = [row['category'] for row in category_rows]

    # Build product query strictly filtered by admin_id
    query = "SELECT * FROM products WHERE admin_id = %s"
    params = [admin_id]

    if search:
        query += " AND name LIKE %s"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = %s"
        params.append(category_filter)

    query += " ORDER BY product_id DESC"

    cursor.execute(query, tuple(params))
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/item_list.html",
        products=products,
        categories=categories
    )


# =========================================================
# ROUTE 10: VIEW SINGLE PRODUCT (ISOLATED TO LOGGED-IN ADMIN)
# =========================================================

@app.route('/admin/view-item/<int:item_id>')
def view_item(item_id):

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM products WHERE product_id = %s AND admin_id = %s",
        (item_id, admin_id)
    )

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found or access denied!", "danger")
        return redirect('/admin/item-list')

    return render_template(
        "admin/view_item.html",
        product=product
    )


# =========================================================
# ROUTE 11: SHOW UPDATE PRODUCT FORM (ISOLATED TO LOGGED-IN ADMIN)
# =========================================================

@app.route('/admin/update-item/<int:item_id>', methods=['GET'])
def update_item_page(item_id):

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM products WHERE product_id = %s AND admin_id = %s",
        (item_id, admin_id)
    )

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found or access denied!", "danger")
        return redirect('/admin/item-list')

    return render_template(
        "admin/update_item.html",
        product=product
    )


# =========================================================
# ROUTE 12: UPDATE PRODUCT AND OPTIONAL IMAGE (ISOLATED TO LOGGED-IN ADMIN)
# =========================================================

@app.route('/admin/update-item/<int:item_id>', methods=['POST'])
def update_item(item_id):

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']

    new_image = request.files.get('image')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM products WHERE product_id = %s AND admin_id = %s",
        (item_id, admin_id)
    )

    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()

        flash("Product not found or access denied!", "danger")
        return redirect('/admin/item-list')

    old_image_name = product['image']

    # Replace image only if a new image is uploaded
    if new_image and new_image.filename != "":
        new_filename = secure_filename(new_image.filename)
        new_image_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            new_filename
        )
        new_image.save(new_image_path)
        final_image_name = new_filename

        if old_image_name != new_filename:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM products
                WHERE image=%s AND product_id != %s
                """,
                (old_image_name, item_id)
            )

            image_count = cursor.fetchone()['total']
            old_image_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                old_image_name
            )

            if image_count == 0 and os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except Exception:
                    pass
    else:
        final_image_name = old_image_name

    cursor.execute(
        """
        UPDATE products
        SET name=%s,
            description=%s,
            category=%s,
            price=%s,
            image=%s
        WHERE product_id=%s AND admin_id=%s
        """,
        (
            name,
            description,
            category,
            price,
            final_image_name,
            item_id,
            admin_id
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product updated successfully!", "success")
    return redirect('/admin/item-list')


# =========================================================
# ROUTE 13: DELETE PRODUCT (ISOLATED TO LOGGED-IN ADMIN)
# =========================================================

@app.route('/admin/delete-item/<int:item_id>')
def delete_item(item_id):

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT image FROM products WHERE product_id=%s AND admin_id=%s",
        (item_id, admin_id)
    )

    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()

        flash("Product not found or access denied!", "danger")
        return redirect('/admin/item-list')

    image_name = product['image']

    cursor.execute(
        "DELETE FROM products WHERE product_id=%s AND admin_id=%s",
        (item_id, admin_id)
    )

    conn.commit()

    # Delete image only if no other product uses it
    if image_name:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM products WHERE image=%s",
            (image_name,)
        )
        image_count = cursor.fetchone()['total']

        if image_count == 0:
            image_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                image_name
            )
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass

    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")
    return redirect('/admin/item-list')

    # Delete image only if no other product uses it

    cursor.execute(
        "SELECT COUNT(*) AS total FROM products WHERE image=%s",
        (image_name,)
    )

    image_count = cursor.fetchone()['total']

    if image_count == 0 and image_name:

        image_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            image_name
        )

        if os.path.exists(image_path):
            os.remove(image_path)

    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")

    return redirect('/admin/item-list')


# =========================================================
# ROUTE 14: SHOW ADMIN PROFILE
# =========================================================

@app.route('/admin/profile', methods=['GET'])
def admin_profile():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM admin WHERE admin_id = %s",
        (admin_id,)
    )

    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "admin/admin_profile.html",
        admin=admin
    )


# =========================================================
# ROUTE 15: UPDATE ADMIN PROFILE
# =========================================================

@app.route('/admin/profile', methods=['POST'])
def admin_profile_update():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']

    name = request.form['name']
    email = request.form['email']
    new_password = request.form['password']

    new_image = request.files.get('profile_image')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM admin WHERE admin_id = %s",
        (admin_id,)
    )

    admin = cursor.fetchone()

    if not admin:
        cursor.close()
        conn.close()

        flash("Admin not found!", "danger")
        return redirect('/admin-login')

    old_image_name = admin['profile_image']

    # Update password only if entered

    if new_password:

        hashed_password = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        )

    else:
        hashed_password = admin['password']

    # Update profile image

    if new_image and new_image.filename != "":

        new_filename = secure_filename(new_image.filename)

        image_path = os.path.join(
            app.config['ADMIN_UPLOAD_FOLDER'],
            new_filename
        )

        new_image.save(image_path)

        final_image_name = new_filename

        if old_image_name and old_image_name != new_filename:

            old_image_path = os.path.join(
                app.config['ADMIN_UPLOAD_FOLDER'],
                old_image_name
            )

            if os.path.exists(old_image_path):
                os.remove(old_image_path)

    else:
        final_image_name = old_image_name

    cursor.execute(
        """
        UPDATE admin
        SET name=%s,
            email=%s,
            password=%s,
            profile_image=%s
        WHERE admin_id=%s
        """,
        (
            name,
            email,
            hashed_password,
            final_image_name,
            admin_id
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    session['admin_name'] = name
    session['admin_email'] = email

    flash("Profile updated successfully!", "success")

    return redirect('/admin/profile')


# =========================================================
# ROUTE 16: FORGOT PASSWORD - SEND OTP
# =========================================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'GET':
        return render_template('admin/forgot_password.html')

    email = request.form['email'].strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT admin_id FROM admin WHERE email=%s",
        (email,)
    )

    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if not admin:
        flash(
            "Email not found! Please enter your registered email.",
            "danger"
        )
        return redirect('/forgot-password')

    otp = str(secrets.randbelow(900000) + 100000)

    otp_hash = bcrypt.hashpw(
        otp.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO password_resets
        (email, otp_hash, expires_at, attempts)
        VALUES (
            %s,
            %s,
            DATE_ADD(UTC_TIMESTAMP(), INTERVAL 5 MINUTE),
            0
        )
        ON DUPLICATE KEY UPDATE
            otp_hash = VALUES(otp_hash),
            expires_at = VALUES(expires_at),
            attempts = 0
        """,
        (email, otp_hash)
    )

    conn.commit()

    cursor.close()
    conn.close()

    message = Message(
        subject="SmartCart Password Reset OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )

    message.body = f"""
Your SmartCart password reset OTP is: {otp}

This OTP is valid for 5 minutes.
Do not share this OTP with anyone.
"""

    mail.send(message)

    session['reset_email'] = email

    flash("OTP sent successfully to your email!", "success")

    return redirect('/reset-password')


# =========================================================
# ROUTE 17: VERIFY OTP AND RESET PASSWORD
# =========================================================

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():

    email = session.get('reset_email')

    if not email:
        flash("Please request an OTP first!", "danger")
        return redirect('/forgot-password')

    if request.method == 'GET':

        return render_template(
            'admin/reset_password.html',
            email=email
        )

    otp = request.form.get('otp','').strip()
    new_password = request.form.get('new_password','')
    confirm_password = request.form.get('confirm_password','')

    print("FORM DATA:", request.form)
    print("OTP:", bool(otp))
    print("NEW PASSWORD:", bool(new_password))
    print("CONFIRM PASSWORD:", bool(confirm_password))

    if not otp or not new_password or not confirm_password:
        flash("Please fill in all fields!","danger")
        return redirect(url_for('reset_password'))

    if len(new_password) < 8:
        flash(
            "Password must contain at least 8 characters!",
            "danger"
        )
        return redirect('/reset-password')

    if new_password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect('/reset-password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT otp_hash, attempts,
        (expires_at > UTC_TIMESTAMP()) AS active
        FROM password_resets
        WHERE email=%s
        """,
        (email,)
    )

    reset_data = cursor.fetchone()

    if not reset_data:

        cursor.close()
        conn.close()

        session.pop('reset_email', None)

        flash("Please request a new OTP!", "danger")

        return redirect('/forgot-password')

    if not reset_data['active']:

        cursor.execute(
            "DELETE FROM password_resets WHERE email=%s",
            (email,)
        )

        conn.commit()

        cursor.close()
        conn.close()

        session.pop('reset_email', None)

        flash("OTP expired! Please request a new OTP.", "danger")

        return redirect('/forgot-password')

    if reset_data['attempts'] >= 5:

        cursor.execute(
            "DELETE FROM password_resets WHERE email=%s",
            (email,)
        )

        conn.commit()

        cursor.close()
        conn.close()

        session.pop('reset_email', None)

        flash(
            "Maximum attempts reached. Request a new OTP.",
            "danger"
        )

        return redirect('/forgot-password')

    stored_hash = reset_data['otp_hash']

    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode('utf-8')

    elif isinstance(stored_hash, bytearray):
        stored_hash = bytes(stored_hash)

    if not bcrypt.checkpw(
        otp.encode('utf-8'),
        stored_hash
    ):

        attempts = reset_data['attempts'] + 1

        if attempts >= 5:

            cursor.execute(
                "DELETE FROM password_resets WHERE email=%s",
                (email,)
            )

            conn.commit()

            cursor.close()
            conn.close()

            session.pop('reset_email', None)

            flash(
                "Maximum attempts reached. Request a new OTP.",
                "danger"
            )

            return redirect('/forgot-password')

        cursor.execute(
            """
            UPDATE password_resets
            SET attempts=%s
            WHERE email=%s
            """,
            (attempts, email)
        )

        conn.commit()

        cursor.close()
        conn.close()

        flash("Invalid OTP! Please try again.", "danger")

        return redirect('/reset-password')

    # Hash new password

    hashed_password = bcrypt.hashpw(
        new_password.encode('utf-8'),
        bcrypt.gensalt()
    )

    cursor.execute(
        """
        UPDATE admin
        SET password=%s
        WHERE email=%s
        """,
        (hashed_password, email)
    )

    cursor.execute(
        "DELETE FROM password_resets WHERE email=%s",
        (email,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    session.pop('reset_email', None)

    flash(
        "Password reset successfully! Please login.",
        "success"
    )

    return redirect('/admin-login')


# =========================================================
# ROUTE 18: USER REGISTRATION
# =========================================================

@app.route('/user-register', methods=['GET', 'POST'])
def user_register():

    if request.method == 'GET':
        return render_template("user/user_register.html")

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:

        cursor.close()
        conn.close()

        flash("Email already registered! Please login.", "danger")

        return redirect('/user-register')

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    )

    cursor.execute(
        """
        INSERT INTO users (name, email, password)
        VALUES (%s, %s, %s)
        """,
        (name, email, hashed_password)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Registration successful! Please login.", "success")

    return redirect('/user-login')


# =========================================================
# ROUTE 19: USER LOGIN
# =========================================================

@app.route('/user-login', methods=['GET', 'POST'])
def user_login():

    if request.method == 'GET':
        return render_template("user/user_login.html")

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        flash("Email not found! Please register.", "danger")
        return redirect('/user-login')

    stored_password = user['password']

    if isinstance(stored_password, str):
        stored_password = stored_password.encode('utf-8')

    if not bcrypt.checkpw(
        password.encode('utf-8'),
        stored_password
    ):
        flash("Incorrect password!", "danger")
        return redirect('/user-login')

    session['user_id'] = user['user_id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']

    flash("Login successful!", "success")

    return redirect('/user-dashboard')


# =========================================================
# ROUTE 20: USER DASHBOARD
# =========================================================

@app.route('/user-dashboard')
def user_dashboard():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    return render_template(
        "user/user_home.html",
        user_name=session['user_name']
    )


# =========================================================
# ROUTE 21: USER LOGOUT
# =========================================================

@app.route('/user-logout')
def user_logout():

    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)

    flash("Logged out successfully!", "success")

    return redirect('/user-login')


# =========================================================
# ROUTE 21B: USER PROFILE (VIEW AND UPDATE)
# =========================================================

@app.route('/user/profile', methods=['GET'])
def user_profile():

    if 'user_id' not in session:
        flash("Please login to view profile!", "danger")
        return redirect('/user-login')

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE user_id = %s",
        (user_id,)
    )
    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT * FROM customer_address
        WHERE user_id = %s
        ORDER BY address_id DESC
        LIMIT 1
        """,
        (user_id,)
    )
    address = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        flash("User not found!", "danger")
        return redirect('/user-login')

    return render_template(
        "user/profile.html",
        user=user,
        address=address
    )


@app.route('/user/profile', methods=['POST'])
def user_profile_update():

    if 'user_id' not in session:
        flash("Please login to update profile!", "danger")
        return redirect('/user-login')

    user_id = session['user_id']

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    new_password = request.form.get('password', '').strip()
    new_image = request.files.get('profile_image')

    if not name or not email:
        flash("Name and email are required!", "danger")
        return redirect('/user/profile')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE user_id = %s",
        (user_id,)
    )
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        flash("User not found!", "danger")
        return redirect('/user-login')

    # If email changed, ensure unique
    if email != user['email']:
        cursor.execute(
            "SELECT user_id FROM users WHERE email=%s AND user_id != %s",
            (email, user_id)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash("This email is already in use by another account!", "danger")
            return redirect('/user/profile')

    # Update password if entered
    if new_password:
        if len(new_password) < 6:
            cursor.close()
            conn.close()
            flash("Password must be at least 6 characters!", "danger")
            return redirect('/user/profile')

        hashed_password = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        )
    else:
        stored_pw = user['password']
        if isinstance(stored_pw, str):
            stored_pw = stored_pw.encode('utf-8')
        hashed_password = stored_pw

    # Ensure profile_image column exists in users table (auto-migrate if missing)
    try:
        cursor.execute("SHOW COLUMNS FROM users LIKE 'profile_image'")
        has_profile_img_col = cursor.fetchone() is not None
        if not has_profile_img_col:
            cursor.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) DEFAULT NULL")
            conn.commit()
            has_profile_img_col = True
    except Exception as e:
        print("Note on users column:", e)
        has_profile_img_col = False

    old_image_name = user.get('profile_image')
    final_image_name = old_image_name

    if new_image and new_image.filename != "":
        clean_ext = os.path.splitext(secure_filename(new_image.filename))[1]
        unique_name = f"user_{user_id}_{secrets.token_hex(4)}{clean_ext}"
        image_path = os.path.join(app.config['USER_UPLOAD_FOLDER'], unique_name)
        new_image.save(image_path)
        final_image_name = unique_name

        if old_image_name and old_image_name != unique_name:
            old_path = os.path.join(app.config['USER_UPLOAD_FOLDER'], old_image_name)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

    if has_profile_img_col:
        cursor.execute(
            """
            UPDATE users
            SET name=%s, email=%s, password=%s, profile_image=%s
            WHERE user_id=%s
            """,
            (name, email, hashed_password, final_image_name, user_id)
        )
    else:
        cursor.execute(
            """
            UPDATE users
            SET name=%s, email=%s, password=%s
            WHERE user_id=%s
            """,
            (name, email, hashed_password, user_id)
        )

    conn.commit()
    cursor.close()
    conn.close()

    session['user_name'] = name
    session['user_email'] = email
    if final_image_name:
        session['user_profile_image'] = final_image_name

    flash("Profile updated successfully!", "success")
    return redirect('/user/profile')


# =========================================================
# ROUTE 22: USER PRODUCT LIST WITH SEARCH AND FILTER
# (Publicly accessible so visitors can see everything at 5000/)
# =========================================================

@app.route('/user/products')
def user_products():

    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch category names as strings
    cursor.execute(
        """
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
          AND category != ''
        ORDER BY category
        """
    )

    category_rows = cursor.fetchall()
    categories = [
        row['category'] for row in category_rows
    ]

    # Product query
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE %s"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = %s"
        params.append(category_filter)

    query += " ORDER BY product_id DESC"

    cursor.execute(query, tuple(params))
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "user/user_products.html",
        products=products,
        categories=categories
    )


# =========================================================
# ROUTE 23: USER SINGLE PRODUCT DETAILS
# =========================================================

@app.route('/user/product/<int:product_id>')
def user_product_details(product_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM products WHERE product_id = %s",
        (product_id,)
    )

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/user/products')

    return render_template(
        "user/product_details.html",
        product=product
    )


# ⭐ ROUTE 1: Add to Cart
# =================================================================
# ADD ITEM TO CART
# =================================================================
@app.route('/user/add-to-cart/<int:product_id>')
def add_to_cart(product_id):

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    # Create cart if doesn't exist
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    # Get product
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_id=%s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if not product:
        flash("Product not found.", "danger")
        return redirect(request.referrer)

    pid = str(product_id)

    # If exists → increase quantity
    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        }

    session['cart'] = cart

    flash("Item added to cart!", "success")
    # return redirect('/user/cart')    instead of this line use below line
    return redirect(request.referrer)   # ⭐ Return to same page
# ⭐ ROUTE 2: View Cart Page
# =================================================================
# VIEW CART PAGE
# =================================================================
@app.route('/user/cart')
def view_cart():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    cart = session.get('cart', {})

    # Calculate total
    grand_total = sum(item['price'] * item['quantity'] for item in cart.values())

    return render_template("user/cart.html", cart=cart, grand_total=grand_total)

# ⭐ ROUTE 3: Increase Quantity
# =================================================================
# INCREASE QUANTITY
# =================================================================
@app.route('/user/cart/increase/<pid>')
def increase_quantity(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart[pid]['quantity'] += 1

    session['cart'] = cart
    return redirect('/user/cart')

# ⭐ ROUTE 4: Decrease Quantity
# =================================================================
# DECREASE QUANTITY
# =================================================================
@app.route('/user/cart/decrease/<pid>')
def decrease_quantity(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart[pid]['quantity'] -= 1

        # If quantity becomes 0 → remove item
        if cart[pid]['quantity'] <= 0:
            cart.pop(pid)

    session['cart'] = cart
    return redirect('/user/cart')

# ⭐ ROUTE 5: Remove Item Completely
# =================================================================
# REMOVE ITEM
# =================================================================
@app.route('/user/cart/remove/<pid>')
def remove_from_cart(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart.pop(pid)

    session['cart'] = cart

    flash("Item removed!", "success")
    return redirect('/user/cart')


# =========================================================
# USER ADDRESS PAGE
# =========================================================

@app.route('/user/address')
def user_address():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    return render_template('user/address.html')


# =========================================================
# SAVE ADDRESS TO DATABASE
# =========================================================

@app.route('/user/save-address', methods=['POST'])
def save_address():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    name = request.form['name']
    phone = request.form['phone']
    address = request.form['address']

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO customer_address
        (user_id, full_name, phone, delivery_address)
        VALUES (%s, %s, %s, %s)
    """

    cursor.execute(query, (user_id, name, phone, address))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Address saved successfully!", "success")
    return redirect('/user/confirm-order')


# =========================================================
# SMART PROCEED TO CHECKOUT / PAYMENT ROUTE
# =========================================================

@app.route('/user/checkout')
def user_checkout():

    if 'user_id' not in session:
        flash("Please login to proceed!", "danger")
        return redirect('/user-login')

    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty! Add products to proceed.", "danger")
        return redirect('/user/products')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT * FROM customer_address
        WHERE user_id = %s
        ORDER BY address_id DESC
        LIMIT 1
        """,
        (session['user_id'],)
    )
    customer = cursor.fetchone()

    cursor.close()
    conn.close()

    if not customer:
        flash("Please provide your delivery address first.", "info")
        return redirect('/user/address')

    return redirect('/user/confirm-order')


# =========================================================
# CONFIRM ORDER PAGE
# =========================================================

@app.route('/user/confirm-order')
def confirm_order():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty!", "danger")
        return redirect('/user/products')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT * FROM customer_address
        WHERE user_id = %s
        ORDER BY address_id DESC
        LIMIT 1
        """,
        (session['user_id'],)
    )

    customer = cursor.fetchone()

    cursor.close()
    conn.close()

    if not customer:
        flash("Please enter your delivery address!", "danger")
        return redirect('/user/address')

    grand_total = sum(item['price'] * item['quantity'] for item in cart.values())

    return render_template(
        'user/confirm_order.html',
        customer=customer,
        cart=cart,
        grand_total=grand_total
    )

# =================================================================
# ROUTE: CREATE RAZORPAY ORDER
# =================================================================
@app.route('/user/pay')
def user_pay():

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    cart = session.get('cart', {})

    if not cart:
        flash("Your cart is empty!", "danger")
        return redirect('/user/products')

    # Calculate total amount
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
    razorpay_amount = int(total_amount * 100)  # convert to paise

    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    session['razorpay_order_id'] = razorpay_order['id']

    return render_template(
        "user/payment.html",
        amount=total_amount,
        key_id=config.RAZORPAY_KEY_ID,
        order_id=razorpay_order['id']
    )


@app.route('/payment-success')
def payment_success():

    payment_id = request.args.get('payment_id')
    order_id = request.args.get('order_id')

    if not payment_id:
        flash("Payment failed!", "danger")
        return redirect('/user/cart')

    return render_template(
        "user/payment_success.html",
        payment_id=payment_id,
        order_id=order_id
    )



# DAY 13: Verify Razorpay Payment & Store Order + Order Items

from flask import request, jsonify, render_template
import razorpay
import traceback

# Ensure razorpay_client is initialized (from Day 12)
# razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

# ------------------------------
# Route: Verify Payment and Store Order
# ------------------------------
@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    if 'user_id' not in session:
        flash("Please login to complete the payment.", "danger")
        return redirect('/user-login')

    # Read values posted from frontend
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')

    if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
        flash("Payment verification failed (missing data).", "danger")
        return redirect('/user/cart')

    # Build verification payload required by Razorpay client.utility
    payload = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        # This will raise an error if signature invalid
        razorpay_client.utility.verify_payment_signature(payload)

    except Exception as e:
        # Verification failed
        app.logger.error("Razorpay signature verification failed: %s", str(e))
        flash("Payment verification failed. Please contact support.", "danger")
        return redirect('/user/cart')

    # Signature verified — now store order and items into DB
    user_id = session['user_id']
    cart = session.get('cart', {})

    if not cart:
        flash("Cart is empty. Cannot create order.", "danger")
        return redirect('/user/products')

    # Calculate total amount (ensure same as earlier)
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())

    # DB insert: orders and order_items
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert into orders table
        cursor.execute("""
            INSERT INTO orders (user_id, razorpay_order_id, razorpay_payment_id, amount, payment_status)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, razorpay_order_id, razorpay_payment_id, total_amount, 'paid'))

        order_db_id = cursor.lastrowid  # newly created order's primary key

        # Insert all items
        for pid_str, item in cart.items():
            product_id = int(pid_str)
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                VALUES (%s, %s, %s, %s, %s)
            """, (order_db_id, product_id, item['name'], item['quantity'], item['price']))

        # Commit transaction
        conn.commit()

        # Clear cart and temporary razorpay order id
        session.pop('cart', None)
        session.pop('razorpay_order_id', None)

        flash("Payment successful and order placed!", "success")
        return redirect(f"/user/order-success/{order_db_id}")

    except Exception as e:
        # Rollback and log error
        conn.rollback()
        app.logger.error("Order storage failed: %s\n%s", str(e), traceback.format_exc())
        flash("There was an error saving your order. Contact support.", "danger")
        return redirect('/user/cart')

    finally:
        cursor.close()
        conn.close()


@app.route('/user/order-success/<int:order_db_id>')
def order_success(order_db_id):
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE order_id=%s AND user_id=%s", (order_db_id, session['user_id']))
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order_db_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/user/products')

    return render_template("user/order_success.html", order=order, items=items)


@app.route('/user/my-orders')
def my_orders():
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC", (session['user_id'],))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("user/my_orders.html", orders=orders)


@app.route("/user/download-invoice/<int:order_id>")
def download_invoice(order_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    # Fetch order
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE order_id=%s AND user_id=%s",
                   (order_id, session['user_id']))
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    items = cursor.fetchall()
    cursor.execute("""
    SELECT full_name, phone, delivery_address
    FROM customer_address
    WHERE user_id = %s
    ORDER BY address_id DESC
    LIMIT 1
    """, (session['user_id'],))

    customer = cursor.fetchone()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/user/my-orders')

    # Render invoice HTML
    html = render_template(
    "user/invoice.html",
    order=order,
    items=items,
    customer=customer
)

    pdf = generate_pdf(html)
    if not pdf:
        flash("Error generating PDF", "danger")
        return redirect('/user/my-orders')

    # Prepare response
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f"attachment; filename=invoice_{order_id}.pdf"

    return response
@app.route('/user-forgot-password', methods=['GET', 'POST'])
def user_forgot_password():

    if request.method == 'GET':
        return render_template("user/forgot_password.html")

    email = request.form['email']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:

        otp = str(random.randint(100000, 999999))

        session['reset_email'] = email
        session['reset_otp'] = otp

        msg = Message(
            subject="Smart Card - Password Reset OTP",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )

        msg.body = f"""
        Hello,

        Your password reset OTP is: {otp}

        Please do not share this OTP with anyone.

        Regards,
        Smart Card Team
        """

        # Send OTP through Gmail
        mail.send(msg)

        flash("OTP sent successfully! Please check your email.", "success")

        return redirect(url_for('verify_user_otp'))

    else:
        flash("Email address not found!", "danger")

        return redirect(url_for('user_forgot_password'))



@app.route('/user-verify-otp', methods=['GET', 'POST'])
def verify_user_otp():

    if request.method == 'GET':
        return render_template("user/verify_otp.html")

    entered_otp = request.form.get('otp', '').strip()
    saved_otp = session.get('reset_otp')

    if entered_otp == saved_otp and saved_otp is not None:
        session['otp_verified'] = True
        return redirect(url_for('user_reset_password'))

    flash("Invalid OTP. Please try again.", "danger")
    return redirect(url_for('verify_user_otp'))

@app.route('/user-reset-password', methods=['GET', 'POST'])
def user_reset_password():

    if not session.get('otp_verified'):
        return redirect(url_for('user_forgot_password'))

    if request.method == 'GET':
        return render_template("user/reset_password.html")

    password = request.form['password']
    confirm_password = request.form['confirm_password']

    if password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect(url_for('user_reset_password'))

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    email = session.get('reset_email')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password=%s WHERE email=%s",
        (hashed_password, email)
    )

    conn.commit()
    cursor.close()
    conn.close()

    session.pop('reset_email', None)
    session.pop('reset_otp', None)
    session.pop('otp_verified', None)

    flash("Password updated successfully!", "success")

    return redirect(url_for('user_login'))



# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == '__main__':
    app.run(debug=True)
